import json
from io import StringIO
from unittest.mock import patch

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from accounts.models import User
from listings.models import Favorite, Listing
from notifications.models import SavedSearch


@override_settings(DEBUG=True)
class FavoritesFixtureTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=1, defaults={'domain': 'localhost:8089', 'name': 'Synthetic'})
        with connection.cursor() as cursor:
            cursor.execute('SELECT host(inet_server_addr())')
            self.address = cursor.fetchone()[0]
        self.data = {'run': '0123456789abcdef', 'db_address': self.address,
                     'passwords': {mode: 'synthetic-test-only-password-value-32' for mode in ('desktop', 'mobile', 'nojs')}}

    def run_fixture(self, data=None, mount=True):
        with patch('sys.stdin', StringIO(json.dumps(data or self.data))), patch(
            'accounts.management.commands.favorites_browser_fixture.Path.read_text',
            return_value='/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media ' if mount else ''):
            output = StringIO()
            call_command('favorites_browser_fixture', stdout=output)
            return output.getvalue()

    def test_create_is_fresh_reserved_and_never_echoes_credentials(self):
        output = self.run_fixture()
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(Listing.objects.count(), 13)
        self.assertEqual(Favorite.objects.count(), 36)
        self.assertEqual(SavedSearch.objects.count(), 36)
        self.assertNotIn('password', output)
        self.assertNotIn('@', output)
        self.assertFalse(User.objects.filter(is_staff=True).exists())
        with self.assertRaises(CommandError):
            self.run_fixture()
        self.assertEqual(User.objects.count(), 4)

    def test_wrong_site_debug_mount_and_database_refused_without_rows(self):
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            self.run_fixture()
        Site.objects.filter(pk=1).update(domain='127.0.0.1:8088')
        with self.assertRaises(CommandError):
            self.run_fixture()
        Site.objects.filter(pk=1).update(domain='localhost:8089')
        with self.assertRaises(CommandError):
            self.run_fixture(mount=False)
        with self.assertRaises(CommandError):
            self.run_fixture({**self.data, 'db_address': '192.0.2.99'})
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_run_extra_fields_or_passwords_refused(self):
        for data in ({**self.data, 'run': '../bad'}, {**self.data, 'user': 1},
                     {**self.data, 'passwords': {'desktop': 'short'}}):
            with self.assertRaises(CommandError):
                self.run_fixture(data)
        self.assertEqual(User.objects.count(), 0)
