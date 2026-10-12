from importlib import import_module, util
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.db import connection, models
from django.http import Http404
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from moderation.models import CaseAuditEvent, ContentReport
from moderation.tests.test_appeals import AppealCalls, AppealFixtures


def boundary(test, name):
    test.assertIsNotNone(util.find_spec("moderation." + name), "Case read boundary is absent")
    return import_module("moderation." + name)


class CaseAccessTests(AppealCalls, AppealFixtures, TestCase):
    def test_own_histories_foreign_uuid_and_safe_projections(self):
        queries = boundary(self, "case_queries")
        self.assertEqual(list(queries.my_reports(actor=self.reporter)), [self.report])
        self.assertEqual(list(queries.my_decisions(actor=self.owner)), [self.decision])
        with self.assertRaises(Http404):
            queries.report_for_reporter(actor=self.owner, report_id=self.report.pk)
        with self.assertRaises(Http404):
            queries.decision_for_subject(actor=self.reporter, decision_id=self.decision.pk)
        projection = queries.decision_for_subject(actor=self.owner, decision_id=self.decision.pk)
        self.assertNotIn("reporter", projection)
        self.assertNotIn("explanation", projection)
        self.assertNotIn(self.report.explanation, str(projection))
        self.assertFalse(any(isinstance(value, models.Model) for value in projection.values()))
        appeal = self.appeal(explanation="Yalnız itiraz sahibi için").record
        report = queries.report_for_reporter(actor=self.reporter, report_id=self.report.pk)
        self.assertNotIn(appeal.explanation, str(report))
        own = queries.appeal_for_appellant(actor=self.owner, appeal_id=appeal.pk)
        self.assertEqual(own["explanation"], appeal.explanation)
        with self.assertRaises(Http404):
            queries.appeal_for_appellant(actor=self.reporter, appeal_id=appeal.pk)

    def test_queues_exclude_conflicts_and_revoked_permissions(self):
        queries = boundary(self, "case_queries")
        pending = self.report_message().record
        self.assertIn(pending, queries.pending_reports(actor=self.case_reviewer))
        self.grant(self.owner, "review_reports")
        self.assertNotIn(pending, queries.pending_reports(actor=self.owner))
        appeal = self.appeal().record
        self.assertIn(appeal, queries.pending_appeals(actor=self.appeal_reviewer))
        self.grant(self.case_reviewer, "review_appeals")
        self.assertNotIn(appeal, queries.pending_appeals(actor=self.case_reviewer))
        self.case_reviewer.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            queries.pending_reports(actor=self.case_reviewer)

    def test_old_reviewer_and_staff_have_no_private_evidence_permission(self):
        evidence = boundary(self, "case_evidence")
        before = CaseAuditEvent.objects.count()
        self.reporter.is_staff = True
        self.reporter.save()
        for actor in (self.reviewer, self.reporter, self.owner):
            with self.assertRaises(PermissionDenied):
                evidence.read_case_evidence(actor=actor, report_id=self.report.pk)
        self.assertEqual(CaseAuditEvent.objects.count(), before)

    def test_appeal_only_reviewer_requires_the_matching_appeal(self):
        evidence = boundary(self, "case_evidence")
        with self.assertRaises(PermissionDenied):
            evidence.read_case_evidence(actor=self.appeal_reviewer, report_id=self.report.pk)
        appeal = self.appeal().record
        result = evidence.read_case_evidence(actor=self.appeal_reviewer, report_id=self.report.pk, appeal_id=appeal.pk)
        self.assertEqual(result["evidence"]["revision_id"], self.public.pk)
        self.assertIn("decision", result)
        self.assertEqual(result["decision"]["reason"], self.decision.reason)
        self.assertEqual(result["decision"]["state"], "active")
        with self.assertRaises(Http404):
            evidence.read_case_evidence(actor=self.appeal_reviewer, report_id=self.report.pk, appeal_id=uuid4())
        self.assertEqual(CaseAuditEvent.objects.filter(action="evidence_viewed").count(), 1)

    def test_message_evidence_is_exact_snapshot_not_thread_and_relation_mismatch_denied(self):
        evidence = boundary(self, "case_evidence")
        report = self.report_message().record
        other = self.next_message()
        result = evidence.read_case_evidence(actor=self.case_reviewer, report_id=report.pk)
        self.assertEqual(result["evidence"]["body"], "Sentetik mesaj")
        self.assertNotIn(other.body, str(result))
        ContentReport.objects.filter(pk=report.pk).update(message=other)
        with self.assertRaises(Http404):
            evidence.read_case_evidence(actor=self.case_reviewer, report_id=report.pk)
        self.assertEqual(CaseAuditEvent.objects.filter(action="evidence_viewed").count(), 1)

    def test_own_history_query_cost_does_not_grow_with_page_size(self):
        queries = boundary(self, "case_queries")
        self.seed_quota(24)
        counts = []
        for size in (12, 24):
            with CaptureQueriesContext(connection) as captured:
                rows = list(queries.my_reports(actor=self.owner)[:size])
                projections = [queries.report_projection(row) for row in rows]
            self.assertEqual(len(projections), size)
            counts.append(len(captured))
        self.assertEqual(counts[0], counts[1])
