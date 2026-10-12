from io import StringIO
import importlib
import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from accounts.models import User
from catalog.models import Category


@override_settings(DEBUG=True)
class PilotBrowserFixtureTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"domain": "localhost:8089", "name": "synthetic"})
        with connection.cursor() as cursor:
            cursor.execute("SELECT host(inet_server_addr())")
            self.address = cursor.fetchone()[0]
        self.data = {"run": "aabbccddeeff1234", "action": "create", "db_address": self.address,
                     "passwords": {role: "synthetic-test-password-long-enough"
                                   for role in ("contact", "message", "creator", "seller", "reviewer")}}

    def invoke(self, data=None, mount=True):
        module = importlib.import_module("accounts.management.commands.pilot_limits_browser_fixture")
        command = module.Command(stdout=StringIO())
        with patch.object(module.sys, "stdin", StringIO(json.dumps(data or self.data))), \
             patch.object(module.Path, "read_text", return_value=module.DEV_MOUNT if mount else ""), \
             patch.object(module.socket, "gethostbyname", return_value=self.address):
            command.handle()
        return json.loads(command.stdout.getvalue())

    def assert_denied_without_users(self, data=None, mount=True):
        before = User.objects.count()
        with self.assertRaises(CommandError):
            self.invoke(data, mount=mount)
        self.assertEqual(User.objects.count(), before)

    @override_settings(DEBUG=False)
    def test_non_debug_runtime_is_rejected(self):
        self.assert_denied_without_users()

    def test_original_site_is_rejected(self):
        Site.objects.filter(pk=settings.SITE_ID).update(domain="127.0.0.1:8088")
        self.assert_denied_without_users()

    def test_wrong_mount_is_rejected(self):
        self.assert_denied_without_users(mount=False)

    def test_wrong_database_address_is_rejected(self):
        self.assert_denied_without_users({**self.data, "db_address": "192.0.2.1"})

    def test_invalid_run_and_extra_input_are_rejected(self):
        for data in ({**self.data, "run": "../real"}, {**self.data, "extra": True},
                     {**self.data, "action": "delete"}):
            with self.subTest(keys=sorted(data)):
                self.assert_denied_without_users(data)

    def test_reserved_account_or_category_collision_is_rejected(self):
        User.objects.create_user(email="pilot-aabbccddeeff1234-contact@browser.example.test")
        self.assert_denied_without_users()
        User.objects.all().delete()
        Category.objects.create(name="collision", slug="pilot-aabbccddeeff1234")
        self.assert_denied_without_users()

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=9)
    def test_non_default_running_capacity_is_rejected(self):
        self.assert_denied_without_users()

    def test_successful_history_and_scoped_override_restore_defaults(self):
        result = self.invoke()
        self.assertEqual(result["counts"]["contact"]["contacts"], 10)
        self.assertEqual(result["counts"]["message"]["messages"], 119)
        self.assertEqual(result["counts"]["creator"]["listings"], 10)
        self.assertEqual(result["defaults"], [10, 120, 10])
        self.assertEqual((settings.PILOT_NEW_CONTACTS_PER_HOUR,
                          settings.PILOT_MESSAGES_PER_HOUR,
                          settings.PILOT_NEW_LISTINGS_PER_DAY), (10, 120, 10))
        self.assertEqual(self.invoke({"run": self.data["run"], "action": "inspect",
                                     "db_address": self.address})["counts"], result["counts"])

    def test_inspection_rejects_foreign_listing_ownership(self):
        result = self.invoke()
        from listings.models import Listing
        outsider = User.objects.create_user(email="unrelated@example.test")
        Listing.objects.filter(pk=result["target_listing"]).update(owner=outsider)
        before = Listing.objects.count()
        with self.assertRaises(CommandError):
            self.invoke({"run": self.data["run"], "action": "inspect", "db_address": self.address})
        self.assertEqual(Listing.objects.count(), before)

    def test_legacy_conversation_fixture_keeps_13_rows_and_one_live_contact_slot(self):
        from datetime import timedelta
        from uuid import uuid4
        from django.utils import timezone
        from accounts.rate_limits import ActionRateLimited, enforce_action_limit
        from conversations.models import Conversation
        from conversations.queries import inbox_conversations

        module = importlib.import_module("accounts.management.commands.conversations_browser_fixture")
        data = {"run": "bbccddee11223344", "action": "create", "db_address": self.address,
                "passwords": {role: "synthetic-test-password-long-enough"
                              for role in ("buyer", "seller", "newcomer")}}
        command = module.Command(stdout=StringIO())
        mount = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "
        with patch.object(module.sys, "stdin", StringIO(json.dumps(data))), \
             patch.object(module.Path, "read_text", return_value=mount), \
             patch.object(module.socket, "gethostbyname", return_value=self.address):
            command.handle()
        result = json.loads(command.stdout.getvalue())
        buyer = User.objects.get(email="conversations-bbccddee11223344-buyer@browser.example.test")
        events = Conversation.objects.filter(initiator=buyer)
        cutoff = timezone.now() - timedelta(hours=1)
        self.assertEqual(events.count(), 13)
        self.assertEqual(events.filter(created_at__gt=cutoff).count(), 9)
        self.assertEqual(events.filter(created_at__lte=cutoff).count(), 4)
        self.assertEqual(inbox_conversations(actor=buyer).count(), 13)
        self.assertEqual(settings.PILOT_NEW_CONTACTS_PER_HOUR, 10)
        self.client.force_login(buyer)
        start = f"/mesajlar/ilan/{result['listing']}/"
        response = self.client.post(start, {"body": "Synthetic genuine final live slot",
                                           "client_token": str(uuid4())})
        self.assertEqual(response.status_code, 302)
        self.assertRegex(response["Location"], r"^/mesajlar/[a-f0-9-]+/$")
        self.assertEqual(events.count(), 14)
        self.assertEqual(events.filter(created_at__gt=cutoff).count(), 10)
        self.assertEqual(len(self.client.get("/mesajlar/").context["page_obj"]), 12)
        self.assertEqual(len(self.client.get("/mesajlar/?page=2").context["page_obj"]), 2)
        with self.assertRaises(ActionRateLimited):
            enforce_action_limit(events=events, action="new_contact", at=timezone.now())
