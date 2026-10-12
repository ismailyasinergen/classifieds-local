from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from uuid import uuid4

from moderation.tests.case_helpers import CaseFixtures


class CaseModelRegistrationTests(SimpleTestCase):
    def test_case_models_are_registered(self):
        for name in (
            "contentreport", "reportdecision", "appeal", "appealdecision",
            "caseauditevent", "casesubmissionreceipt",
        ):
            with self.subTest(model=name):
                self.assertIn(name, apps.all_models["moderation"])


class CaseModelTests(CaseFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.assertIn("contentreport", apps.all_models["moderation"])
        self.Report = apps.get_model("moderation", "ContentReport")
        self.Decision = apps.get_model("moderation", "ReportDecision")
        self.Appeal = apps.get_model("moderation", "Appeal")
        self.AppealDecision = apps.get_model("moderation", "AppealDecision")
        self.Audit = apps.get_model("moderation", "CaseAuditEvent")
        self.Receipt = apps.get_model("moderation", "CaseSubmissionReceipt")

    def report(self, **kwargs):
        return self.Report.objects.create(**(dict(
            reporter=self.reporter, subject_user=self.owner, target_type="listing",
            revision=self.public, reason_code="other", explanation="İnceleme gerekçesi",
            evidence={"schema_version": 1}, client_token=uuid4()) | kwargs))

    def decision(self, report=None, **kwargs):
        return self.Decision.objects.create(**(dict(
            report=report or self.report(), actor=self.case_reviewer,
            action="no_action", reason="İşlem gerekmiyor") | kwargs))

    def test_target_xor_and_subject_check_at_database(self):
        report = self.report()
        for values in (
            {"message": self.message}, {"revision": None}, {"target_type": "message"},
            {"subject_user": self.reporter}, {"target_type": "invalid"},
        ):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                self.Report.objects.filter(pk=report.pk).update(**values)

    def test_unique_target_and_token_at_database(self):
        report = self.report()
        for values in ({}, {"revision": None, "message": self.message, "target_type": "message",
                            "client_token": report.client_token}):
            duplicate = self.Report(
                reporter=self.reporter, subject_user=self.owner, target_type="listing",
                revision=self.public, reason_code="other", explanation="Tekrar",
                evidence={"schema_version": 1}, client_token=uuid4())
            for field, value in values.items():
                setattr(duplicate, field, value)
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                self.Report.objects.bulk_create([duplicate])

    def test_full_clean_and_nonblank_database_constraint(self):
        for value in ("", " \t\n", "x" * 2001):
            with self.subTest(value_length=len(value)), self.assertRaises(ValidationError):
                self.report(explanation=value)
        report = self.report()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Report.objects.filter(pk=report.pk).update(explanation=" \t\n")

    def test_decision_action_requires_exact_restriction(self):
        decision = self.decision()
        for action in ("invalid", "hide_listing", "restrict_messaging"):
            with self.subTest(action=action), self.assertRaises(IntegrityError), transaction.atomic():
                self.Decision.objects.filter(pk=decision.pk).update(action=action)
        with self.assertRaises(ValidationError):
            self.Decision.objects.create(report=decision.report, actor=self.case_reviewer,
                                         action="no_action", reason=" ")

    def test_appeal_and_decision_are_unique_and_outcome_valid(self):
        decision = self.decision()
        appeal = self.Appeal.objects.create(decision=decision, appellant=self.owner,
                                            explanation="Gözden geçirin", client_token=uuid4())
        with self.assertRaises(ValidationError):
            self.Appeal.objects.create(decision=decision, appellant=self.owner,
                                       explanation="Tekrar", client_token=uuid4())
        result = self.AppealDecision.objects.create(
            appeal=appeal, actor=self.appeal_reviewer, outcome="uphold", reason="Karar uygun")
        with self.assertRaises(ValidationError):
            self.AppealDecision.objects.create(
                appeal=appeal, actor=self.appeal_reviewer, outcome="revoke", reason="Tekrar")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.AppealDecision.objects.filter(pk=result.pk).update(outcome="bad")

    def test_receipt_xor_and_unique_token(self):
        report = self.report()
        receipt = self.Receipt.objects.create(
            actor=self.reporter, operation="report", client_token=uuid4(),
            fingerprint="a" * 64, report=report)
        with self.assertRaises(ValidationError):
            self.Receipt.objects.create(actor=self.reporter, operation="report",
                client_token=receipt.client_token, fingerprint="b" * 64, report=report)
        for values in ({"report": None}, {"operation": "appeal"}, {"operation": "bad"}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                self.Receipt.objects.filter(pk=receipt.pk).update(**values)
        with self.assertRaises(ValidationError):
            self.Receipt.objects.create(actor=self.reporter, operation="report",
                client_token=uuid4(), fingerprint="invalid", report=report)

    def test_all_case_records_are_append_only_and_not_admin_registered(self):
        from django.contrib import admin
        report = self.report()
        decision = self.decision(report)
        appeal = self.Appeal.objects.create(decision=decision, appellant=self.owner,
                                            explanation="İtiraz", client_token=uuid4())
        result = self.AppealDecision.objects.create(
            appeal=appeal, actor=self.appeal_reviewer, outcome="uphold", reason="Gerekçe")
        event = self.Audit.objects.create(actor=self.reporter, report=report, action="report_created")
        receipt = self.Receipt.objects.create(actor=self.reporter, operation="report",
            client_token=uuid4(), fingerprint="a" * 64, report=report)
        for record in (report, decision, appeal, result, event, receipt):
            with self.subTest(model=type(record).__name__):
                self.assertFalse(admin.site.is_registered(type(record)))
                self.assertEqual(record._meta.default_permissions, ())
                with self.assertRaises(ValidationError):
                    record.save()
                with self.assertRaises(ValidationError):
                    record.delete()
        report.explanation = "Değiştirildi"
        with self.assertRaises(ValidationError):
            report.save(update_fields=["explanation"])
        report.refresh_from_db()
        self.assertEqual(report.explanation, "İnceleme gerekçesi")

    def test_audit_accepts_only_metadata_and_valid_actions(self):
        report = self.report()
        with self.assertRaises(ValidationError):
            self.Audit.objects.create(actor=self.reporter, report=report, action="invalid")
        fields = {field.name for field in self.Audit._meta.fields}
        self.assertEqual(fields, {"id", "actor", "report", "appeal", "action", "created_at"})
