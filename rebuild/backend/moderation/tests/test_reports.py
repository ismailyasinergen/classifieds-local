from datetime import timedelta
from importlib import import_module, util
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.rate_limits import ActionRateLimited
from conversations.models import Conversation, Message, Participant, UserBlock
from conversations.services import send_message
from events.models import OutboxEvent
from listings.models import Listing
from moderation.case_inputs import CaseConflict
from moderation.models import CaseAuditEvent, CaseSubmissionReceipt, ContentReport, MessagingRestriction, Restriction
from moderation.tests.case_helpers import CaseFixtures


class ReportCalls:
    def service(self):
        self.assertIsNotNone(util.find_spec("moderation.reports"), "Report submission boundary is absent")
        return import_module("moderation.reports")

    def report_listing(self, **changes):
        return self.service().submit_listing_report(**(dict(actor=self.reporter,
            revision_id=self.public.pk, reason_code="other", explanation="Sentetik bildirim",
            client_token=uuid4()) | changes))

    def report_message(self, **changes):
        return self.service().submit_message_report(**(dict(actor=self.owner,
            message_id=self.message.pk, reason_code="other", explanation="Sentetik bildirim",
            client_token=uuid4()) | changes))

    def next_message(self):
        return send_message(actor=self.reporter, conversation_id=self.conversation.pk,
                            body="Başka sentetik mesaj", client_token=uuid4())

    def seed_quota(self, count, at=None):
        for _ in range(count):
            message = self.next_message()
            ContentReport.objects.create(reporter=self.owner, subject_user=self.reporter,
                target_type="message", message=message, reason_code="other", explanation="Eski bildirim",
                evidence={"schema_version": 1}, client_token=uuid4(), created_at=at or timezone.now())

    def unchanged_state(self):
        return (
            *(model.objects.count() for model in (ContentReport, CaseSubmissionReceipt, CaseAuditEvent,
                Restriction, MessagingRestriction, OutboxEvent, Message)),
            list(Conversation.objects.order_by("pk").values_list("last_sequence", "last_message_at")),
            list(Participant.objects.order_by("pk").values_list("last_read_sequence", "archived_at")),
        )


