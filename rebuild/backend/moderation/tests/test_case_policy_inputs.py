from importlib import import_module, util
from uuid import uuid4

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.transaction import TransactionManagementError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings

from accounts.models import User
from accounts.rate_limits import check_activity_limits
from moderation.models import ContentReport
from moderation.tests.case_helpers import CaseFixtures


def module(test, name):
    test.assertIsNotNone(util.find_spec("moderation." + name), "Required case boundary is absent")
    return import_module("moderation." + name)


class CaseInputTests(SimpleTestCase):
    def test_new_capacities_and_existing_defaults(self):
        self.assertEqual(getattr(settings, "PILOT_REPORTS_PER_DAY", None), 20)
        self.assertEqual(getattr(settings, "PILOT_APPEALS_PER_DAY", None), 10)
        self.assertEqual((settings.PILOT_NEW_CONTACTS_PER_HOUR, settings.PILOT_MESSAGES_PER_HOUR,
                          settings.PILOT_NEW_LISTINGS_PER_DAY), (10, 120, 10))

    def test_invalid_capacity_fails_system_check(self):
        for name in ("PILOT_REPORTS_PER_DAY", "PILOT_APPEALS_PER_DAY"):
            for value in (True, 0, 10001):
                with self.subTest(name=name, value=value), override_settings(**{name: value}):
                    self.assertTrue(any(name in error.msg for error in check_activity_limits(None)))

    def test_text_token_and_fingerprint_validation(self):
        inputs = module(self, "case_inputs")
        for value in (True, None, [], "", " \n", "x\x00", "\ud800", "x" * 2001):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValidationError):
                inputs.normalize_text(value, field="explanation")
        self.assertEqual(inputs.normalize_text(" a\r\nb\rc ", field="explanation"), "a\nb\nc")
        token = uuid4()
        self.assertEqual(inputs.parse_client_token(str(token)), token)
        self.assertEqual(inputs.parse_client_token(token), token)
        for value in (True, [], None, "bad", 1):
            with self.assertRaises(ValidationError):
                inputs.parse_client_token(value)
        values = dict(operation="report", target_type="listing", target_id=12, reason_code="other")
        self.assertEqual(inputs.submission_fingerprint(**values, explanation="a\r\nb"),
                         inputs.submission_fingerprint(**values, explanation="a\nb"))
        self.assertNotEqual(inputs.submission_fingerprint(**values, explanation="a"),
                            inputs.submission_fingerprint(**values, explanation="b"))


class CasePolicyTests(CaseFixtures, TestCase):
    def test_staff_flag_does_not_grant_case_permission(self):
        policies = module(self, "case_policies")
        self.reporter.is_staff = True
        self.reporter.save()
        for call in (policies.require_report_reviewer, policies.require_appeal_reviewer):
            with self.assertRaises(PermissionDenied):
                call(actor=self.reporter)
        permission = self.grant(self.reporter, "review_reports")
        self.assertTrue(self.reporter.has_perm("moderation.review_reports"))
        policies.require_report_reviewer(actor=self.reporter)
        self.reporter.user_permissions.remove(permission)
        with self.assertRaises(PermissionDenied):
            policies.require_report_reviewer(actor=self.reporter)

    def test_actor_checks_current_active_and_verified_email(self):
        policies = module(self, "case_policies")
        self.assertEqual(policies.require_case_actor(actor=self.reporter).pk, self.reporter.pk)
        User.objects.filter(pk=self.reporter.pk).update(email="changed@example.test")
        with self.assertRaises(PermissionDenied):
            policies.require_case_actor(actor=self.reporter)
        User.objects.filter(pk=self.reporter.pk).update(email=self.reporter.email, is_active=False)
        with self.assertRaises(PermissionDenied):
            policies.require_case_actor(actor=self.reporter)

    def test_conflicted_superuser_cannot_review(self):
        policies = module(self, "case_policies")
        report = ContentReport.objects.create(reporter=self.reporter, subject_user=self.owner,
            target_type="listing", revision=self.public, reason_code="other", explanation="Gerekçe",
            evidence={"schema_version": 1}, client_token=uuid4())
        for user in (self.reporter, self.owner):
            User.objects.filter(pk=user.pk).update(is_superuser=True)
            with self.assertRaises(PermissionDenied):
                policies.require_report_reviewer(actor=user, report=report)

    def test_receipt_fingerprint_conflict_and_exact_result(self):
        receipts = module(self, "submission_receipts")
        inputs = module(self, "case_inputs")
        report = ContentReport.objects.create(reporter=self.reporter, subject_user=self.owner,
            target_type="listing", revision=self.public, reason_code="other", explanation="Gerekçe",
            evidence={"schema_version": 1}, client_token=uuid4())
        token = uuid4()
        record = receipts.record_receipt(actor_id=self.reporter.pk, operation="report", token=token,
                                          fingerprint="a" * 64, report_id=report.pk)
        self.assertEqual(receipts.lookup_receipt(actor_id=self.reporter.pk, operation="report",
                          token=token, fingerprint="a" * 64).pk, record.pk)
        with self.assertRaises(inputs.CaseConflict):
            receipts.lookup_receipt(actor_id=self.reporter.pk, operation="report", token=token,
                                    fingerprint="b" * 64)


class CaseLockTests(CaseFixtures, TransactionTestCase):
    def test_lock_helpers_require_atomic_and_lock_exact_identity(self):
        locking = module(self, "case_locking")
        with self.assertRaises(TransactionManagementError):
            locking.lock_case_target(actor=self.reporter, target_type="listing", target_id=self.public.pk)
        with transaction.atomic():
            target = locking.lock_case_target(actor=self.reporter, target_type="listing", target_id=self.public.pk)
            self.assertEqual(target.revision.pk, self.public.pk)
            self.assertEqual(target.listing.pk, self.public.listing_id)
            self.assertEqual(list(target.users), sorted([self.reporter.pk, self.owner.pk]))
            self.assertIsNone(target.message)
        receipts = module(self, "submission_receipts")
        with self.assertRaises(TransactionManagementError):
            receipts.lookup_receipt(actor_id=self.reporter.pk, operation="report", token=uuid4(),
                                    fingerprint="a" * 64)
