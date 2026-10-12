from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError

from accounts.locking import lock_users
from accounts.models import User
from conversations.models import Conversation, Message
from listings.models import Listing, ListingRevision
from .case_inputs import CaseConflict
from .models import Appeal, AppealDecision, ContentReport, ReportDecision
from .submission_receipts import require_atomic


@dataclass(frozen=True)
class LockedTarget:
    actor: User
    users: dict[int, User]
    listing: Listing | None = None
    revision: ListingRevision | None = None
    conversation: Conversation | None = None
    message: Message | None = None


@dataclass(frozen=True)
class LockedCase:
    target: LockedTarget
    report: ContentReport
    decision: ReportDecision | None
    appeal: Appeal | None
    appeal_decision: AppealDecision | None


def lock_case_target(*, actor, target_type, target_id, extra_user_ids=()):
    require_atomic()
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        raise PermissionDenied("Giriş yapın.")
    if target_type == "listing":
        parent_id = ListingRevision.objects.values_list("listing_id", flat=True).get(pk=target_id)
        listing = Listing.objects.select_for_update().get(pk=parent_id)
        users = lock_users(user_ids=[actor.pk, listing.owner_id, *extra_user_ids])
        revision = ListingRevision.objects.select_for_update().get(pk=target_id)
        if revision.listing_id != listing.pk:
            raise CaseConflict("identity_changed")
        return LockedTarget(actor=users[actor.pk], users=users, listing=listing, revision=revision)
    if target_type == "message":
        identity = Message.objects.values_list("conversation_id", "sender_id").get(pk=target_id)
        parties = Conversation.objects.values_list("initiator_id", "recipient_id").get(pk=identity[0])
        users = lock_users(user_ids=[actor.pk, identity[1], *parties, *extra_user_ids])
        conversation = Conversation.objects.select_for_update().get(pk=identity[0])
        message = Message.objects.select_for_update().get(pk=target_id)
        if ((message.conversation_id, message.sender_id) != identity
                or (conversation.initiator_id, conversation.recipient_id) != parties):
            raise CaseConflict("identity_changed")
        return LockedTarget(actor=users[actor.pk], users=users, conversation=conversation, message=message)
    raise ValidationError("Geçersiz bildirim hedefi.")


def lock_report_case(*, actor, report_id, extra_user_ids=()):
    require_atomic()
    before = ContentReport.objects.get(pk=report_id)
    decision_actor = ReportDecision.objects.filter(report_id=report_id).values_list("actor_id", flat=True).first()
    users = [before.reporter_id, before.subject_user_id, *extra_user_ids]
    if decision_actor is not None:
        users.append(decision_actor)
    target_id = before.revision_id if before.target_type == "listing" else before.message_id
    target = lock_case_target(actor=actor, target_type=before.target_type,
                              target_id=target_id, extra_user_ids=users)
    report = ContentReport.objects.select_for_update().get(pk=report_id)
    fields = ("target_type", "revision_id", "message_id", "reporter_id", "subject_user_id")
    if any(getattr(before, field) != getattr(report, field) for field in fields):
        raise CaseConflict("identity_changed")
    decision = ReportDecision.objects.select_for_update().filter(report=report).first()
    if decision is not None and decision.actor_id not in target.users:
        # A decision appeared while acquiring anchors; retry with the complete user set.
        raise CaseConflict("identity_changed")
    appeal = Appeal.objects.select_for_update().filter(decision=decision).first() if decision else None
    result = AppealDecision.objects.select_for_update().filter(appeal=appeal).first() if appeal else None
    if decision:
        decision.report = report
    return LockedCase(target=target, report=report, decision=decision, appeal=appeal, appeal_decision=result)
