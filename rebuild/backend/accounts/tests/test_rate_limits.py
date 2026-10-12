from datetime import timedelta
from importlib.util import find_spec
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction
from django.db.transaction import TransactionManagementError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import User
from listings.models import Listing

AVAILABLE = find_spec("accounts.rate_limits") is not None
if AVAILABLE:
    from accounts.rate_limits import ActionRateLimited, enforce_action_limit

LIMITS = {
    "new_contact": ("PILOT_NEW_CONTACTS_PER_HOUR", 10, 3600),
    "message": ("PILOT_MESSAGES_PER_HOUR", 120, 3600),
    "new_listing": ("PILOT_NEW_LISTINGS_PER_DAY", 10, 86400),
}


class HelperContractTests(SimpleTestCase):
    def test_activity_limit_helper_exists(self):
        self.assertTrue(AVAILABLE, "Missing service-boundary activity limit helper")

    def test_initial_pilot_default_capacities(self):
        for name, capacity, window in LIMITS.values():
            self.assertEqual(getattr(settings, name, None), capacity)


@skipUnless(AVAILABLE, "Helper contract red test records missing implementation")
class ConfigurationTests(TestCase):
    def test_checks_and_runtime_reject_invalid_settings_without_echoing_values(self):
        for name, capacity, window in LIMITS.values():
            for value in (True, False, "private-invalid-input", "1", 1.0, None, 0, -1, 10001):
                with self.subTest(name=name, value=value), override_settings(**{name: value}):
                    errors = [e for e in run_checks() if e.id == "accounts.E001"]
                    self.assertTrue(any(name in e.msg for e in errors))
                    self.assertNotIn("private-invalid-input", str(errors))
                    with self.assertRaises(ImproperlyConfigured) as caught:
                        enforce_action_limit(events=Listing.objects.none(), action="new_listing", at=timezone.now())
                    self.assertIn(name, str(caught.exception))
                    self.assertNotIn("private-invalid-input", str(caught.exception))

    def test_malformed_environment_input_reaches_named_checks_and_runtime_validation(self):
        from config.settings import _pilot_capacity
        for name, capacity, window in LIMITS.values():
            with self.subTest(name=name), patch.dict("os.environ", {name: "private-invalid-input"}):
                value = _pilot_capacity(name, capacity)
                with override_settings(**{name: value}):
                    errors = [e for e in run_checks() if e.id == "accounts.E001"]
                    self.assertTrue(any(name in e.msg for e in errors))
                    self.assertNotIn("private-invalid-input", str(errors))
                    with self.assertRaises(ImproperlyConfigured):
                        enforce_action_limit(events=Listing.objects.none(), action="new_listing", at=timezone.now())

    def test_inclusive_capacity_range(self):
        for capacity in (1, 10000):
            with override_settings(**{name: capacity for name, default, window in LIMITS.values()}):
                self.assertFalse([e for e in run_checks() if e.id == "accounts.E001"])
                enforce_action_limit(events=Listing.objects.none(), action="new_listing", at=timezone.now())


@skipUnless(AVAILABLE, "Helper contract red test records missing implementation")
class AccountingTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user("limits@example.test")
        self.at = timezone.now()
        self.events = Listing.objects.filter(owner=self.actor)

    def row(self, at):
        row = Listing.objects.create(owner=self.actor)
        Listing.objects.filter(pk=row.pk).update(created_at=at)
        return row

    def test_every_action_expires_exact_cutoff_and_counts_just_inside(self):
        for action, (name, default, window) in LIMITS.items():
            with self.subTest(action=action), override_settings(**{name: 1}):
                row = self.row(self.at - timedelta(seconds=window))
                enforce_action_limit(events=self.events, action=action, at=self.at)
                Listing.objects.filter(pk=row.pk).update(created_at=self.at - timedelta(seconds=window, microseconds=-1))
                with self.assertRaises(ActionRateLimited) as caught:
                    enforce_action_limit(events=self.events, action=action, at=self.at)
                self.assertEqual(caught.exception.action, action)
                self.assertEqual(caught.exception.retry_after, 1)
                row.delete()

    @override_settings(PILOT_NEW_LISTINGS_PER_DAY=2)
    def test_reduced_capacity_uses_second_newest_timestamp_not_oldest_overall(self):
        for seconds in (80000, 4000, 2000, 1000):
            self.row(self.at - timedelta(seconds=seconds))
        with self.assertRaises(ActionRateLimited) as caught:
            enforce_action_limit(events=self.events, action="new_listing", at=self.at)
        self.assertEqual(caught.exception.retry_after, 84400)

    @override_settings(PILOT_NEW_LISTINGS_PER_DAY=2)
    def test_future_rows_and_tied_timestamps_count_conservatively(self):
        for _ in range(3):
            self.row(self.at + timedelta(seconds=3, microseconds=1))
        with self.assertRaises(ActionRateLimited) as caught:
            enforce_action_limit(events=self.events, action="new_listing", at=self.at)
        self.assertEqual(caught.exception.retry_after, 86404)

    @override_settings(PILOT_NEW_LISTINGS_PER_DAY=2)
    def test_accounting_sql_is_bounded_timestamp_only_and_has_stable_order(self):
        for _ in range(4):
            self.row(self.at)
        with CaptureQueriesContext(connection) as queries:
            with self.assertRaises(ActionRateLimited):
                enforce_action_limit(events=self.events, action="new_listing", at=self.at)
        self.assertEqual(len(queries), 1)
        sql = queries[0]["sql"]
        self.assertIn('SELECT "listings_listing"."created_at"', sql)
        # Django uses the selected timestamp's ordinal in ORDER BY.
        self.assertIn('ORDER BY 1 DESC, "listings_listing"."id" DESC', sql)
        self.assertIn("LIMIT 2", sql)
        for disallowed in ("COUNT(", "FOR UPDATE", "FOR NO KEY", "public_revision", "body"):
            self.assertNotIn(disallowed, sql)

    def test_action_exception_exposes_only_positive_integer_retry(self):
        error = ActionRateLimited(action="new_listing", retry_after=2)
        self.assertEqual(error.action, "new_listing")
        self.assertEqual(error.retry_after, 2)
        self.assertIn("taslak", error.messages[0].lower())


@skipUnless(AVAILABLE, "Helper contract red test records missing implementation")
class AtomicContractTests(TransactionTestCase):
    def test_helper_requires_atomic_even_for_empty_events(self):
        with self.assertRaises(TransactionManagementError):
            enforce_action_limit(events=Listing.objects.none(), action="new_listing", at=timezone.now())
        with transaction.atomic():
            enforce_action_limit(events=Listing.objects.none(), action="new_listing", at=timezone.now())
