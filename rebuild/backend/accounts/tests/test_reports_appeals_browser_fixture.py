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
from accounts.models import User, SecurityEvent
from catalog.models import Category, AttributeSchema
from conversations.models import Conversation, Message, Participant, UserBlock
from listings.models import Listing, ListingRevision
from moderation.models import (ContentReport, ReportDecision, Appeal, AppealDecision,
    CaseAuditEvent, CaseSubmissionReceipt, Restriction, MessagingRestriction, ModerationDecision)

MODES = ("desktop", "mobile", "nojs")
ROLES = tuple(f"{mode}-{role}" for mode in MODES for role in ("sender", "recipient", "report-reviewer", "appeal-reviewer"))
RUN = "c12539bc049ed876"
ADDRESS = "192.0.2.10"
MOUNT = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "


@override_settings(DEBUG=True, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CaseBrowserFixtureTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"domain": "localhost:8089", "name": "Synthetic developer"})

    def payload(self, **changes):
        return dict(action="create", run=RUN, db_address=ADDRESS,
            passwords={role: "Synthetic-fixture-password-" + role for role in ROLES}) | changes

    def counts(self):
        return tuple(model.objects.count() for model in (User, EmailAddress, Group, Category, AttributeSchema,
            Listing, ListingRevision, Conversation, Message, Participant, UserBlock, Authenticator, SecurityEvent,
            ContentReport, ReportDecision, Appeal, AppealDecision, CaseAuditEvent, CaseSubmissionReceipt,
            Restriction, MessagingRestriction, ModerationDecision))

    def invoke(self, payload, *, mount=MOUNT, database=None, dns=ADDRESS):
        self.assertIn("reports_appeals_browser_fixture", get_commands(), "Guarded case fixture is absent")
        guard = importlib.import_module("accounts.management.commands.mfa_browser_fixture")
        output = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch("sys.stdin", io.StringIO(json.dumps(payload))))
            stack.enter_context(patch.object(guard, "_mountinfo", return_value=mount))
            stack.enter_context(patch.object(guard, "_database_identity", return_value=database or (settings.DATABASES["default"]["NAME"], ADDRESS)))
            stack.enter_context(patch.object(guard.socket, "gethostbyname", return_value=dns))
            call_command("reports_appeals_browser_fixture", stdout=output)
        return json.loads(output.getvalue())

    def reject(self, payload, **changes):
        before = self.counts()
        with self.assertRaisesMessage(CommandError, "Guarded case fixture operation refused."):
            self.invoke(payload, **changes)
        self.assertEqual(before, self.counts())

    def test_create_is_synthetic_distinct_roles_without_factors_or_cases(self):
        result = self.invoke(self.payload())
        self.assertEqual(result["state"]["counts"]["users"], 13)
        self.assertEqual(set(result["state"]["targets"]), set(MODES))
        for role in ROLES:
            user = User.objects.get(email=f"case-{RUN}-{role}@browser.example.test")
            self.assertFalse(user.is_staff or user.is_superuser)
            self.assertEqual(user.has_perm("moderation.review_reports"), role.endswith("report-reviewer"))
            self.assertEqual(user.has_perm("listings.review_listingrevision"), False)
        for model in (ContentReport, ReportDecision, Appeal, AppealDecision, CaseAuditEvent,
                      CaseSubmissionReceipt, Authenticator, SecurityEvent):
            self.assertEqual(model.objects.count(), 0)
        inspected = self.invoke(dict(action="inspect", run=RUN, db_address=ADDRESS, receipt=result["receipt"]))
        self.assertEqual(inspected, result["state"])
        self.assertNotIn("@", json.dumps(inspected))

    def test_runtime_guard_rejections_write_nothing(self):
        with override_settings(DEBUG=False):
            self.reject(self.payload())
        Site.objects.filter(pk=settings.SITE_ID).update(domain="localhost:8088")
        self.reject(self.payload())
        Site.objects.filter(pk=settings.SITE_ID).update(domain="localhost:8089")
        self.reject(self.payload(), mount="foreign")
        self.reject(self.payload(), database=("foreign", ADDRESS))
        self.reject(self.payload(db_address="192.0.2.11"))
        self.reject(self.payload(), dns="192.0.2.12")

    def test_invalid_input_is_atomic(self):
        for changes in ({"run": "../bad"}, {"run": "A"*16}, {"action": "delete"}, {"passwords": {}},
                        {"extra": True}, {"passwords": dict.fromkeys(ROLES, "short")}):
            self.reject(self.payload(**changes))
        missing = self.payload()
        del missing["run"]
        self.reject(missing)

    def test_collision_duplicate_and_cross_run_receipt(self):
        first = self.invoke(self.payload())
        self.reject(self.payload())
        self.reject(dict(action="inspect", run="a"*16, db_address=ADDRESS, receipt=first["receipt"]))
        self.reject(dict(action="inspect", run=RUN, db_address=ADDRESS, receipt="invalid"))
        self.assertEqual(self.invoke(dict(action="inspect", run=RUN, db_address=ADDRESS, receipt=first["receipt"])), first["state"])

    def test_existing_unrelated_prefix_is_not_adopted(self):
        User.objects.create_user(f"case-{RUN}-collision@browser.example.test")
        self.reject(self.payload())

    def test_partial_creation_rolls_back(self):
        self.assertIn("reports_appeals_browser_fixture", get_commands())
        original, count = User.objects.create_user, 0
        def fail(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                raise ValueError("Controlled synthetic failure")
            return original(*args, **kwargs)
        with patch.object(User.objects, "create_user", side_effect=fail):
            self.reject(self.payload())
        self.assertEqual(count, 3)

    def test_tampered_role_is_rejected_without_writes(self):
        result = self.invoke(self.payload())
        User.objects.filter(email=f"case-{RUN}-desktop-sender@browser.example.test").update(is_staff=True)
        self.reject(dict(action="inspect", run=RUN, db_address=ADDRESS, receipt=result["receipt"]))