class ReportTests(ReportCalls, CaseFixtures, TestCase):
    def test_listing_report_captures_exact_public_revision(self):
        before = OutboxEvent.objects.count()
        result = self.report_listing()
        self.assertEqual(result.disposition, "created")
        self.assertEqual(result.record.revision_id, self.public.pk)
        self.assertEqual(result.record.subject_user_id, self.owner.pk)
        evidence = result.record.evidence
        self.assertEqual(evidence["title"], "Araba")
        self.assertEqual(evidence["revision_id"], self.public.pk)
        self.assertEqual(evidence["price"], "1234.50")
        self.assertEqual(evidence["schema_version"], 1)
        self.assertNotIn("email", evidence)
        self.assertNotIn("original", evidence)
        self.assertEqual(Restriction.objects.count(), 0)
        self.assertEqual(OutboxEvent.objects.count(), before)

    def test_message_report_requires_recipient_and_current_participation(self):
        before = self.unchanged_state()
        for actor in (self.reporter, self.case_reviewer):
            with self.assertRaises(PermissionDenied):
                self.report_message(actor=actor)
        self.assertEqual(self.unchanged_state(), before)
        Participant.objects.filter(conversation=self.conversation, user=self.owner).delete()
        with self.assertRaises(PermissionDenied):
            self.report_message()
        self.assertEqual(ContentReport.objects.count(), 0)

    def test_hidden_foreign_or_own_target_leaves_zero_rows(self):
        self.service()
        for changes in ({"actor": self.owner},):
            before = self.unchanged_state()
            with self.assertRaises(PermissionDenied):
                self.report_listing(**changes)
            self.assertEqual(self.unchanged_state(), before)
        Restriction.objects.create(listing=self.listing, actor=self.case_reviewer, reason="Gizli")
        before = self.unchanged_state()
        with self.assertRaises(PermissionDenied):
            self.report_listing()
        self.assertEqual(self.unchanged_state(), before)
        draft = self.edit(self.public, title="Özel taslak")
        with self.assertRaises(PermissionDenied):
            self.report_listing(revision_id=draft.pk)

    def test_changed_public_revision_is_conflict(self):
        self.service()
        newer = self.submit(self.edit(self.public, title="Yeni içerik"))
        self.approve(newer, expected=self.public.pk)
        before = self.unchanged_state()
        with self.assertRaises(CaseConflict):
            self.report_listing()
        self.assertEqual(self.unchanged_state(), before)

    def test_exact_and_alias_replay_conflict_and_actor_isolation(self):
        token = uuid4()
        first = self.report_listing(client_token=token)
        before = self.unchanged_state()
        replay = self.report_listing(client_token=token)
        self.assertEqual((replay.record.pk, replay.disposition), (first.record.pk, "replayed"))
        self.assertEqual(self.unchanged_state(), before)
        with self.assertRaises(CaseConflict):
            self.report_listing(client_token=token, explanation="Farklı")
        alias = uuid4()
        existing = self.report_listing(client_token=alias, explanation="Yeni açıklama")
        self.assertEqual((existing.record.pk, existing.disposition), (first.record.pk, "existing_target"))
        first.record.refresh_from_db()
        self.assertEqual(first.record.explanation, "Sentetik bildirim")
        with self.assertRaises(CaseConflict):
            self.report_listing(client_token=alias, explanation="Başka açıklama")
        other = self.report_listing(actor=self.case_reviewer, client_token=token)
        self.assertNotEqual(first.record.pk, other.record.pk)
        self.assertEqual(CaseAuditEvent.objects.filter(action="report_created").count(), 2)

    def test_alias_token_cannot_move_to_another_target(self):
        first = self.report_message()
        alias = uuid4()
        self.assertEqual(self.report_message(client_token=alias).record.pk, first.record.pk)
        other = self.next_message()
        with self.assertRaises(CaseConflict):
            self.report_message(client_token=alias, message_id=other.pk)
        self.assertEqual(ContentReport.objects.count(), 1)

    def test_replay_of_own_success_survives_later_hiding(self):
        token = uuid4()
        first = self.report_listing(client_token=token)
        Restriction.objects.create(listing=self.listing, actor=self.case_reviewer, reason="Gizli")
        self.assertEqual(self.report_listing(client_token=token).record.pk, first.record.pk)
        self.reporter.is_active = False
        self.reporter.save()
        with self.assertRaises(PermissionDenied):
            self.report_listing(client_token=token)

    def test_restricted_archived_recipient_can_report_without_history_changes(self):
        self.service()
        UserBlock.objects.create(blocker=self.owner, blocked=self.reporter)
        MessagingRestriction.objects.create(user=self.owner, actor=self.case_reviewer, reason="Kısıt")
        Participant.objects.filter(conversation=self.conversation).update(archived_at=timezone.now())
        Listing.objects.filter(pk=self.listing.pk).update(lifecycle="closed")
        history = self.unchanged_state()[7:]
        result = self.report_message()
        self.assertEqual(result.record.evidence["body"], "Sentetik mesaj")
        self.assertEqual(result.record.evidence["message_id"], self.message.pk)
        self.assertEqual(self.unchanged_state()[7:], history)

    def test_invalid_input_and_audit_failure_have_no_side_effects(self):
        self.service()
        before = self.unchanged_state()
        for changes in ({"reason_code": "harassment"}, {"explanation": " "},
                        {"explanation": "x\x00"}, {"client_token": True}):
            with self.assertRaises(ValidationError):
                self.report_listing(**changes)
        with patch("moderation.reports.append_case_event", side_effect=RuntimeError("synthetic audit outage")):
            with self.assertRaises(RuntimeError):
                self.report_listing()
        self.assertEqual(self.unchanged_state(), before)

    def test_twentieth_succeeds_twenty_first_rejected_replay_at_capacity(self):
        self.service()
        self.seed_quota(19)
        token = uuid4()
        first = self.report_message(client_token=token)
        other = self.next_message()
        before = self.unchanged_state()
        with self.assertRaises(ActionRateLimited) as caught:
            self.report_message(message_id=other.pk)
        self.assertGreater(caught.exception.retry_after, 0)
        self.assertEqual(self.unchanged_state(), before)
        self.assertEqual(self.report_message(client_token=token).record.pk, first.record.pk)

    def test_exact_window_boundary_expires(self):
        self.service()
        at = timezone.now()
        self.seed_quota(20, at=at - timedelta(days=1))
        with patch("moderation.reports.timezone.now", return_value=at):
            self.assertEqual(self.report_message().disposition, "created")
