"""Removing a fixture guard must make a real rejection/state assertion fail."""
import importlib
import io
import json
from contextlib import ExitStack
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import SecurityEvent, User
from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision

MODES = ("desktop", "mobile", "nojs")
ROLES = tuple(f"{mode}-{role}" for mode in MODES for role in ("staff", "reviewer", "seller"))
RUN = "a12539bc049ed876"
ADDRESS = "192.0.2.10"
MOUNT = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "


@override_settings(DEBUG=True, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MFABrowserFixtureTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"domain": "localhost:8089", "name": "Synthetic developer"})

    def payload(self, **changes):
        data = {"action": "create", "run": RUN, "db_address": ADDRESS,
                "passwords": {role: "Synthetic-fixture-password-" + role for role in ROLES}}
        data.update(changes)
        return data

    def counts(self):
        return tuple(model.objects.count() for model in (
            User, EmailAddress, Group, Category, AttributeSchema, Listing,
            ListingRevision, Authenticator, SecurityEvent,
        ))

    def invoke(self, payload, *, mount=MOUNT, database=None, dns=ADDRESS):
        # The initial RED is a missing-command assertion, not an import error.
        self.assertIn("mfa_browser_fixture", get_commands(), "Guarded MFA fixture is not implemented.")
        module = importlib.import_module("accounts.management.commands.mfa_browser_fixture")
        database = database if database is not None else (settings.DATABASES["default"]["NAME"], ADDRESS)
        output = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch("sys.stdin", io.StringIO(json.dumps(payload))))
            stack.enter_context(patch.object(module, "_mountinfo", return_value=mount))
            stack.enter_context(patch.object(module, "_database_identity", return_value=database))
            stack.enter_context(patch.object(module.socket, "gethostbyname", return_value=dns))
            call_command("mfa_browser_fixture", stdout=output)
        return json.loads(output.getvalue())

    def rejected_without_writes(self, payload, **guard_changes):
        before = self.counts()
        with self.assertRaisesMessage(CommandError, "Guarded MFA fixture operation refused."):
            self.invoke(payload, **guard_changes)
        self.assertEqual(self.counts(), before)

    def test_create_has_nine_owned_accounts_three_submitted_listings_and_no_mfa(self):
        result = self.invoke(self.payload())
        self.assertEqual(set(result), {"receipt", "state"})
        state = result["state"]
        self.assertEqual(state["counts"], {"users": 9, "groups": 1, "listings": 3, "revisions": 3})
        self.assertEqual(set(state["roles"]), set(ROLES))
        self.assertEqual(state["revisions"], dict.fromkeys(MODES, "submitted"))
        for role in ROLES:
            self.assertEqual(state["roles"][role], {"primary": 0, "recovery": 0, "events": 0})
            user = User.objects.get(email=f"mfa-{RUN}-{role}@browser.example.test")
            self.assertEqual(user.is_staff, role.endswith("-staff"))
            self.assertFalse(user.is_superuser)
            self.assertEqual(user.has_perm("listings.review_listingrevision"), role.endswith("-reviewer"))
            self.assertTrue(EmailAddress.objects.filter(user=user, email=user.email, verified=True).exists())
        self.assertEqual(Authenticator.objects.count(), 0)
        self.assertEqual(SecurityEvent.objects.count(), 0)
        inspected = self.invoke({"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": result["receipt"]})
        self.assertEqual(inspected, state)
        self.assertNotIn("receipt", inspected)
        self.assertNotIn("@", json.dumps(inspected))

    def test_non_debug_original_site_and_wrong_media_mount_are_rejected(self):
        with override_settings(DEBUG=False):
            self.rejected_without_writes(self.payload())
        Site.objects.filter(pk=settings.SITE_ID).update(domain="localhost:8088")
        self.rejected_without_writes(self.payload())
        Site.objects.filter(pk=settings.SITE_ID).update(domain="localhost:8089")
        self.rejected_without_writes(self.payload(), mount="/volumes/classifieds-rebuild_rebuild_media/_data /var/lib/classifieds/media ")

    def test_wrong_database_name_address_dns_and_vendor_are_rejected(self):
        self.rejected_without_writes(self.payload(), database=("foreign_database", ADDRESS))
        self.rejected_without_writes(self.payload(db_address="192.0.2.11"))
        self.rejected_without_writes(self.payload(), dns="192.0.2.12")
        from django.db import connection
        with patch.object(connection, "vendor", "sqlite"):
            self.rejected_without_writes(self.payload())

    def test_invalid_run_action_extra_fields_and_password_map_are_rejected(self):
        for changes in ({"run": "../foreign"}, {"run": "A" * 16}, {"action": "delete"},
                        {"user_id": 1}, {"passwords": {}}, {"passwords": dict.fromkeys(ROLES, "short")}):
            with self.subTest(case=next(iter(changes))):
                self.rejected_without_writes(self.payload(**changes))

    def test_existing_user_category_or_group_collision_is_never_adopted(self):
        user = User.objects.create_user(email=f"mfa-{RUN}-collision@browser.example.test")
        self.rejected_without_writes(self.payload())
        user.delete()
        category = Category.objects.create(name="Synthetic collision", slug=f"mfa-{RUN}")
        self.rejected_without_writes(self.payload())
        category.delete()
        Group.objects.create(name=f"mfa-{RUN}-reviewers")
        self.rejected_without_writes(self.payload())

    def test_duplicate_creation_preserves_the_first_run(self):
        first = self.invoke(self.payload())
        self.rejected_without_writes(self.payload())
        current = self.invoke({"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": first["receipt"]})
        self.assertEqual(current, first["state"])

    def test_inspection_requires_matching_signed_run_receipt(self):
        first = self.invoke(self.payload())
        for payload in (
            {"action": "inspect", "run": RUN, "db_address": ADDRESS},
            {"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": "invalid"},
            {"action": "inspect", "run": "b" * 16, "db_address": ADDRESS, "receipt": first["receipt"]},
            {"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": first["receipt"], "user_id": 1},
        ):
            self.rejected_without_writes(payload)

    def test_foreign_revision_in_owned_category_is_rejected_without_further_writes(self):
        first = self.invoke(self.payload())
        foreign = User.objects.create_user(email="foreign-fixture-user@example.invalid")
        listing = Listing.objects.get(owner__email=f"mfa-{RUN}-desktop-seller@browser.example.test")
        Listing.objects.filter(pk=listing.pk).update(owner=foreign)
        self.rejected_without_writes({"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": first["receipt"]})

    def test_changed_owned_role_or_group_permission_is_rejected(self):
        first = self.invoke(self.payload())
        User.objects.filter(email=f"mfa-{RUN}-desktop-reviewer@browser.example.test").update(is_staff=True)
        self.rejected_without_writes({"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": first["receipt"]})
        User.objects.filter(email=f"mfa-{RUN}-desktop-reviewer@browser.example.test").update(is_staff=False)
        Group.objects.get(name=f"mfa-{RUN}-reviewers").permissions.clear()
        self.rejected_without_writes({"action": "inspect", "run": RUN, "db_address": ADDRESS, "receipt": first["receipt"]})

    def test_partial_creation_failure_rolls_back_every_owned_row(self):
        self.assertIn("mfa_browser_fixture", get_commands(), "Guarded MFA fixture is not implemented.")
        original = User.objects.create_user
        calls = 0

        def create_one_then_fail(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("Synthetic controlled construction failure")
            return original(*args, **kwargs)

        with patch.object(User.objects, "create_user", side_effect=create_one_then_fail):
            self.rejected_without_writes(self.payload())
        self.assertEqual(calls, 2)
