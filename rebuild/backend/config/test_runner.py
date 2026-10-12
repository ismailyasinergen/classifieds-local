"""All normal tests use process-local security keys, never live Redis."""
from django.test import override_settings
from django.test.runner import DiscoverRunner


class IsolatedSecurityTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        self.security_settings = override_settings(
            CACHES={"default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "classifieds-tests",
            }},
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        )
        self.security_settings.enable()
        super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs):
        try:
            super().teardown_test_environment(**kwargs)
        finally:
            self.security_settings.disable()
