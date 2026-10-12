from datetime import timedelta
from importlib import import_module, util
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from events.models import OutboxEvent
from moderation.case_inputs import CaseConflict
from moderation.models import CaseAuditEvent, MessagingRestriction, ReportDecision, Restriction
from moderation.tests.case_helpers import CaseFixtures
from moderation.tests.test_reports import ReportCalls


class DecisionCalls(ReportCalls):
    def decide(self, report, **changes):
        self.assertIsNotNone(util.find_spec("moderation.report_decisions"), "Case decision boundary is absent")
        return import_module("moderation.report_decisions").decide_report(**(dict(
            actor=self.case_reviewer, report_id=report.pk, action="no_action", reason="İnceleme sonucu") | changes))


class ReportDecisionTests(DecisionCalls, CaseFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.grant(self.case_reviewer, "review_reports")

    def test_no_action_does_not_restrict(self):
        report = self.report_listing().record
        before = OutboxEvent.objects.count()
        decision = self.decide(report)
        self.assertEqual(decision.action, "no_action")
        self.assertEqual((Restriction.objects.count(), MessagingRestriction.objects.count()), (0, 0))
        self.assertEqual(OutboxEvent.objects.count(), before)

    def test_hide_only_reported_current_listing(self):
        report = self.report_listing().record
        decision = self.decide(report, action="hide_listing", expected_public_revision_id=self.public.pk)
        self.assertEqual(decision.visibility_restriction.listing_id, self.listing.pk)
        self.assertIsNone(decision.visibility_restriction.seller_id)
        self.listing.refresh_from_db()
        self.assertEqual((self.listing.lifecycle, self.listing.public_revision_id), ("live", self.public.pk))
        self.assertEqual(MessagingRestriction.objects.count(), 0)

    def test_message_sanction_requires_extra_permission_and_future_end(self):
        report = self.report_message().record
        end = timezone.now() + timedelta(hours=1)
        with self.assertRaises(PermissionDenied):
            self.decide(report, action="restrict_messaging", ends_at=end)
        self.grant(self.case_reviewer, "restrict_messaging")
        for invalid in (None, "later", timezone.now().replace(tzinfo=None), timezone.now() - timedelta(seconds=1)):
            with self.assertRaises(ValidationError):
                self.decide(report, action="restrict_messaging", ends_at=invalid)
        decision = self.decide(report, action="restrict_messaging", ends_at=end)
        self.assertEqual(decision.messaging_restriction.user_id, self.reporter.pk)
        self.assertEqual(decision.messaging_restriction.ends_at, end)
        self.assertEqual(Restriction.objects.count(), 0)

    def test_conflicted_actor_including_superuser_cannot_decide(self):
        report = self.report_listing().record
        for actor in (self.owner, self.reporter):
            User.objects.filter(pk=actor.pk).update(is_superuser=True)
            with self.assertRaises(PermissionDenied):
                self.decide(report, actor=actor)
        self.assertFalse(ReportDecision.objects.exists())

    def test_other_revision_cannot_be_hidden_by_stale_form(self):
        report = self.report_listing().record
        newer = self.submit(self.edit(self.public, title="Yeni"))
        self.approve(newer, expected=self.public.pk)
        with self.assertRaises(CaseConflict):
            self.decide(report, action="hide_listing", expected_public_revision_id=self.public.pk)
        with self.assertRaises(CaseConflict):
            self.decide(report, action="hide_listing", expected_public_revision_id=newer.pk)
        self.assertEqual(Restriction.objects.count(), 0)
        self.assertEqual(self.decide(report).action, "no_action")

    def test_replay_is_exact_and_rechecks_current_permission(self):
        report = self.report_listing().record
        first = self.decide(report, reason="  Gerekçe\r\nİkinci satır ")
        self.assertEqual(self.decide(report, reason="Gerekçe\nİkinci satır").pk, first.pk)
        with self.assertRaises(CaseConflict):
            self.decide(report, reason="Başka gerekçe")
        self.grant(self.appeal_reviewer, "review_reports")
        with self.assertRaises(CaseConflict):
            self.decide(report, actor=self.appeal_reviewer, reason=first.reason)
        self.case_reviewer.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            self.decide(report, reason=first.reason)
        self.assertEqual(ReportDecision.objects.count(), 1)
        self.assertEqual(CaseAuditEvent.objects.filter(action="report_decided").count(), 1)

    def test_audit_or_decision_failure_rolls_back_restriction(self):
        report = self.report_listing().record
        self.assertIsNotNone(util.find_spec("moderation.report_decisions"))
        for boundary in ("moderation.report_decisions.append_case_event", "moderation.models.ReportDecision.save"):
            with patch(boundary, side_effect=RuntimeError("synthetic write outage")):
                with self.assertRaises(RuntimeError):
                    self.decide(report, action="hide_listing", expected_public_revision_id=self.public.pk)
            self.assertEqual(Restriction.objects.count(), 0)
            self.assertEqual(ReportDecision.objects.count(), 0)
            self.assertEqual(CaseAuditEvent.objects.filter(action="report_decided").count(), 0)

    def test_action_target_reason_and_subject_mismatch_rejected(self):
        report = self.report_listing().record
        for changes in ({"action": "bad"}, {"reason": " "}, {"reason": "x" * 2001},
                        {"action": "restrict_messaging", "ends_at": timezone.now() + timedelta(hours=1)},
                        {"ends_at": timezone.now() + timedelta(hours=1)}):
            with self.assertRaises(ValidationError):
                self.decide(report, **changes)
        from moderation.models import ContentReport
        ContentReport.objects.filter(pk=report.pk).update(subject_user=self.appeal_reviewer)
        with self.assertRaises(CaseConflict):
            self.decide(report, action="hide_listing", expected_public_revision_id=self.public.pk)
        self.assertEqual(Restriction.objects.count(), 0)
