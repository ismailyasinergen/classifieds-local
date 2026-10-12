from datetime import timedelta
from importlib import import_module, util
from unittest.mock import patch
from uuid import uuid4

from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from accounts.rate_limits import ActionRateLimited
from conversations.models import UserBlock
from moderation.case_inputs import CaseConflict
from moderation.models import Appeal, AppealDecision, CaseAuditEvent, MessagingRestriction, Restriction
from moderation.tests.case_helpers import CaseFixtures
from moderation.tests.test_report_decisions import DecisionCalls


class AppealFixtures(CaseFixtures):
    def setUp(self):
        super().setUp()
        self.grant(self.case_reviewer, "review_reports")
        self.grant(self.appeal_reviewer, "review_appeals")
        self.report = self.report_listing().record
        self.decision = self.decide(self.report, action="hide_listing", expected_public_revision_id=self.public.pk)


class AppealCalls(DecisionCalls):
    def appeal_service(self):
        self.assertIsNotNone(util.find_spec("moderation.appeals"), "Appeal boundary is absent")
        return import_module("moderation.appeals")

    def appeal(self, **changes):
        return self.appeal_service().submit_appeal(**(dict(actor=self.owner, decision_id=self.decision.pk,
            explanation="Sentetik itiraz", client_token=uuid4()) | changes))

    def resolve(self, appeal, **changes):
        return self.appeal_service().decide_appeal(**(dict(actor=self.appeal_reviewer,
            appeal_id=appeal.pk, outcome="revoke", reason="Yeniden inceleme sonucu") | changes))

    def message_decisions(self, count):
        messages = [self.message] + [self.next_message() for _ in range(count - 1)]
        self.grant(self.case_reviewer, "restrict_messaging")
        return [self.decide(self.report_message(message_id=message.pk).record,
            action="restrict_messaging", ends_at=timezone.now() + timedelta(hours=1)) for message in messages]


