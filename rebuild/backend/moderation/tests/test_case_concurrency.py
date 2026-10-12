from uuid import uuid4
from django.utils import timezone

from django.test import TransactionTestCase

from accounts.rate_limits import ActionRateLimited
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers
from moderation.models import CaseAuditEvent, CaseSubmissionReceipt, ContentReport
from moderation.tests.case_helpers import CaseFixtures
from moderation.tests.test_reports import ReportCalls
from moderation.tests.test_report_decisions import DecisionCalls
from moderation.case_inputs import CaseConflict
from moderation.models import ReportDecision, Restriction


class ReportConcurrencyTests(ReportCalls, PostgresLimitWorkers, CaseFixtures, TransactionTestCase):
    def test_concurrent_same_token_creates_one_report_and_audit(self):
        self.service()
        token = uuid4()
        results = self.race(
            lambda: self.report_listing(client_token=token).record.pk,
            lambda: self.report_listing(client_token=token).record.pk,
        )
        self.assertEqual(results[0], results[1])
        self.assertEqual(ContentReport.objects.count(), 1)
        self.assertEqual(CaseAuditEvent.objects.count(), 1)
        self.assertEqual(CaseSubmissionReceipt.objects.count(), 1)

    def test_last_twentieth_report_slot_is_atomic(self):
        self.service()
        self.seed_quota(19)
        second = self.next_message()

        def submit(message_id):
            try:
                return self.report_message(message_id=message_id).disposition
            except ActionRateLimited:
                return "limited"

        outcomes = self.race(lambda: submit(self.message.pk), lambda: submit(second.pk))
        self.assertCountEqual(outcomes, ["created", "limited"])
        self.assertEqual(ContentReport.objects.count(), 20)
        self.assertEqual(CaseSubmissionReceipt.objects.count(), 1)
        self.assertEqual(CaseAuditEvent.objects.count(), 1)


class DecisionConcurrencyTests(DecisionCalls, PostgresLimitWorkers, CaseFixtures, TransactionTestCase):
    def test_opposing_report_decisions_produce_one_result(self):
        self.grant(self.case_reviewer, "review_reports")
        report = self.report_listing().record

        def decide(action):
            try:
                return self.decide(report, action=action,
                    expected_public_revision_id=self.public.pk if action == "hide_listing" else None).action
            except CaseConflict:
                return "conflict"

        results = self.race(lambda: decide("hide_listing"), lambda: decide("no_action"))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(ReportDecision.objects.count(), 1)
        self.assertLessEqual(Restriction.objects.count(), 1)
        self.assertEqual(CaseAuditEvent.objects.filter(action="report_decided").count(), 1)


from moderation.tests.test_appeals import AppealCalls, AppealFixtures
from moderation.models import Appeal, AppealDecision, MessagingRestriction
from moderation.messaging import revoke_messaging_restriction


class AppealConcurrencyTests(AppealCalls, PostgresLimitWorkers, AppealFixtures, TransactionTestCase):
    def test_same_token_concurrent_appeal_creates_one_receipt(self):
        token = uuid4()
        results = self.race(lambda: self.appeal(client_token=token).record.pk,
                            lambda: self.appeal(client_token=token).record.pk)
        self.assertEqual(results[0], results[1])
        self.assertEqual(Appeal.objects.count(), 1)
        self.assertEqual(CaseSubmissionReceipt.objects.filter(operation="appeal").count(), 1)
        self.assertEqual(CaseAuditEvent.objects.filter(action="appeal_created").count(), 1)

    def test_last_tenth_appeal_slot_is_atomic(self):
        self.appeal_service()
        decisions = self.message_decisions(11)
        for decision in decisions[:9]:
            self.appeal(actor=self.reporter, decision_id=decision.pk)

        def submit(decision):
            try:
                return self.appeal(actor=self.reporter, decision_id=decision.pk).disposition
            except ActionRateLimited:
                return "limited"

        self.assertCountEqual(self.race(lambda: submit(decisions[9]), lambda: submit(decisions[10])),
                              ["created", "limited"])
        self.assertEqual(Appeal.objects.count(), 10)

    def test_opposing_appeal_decisions_have_one_result(self):
        appeal = self.appeal().record

        def resolve(outcome):
            try:
                return self.resolve(appeal, outcome=outcome).outcome
            except CaseConflict:
                return "conflict"

        results = self.race(lambda: resolve("uphold"), lambda: resolve("revoke"))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(AppealDecision.objects.count(), 1)
        self.assertEqual(CaseAuditEvent.objects.filter(action="appeal_decided").count(), 1)

    def test_existing_message_revoke_and_appeal_revoke_keep_first_timestamp(self):
        self.appeal_service()
        decision = self.message_decisions(1)[0]
        self.grant(self.appeal_reviewer, "restrict_messaging")
        appeal = self.appeal(actor=self.reporter, decision_id=decision.pk).record
        results = self.race(
            lambda: revoke_messaging_restriction(actor=self.appeal_reviewer,
                restriction_id=decision.messaging_restriction_id).revoked_at,
            lambda: self.resolve(appeal).pk,
        )
        decision.messaging_restriction.refresh_from_db()
        self.assertEqual(decision.messaging_restriction.revoked_at, results[0])
        self.assertEqual(AppealDecision.objects.count(), 1)

    def test_expiry_while_reviewer_waits_does_not_lose_the_decision(self):
        decision = self.message_decisions(1)[0]
        self.grant(self.appeal_reviewer, "restrict_messaging")
        appeal = self.appeal(actor=self.reporter, decision_id=decision.pk).record
        self.ordered(
            lambda: MessagingRestriction.objects.filter(pk=decision.messaging_restriction_id).update(ends_at=timezone.now()),
            lambda: self.resolve(appeal).pk,
            [self.owner.pk, self.reporter.pk, self.case_reviewer.pk, self.appeal_reviewer.pk],
        )
        decision.messaging_restriction.refresh_from_db()
        self.assertLessEqual(decision.messaging_restriction.ends_at, decision.messaging_restriction.revoked_at)
        self.assertEqual(AppealDecision.objects.count(), 1)
