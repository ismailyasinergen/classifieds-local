from io import StringIO
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase, override_settings
from catalog.models import Category


class LocalSetupTests(TestCase):
    @override_settings(DEBUG=True)
    def test_explicit_local_setup_is_idempotent_and_seeds_catalog(self):
        for _ in range(2):
            call_command("setup_local", domain="127.0.0.1:8088", stdout=StringIO())
        site = Site.objects.get(pk=1)
        self.assertEqual((site.name, site.domain), ("Classifieds Local", "127.0.0.1:8088"))
        self.assertEqual(Category.objects.filter(slug="automobiles").count(), 1)

    @override_settings(DEBUG=False)
    def test_local_setup_refuses_nonlocal_runtime(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("setup_local", stdout=StringIO())