class AppealTests(AppealCalls, AppealFixtures, TestCase):
    def test_only_current_verified_subject_can_appeal_a_sanction(self):
        self.appeal_service()
        with self.assertRaises(PermissionDenied):
            self.appeal(actor=self.reporter)
        EmailAddress.objects.filter(user=self.owner).update(verified=False)
        with self.assertRaises(PermissionDenied):
            self.appeal()
        EmailAddress.objects.filter(user=self.owner).update(verified=True)
        no_action = self.decide(self.report_message().record)
        with self.assertRaises(PermissionDenied):
            self.appeal(actor=self.reporter, decision_id=no_action.pk)
        self.assertEqual(Appeal.objects.count(), 0)

    def test_expired_and_already_revoked_sanctions_remain_appealable(self):
        self.appeal_service()
        Restriction.objects.filter(pk=self.decision.visibility_restriction_id).update(
            begins_at=timezone.now() - timedelta(days=2), ends_at=timezone.now() - timedelta(days=1),
            revoked_at=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.appeal().disposition, "created")

    def test_replay_and_alias_preserve_original_text_and_token_meaning(self):
        token, alias = uuid4(), uuid4()
        first = self.appeal(client_token=token)
        self.assertEqual(self.appeal(client_token=token).record.pk, first.record.pk)
        existing = self.appeal(client_token=alias, explanation="Yeni metin")
        self.assertEqual(existing.disposition, "existing_target")
        self.assertEqual(existing.record.explanation, "Sentetik itiraz")
        with self.assertRaises(CaseConflict):
            self.appeal(client_token=alias, explanation="Değişen metin")
        self.assertEqual(Appeal.objects.count(), 1)
        self.assertEqual(CaseAuditEvent.objects.filter(action="appeal_created").count(), 1)

    def test_first_reviewer_reporter_and_appellant_cannot_resolve_even_as_superuser(self):
        appeal = self.appeal().record
        for actor in (self.case_reviewer, self.reporter, self.owner):
            User.objects.filter(pk=actor.pk).update(is_superuser=True)
            with self.assertRaises(PermissionDenied):
                self.resolve(appeal, actor=actor)
        self.appeal_reviewer.user_permissions.clear()
        self.grant(self.appeal_reviewer, "review_reports")
        with self.assertRaises(PermissionDenied):
            self.resolve(appeal)
        self.assertEqual(AppealDecision.objects.count(), 0)

    def test_revoke_only_exact_restriction_preserves_lifecycle_other_restrictions_and_block(self):
        appeal = self.appeal().record
        other = Restriction.objects.create(seller=self.owner, actor=self.case_reviewer, reason="Başka kısıt")
        block = UserBlock.objects.create(blocker=self.owner, blocked=self.reporter)
        self.listing.lifecycle = "closed"
        self.listing.save()
        original = (self.decision.actor_id, self.decision.reason, self.decision.decided_at)
        self.resolve(appeal)
        self.decision.visibility_restriction.refresh_from_db()
        other.refresh_from_db()
        self.listing.refresh_from_db()
        self.decision.refresh_from_db()
        self.assertIsNotNone(self.decision.visibility_restriction.revoked_at)
        self.assertIsNone(other.revoked_at)
        self.assertEqual(self.listing.lifecycle, "closed")
        self.assertTrue(UserBlock.objects.filter(pk=block.pk).exists())
        self.assertEqual((self.decision.actor_id, self.decision.reason, self.decision.decided_at), original)

    def test_uphold_and_exact_replay_leave_restriction_unchanged(self):
        appeal = self.appeal().record
        first = self.resolve(appeal, outcome="uphold")
        self.assertEqual(self.resolve(appeal, outcome="uphold").pk, first.pk)
        with self.assertRaises(CaseConflict):
            self.resolve(appeal, outcome="revoke")
        self.decision.visibility_restriction.refresh_from_db()
        self.assertIsNone(self.decision.visibility_restriction.revoked_at)
        self.assertEqual(CaseAuditEvent.objects.filter(action="appeal_decided").count(), 1)

    def test_revoke_message_requires_extra_permission_and_preserves_prior_revocation(self):
        self.appeal_service()
        decision = self.message_decisions(1)[0]
        appeal = self.appeal(actor=self.reporter, decision_id=decision.pk).record
        with self.assertRaises(PermissionDenied):
            self.resolve(appeal)
        self.grant(self.appeal_reviewer, "restrict_messaging")
        at = timezone.now() - timedelta(seconds=1)
        MessagingRestriction.objects.filter(pk=decision.messaging_restriction_id).update(revoked_at=at)
        self.resolve(appeal)
        decision.messaging_restriction.refresh_from_db()
        self.assertEqual(decision.messaging_restriction.revoked_at, at)

    def test_audit_failure_rolls_back_revocation_and_appeal_result(self):
        appeal = self.appeal().record
        with patch("moderation.appeals.append_case_event", side_effect=RuntimeError("synthetic audit outage")):
            with self.assertRaises(RuntimeError):
                self.resolve(appeal)
        self.decision.visibility_restriction.refresh_from_db()
        self.assertIsNone(self.decision.visibility_restriction.revoked_at)
        self.assertEqual(AppealDecision.objects.count(), 0)

    def test_tenth_appeal_succeeds_eleventh_limited_and_replay_is_free(self):
        self.appeal_service()
        decisions = self.message_decisions(11)
        for decision in decisions[:9]:
            self.appeal(actor=self.reporter, decision_id=decision.pk)
        token = uuid4()
        tenth = self.appeal(actor=self.reporter, decision_id=decisions[9].pk, client_token=token)
        with self.assertRaises(ActionRateLimited) as caught:
            self.appeal(actor=self.reporter, decision_id=decisions[10].pk)
        self.assertGreater(caught.exception.retry_after, 0)
        self.assertEqual(self.appeal(actor=self.reporter, decision_id=decisions[9].pk,
                                     client_token=token).record.pk, tenth.record.pk)
        self.assertEqual(Appeal.objects.count(), 10)
