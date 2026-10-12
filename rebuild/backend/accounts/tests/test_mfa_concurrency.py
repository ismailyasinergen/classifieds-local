"""Exact synthetic-key Redis race and PostgreSQL single-use recovery lock."""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
from django.core.cache import caches
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings

from accounts.models import User
from .mfa_support import totp_code


class MFASingleUseConcurrencyTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email=f"mfa-race-{uuid.uuid4().hex}@example.invalid")
        self.secret = generate_totp_secret()
        self.primary = TOTP.activate(self.user, self.secret).instance
        self.recovery = RecoveryCodes.activate(self.user).instance

    def race(self, validate):
        barrier = threading.Barrier(2, timeout=10)

        def contender():
            close_old_connections()
            try:
                barrier.wait()
                return validate()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(contender) for _ in range(2)]
            return [future.result(timeout=20) for future in futures]

    def test_shared_redis_accepts_the_same_totp_exactly_once(self):
        prefix = "classifieds-mfa-tests-" + uuid.uuid4().hex
        code = totp_code(self.secret)
        config = {"default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://redis:6379/1", "KEY_PREFIX": prefix,
            "OPTIONS": {"socket_connect_timeout": 2, "socket_timeout": 2},
        }}
        with override_settings(CACHES=config):
            cache = caches["default"]
            exact_key = self.primary.wrap()._get_used_cache_key(code)
            try:
                results = self.race(lambda: Authenticator.objects.get(pk=self.primary.pk).wrap().validate_code(code))
                self.assertEqual(sorted(results), [False, True])
                self.assertTrue(cache.get(exact_key) is not None)
            finally:
                # Never clear/flush shared Redis; delete precisely our owned key.
                cache.delete(exact_key)

    def test_postgresql_accepts_the_same_recovery_code_exactly_once(self):
        self.assertEqual(connection.vendor, "postgresql")
        code = self.recovery.wrap().get_unused_codes()[0]
        results = self.race(lambda: Authenticator.objects.get(pk=self.recovery.pk).wrap().validate_code(code))
        self.assertEqual(sorted(results), [False, True])
        self.recovery.refresh_from_db()
        self.assertEqual(len(self.recovery.wrap().get_unused_codes()), 9)
        self.assertFalse(self.recovery.wrap().validate_code(code))

    def test_default_test_cache_cannot_clear_live_authentication_keys(self):
        self.assertEqual(caches["default"].__class__.__name__, "LocMemCache")
        prefix = "classifieds-mfa-tests-" + uuid.uuid4().hex
        cache_config = {"security_isolation_probe": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://redis:6379/1", "KEY_PREFIX": prefix,
            "OPTIONS": {"socket_connect_timeout": 2, "socket_timeout": 2},
        }}
        from django.conf import settings
        with override_settings(CACHES={**settings.CACHES, **cache_config}):
            probe = caches["security_isolation_probe"]
            exact_key = "owned-isolation-sentinel"
            try:
                probe.set(exact_key, "synthetic-owned-value", 60)
                caches["default"].clear()
                self.assertEqual(probe.get(exact_key), "synthetic-owned-value")
            finally:
                probe.delete(exact_key)
