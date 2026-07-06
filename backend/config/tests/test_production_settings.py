from django.conf import settings
from django.core.checks import run_checks
from django.test import SimpleTestCase, override_settings

from config import settings as project_settings


class ProductionSettingsTests(SimpleTestCase):
    def test_env_list_helper_trims_empty_values(self):
        original = project_settings.os.environ.get("TEST_ENV_LIST_V102")
        try:
            project_settings.os.environ["TEST_ENV_LIST_V102"] = " example.com, , www.example.com "
            self.assertEqual(
                project_settings._env_list("TEST_ENV_LIST_V102"),
                ["example.com", "www.example.com"],
            )
        finally:
            if original is None:
                project_settings.os.environ.pop("TEST_ENV_LIST_V102", None)
            else:
                project_settings.os.environ["TEST_ENV_LIST_V102"] = original

    def test_local_development_defaults_remain_available(self):
        self.assertIn("localhost", settings.ALLOWED_HOSTS)
        self.assertIn("127.0.0.1", settings.ALLOWED_HOSTS)
        self.assertIn(settings.MEDIA_URL, {"media/", "/media/"})
        self.assertIn(settings.STATIC_URL, {"static/", "/static/"})

    @override_settings(
        DEBUG=False,
        SECRET_KEY="test-production-secret-key-with-more-than-fifty-characters-v102",
        ALLOWED_HOSTS=["example.com", "www.example.com"],
        CSRF_TRUSTED_ORIGINS=["https://example.com", "https://www.example.com"],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_production_security_profile_has_no_deploy_warnings(self):
        messages = run_checks(include_deployment_checks=True)
        security_messages = [
            message
            for message in messages
            if message.id.startswith("security.")
        ]
        self.assertEqual(security_messages, [])
