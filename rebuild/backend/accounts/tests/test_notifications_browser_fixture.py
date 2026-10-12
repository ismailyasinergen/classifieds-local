import json
from io import StringIO
from unittest.mock import patch
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from accounts.models import User
from allauth.mfa.models import Authenticator
from notifications.models import SavedSearch, NotificationDelivery
from events.models import OutboxEvent


@override_settings(DEBUG=True, IN_APP_NOTIFICATIONS_ENABLED=True)
class NotificationFixtureTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=1, defaults={'domain': 'localhost:8089', 'name': 'Synthetic'})
        with connection.cursor() as cursor:
            cursor.execute('SELECT host(inet_server_addr())')
            address = cursor.fetchone()[0]
        self.data = {'action': 'create', 'run': '0123456789abcdef', 'db_address': address,
                     'passwords': {m: 'synthetic-test-only-password-value-32' for m in ('desktop', 'mobile', 'nojs', 'reviewer')}}

    def invoke(self, data=None, mount=True):
        with patch('sys.stdin', StringIO(json.dumps(data or self.data))), patch(
            'accounts.management.commands.mfa_browser_fixture._mountinfo',
            return_value='/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media ' if mount else ''):
            out = StringIO()
            call_command('notifications_browser_fixture', stdout=out)
            return out.getvalue()

    def test_new_records_only_no_publication_subscription_or_factor(self):
        raw = self.invoke()
        result = json.loads(raw)
        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(result['createdListings'], 6)
        self.assertFalse(OutboxEvent.objects.exists())
        self.assertFalse(SavedSearch.objects.exists())
        self.assertFalse(NotificationDelivery.objects.exists())
        self.assertFalse(Authenticator.objects.exists())
        self.assertNotIn('password', raw)
        self.assertNotIn('@', raw)
        with self.assertRaises(CommandError):
            self.invoke()

    def test_original_wrong_mount_and_disabled_refused(self):
        with self.assertRaises(CommandError):
            self.invoke(mount=False)
        with override_settings(IN_APP_NOTIFICATIONS_ENABLED=False), self.assertRaises(CommandError):
            self.invoke()
        Site.objects.filter(pk=1).update(domain='127.0.0.1:8088')
        with self.assertRaises(CommandError):
            self.invoke()
        self.assertFalse(User.objects.exists())

    def test_signed_inspection_cannot_change_or_cross_run(self):
        result = json.loads(self.invoke())
        data = {k: v for k, v in self.data.items() if k != 'passwords'}
        data.update(action='inspect', receipt=result['receipt'])
        self.assertEqual(json.loads(self.invoke(data))['events'], 0)
        with self.assertRaises(CommandError):
            self.invoke({**data, 'run': 'fedcba9876543210'})
        self.assertEqual(User.objects.count(), 5)
