from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.rate_limits import enforce_action_limit
from conversations.models import Participant
from media.models import RevisionImage
from .case_audit import append_case_event
from .case_inputs import (
    CaseConflict, LISTING_REASONS, MESSAGE_REASONS, SubmissionResult,
    normalize_text, parse_client_token, submission_fingerprint,
)
from .case_locking import lock_case_target
from .case_policies import require_case_actor
from .models import ContentReport
from .policies import visible_listings
from .submission_receipts import lookup_receipt, record_receipt


def require_report_target(*, target, at):
    """Current object authorization, also used by the form GET boundary."""
    if target.listing is not None:
        if target.actor.pk == target.listing.owner_id or target.revision.status != "approved":
            raise PermissionDenied("Bu içerik bildirilemez.")
        if target.listing.public_revision_id != target.revision.pk:
            raise CaseConflict("stale_public_revision")
        if not visible_listings(at=at).filter(pk=target.listing.pk).exists():
            raise PermissionDenied("Bu içerik bildirilemez.")
        return target.listing.owner_id
    conversation, message = target.conversation, target.message
    if (target.actor.pk not in (conversation.initiator_id, conversation.recipient_id)
            or message.sender_id == target.actor.pk
            or message.sender_id not in (conversation.initiator_id, conversation.recipient_id)
            or not Participant.objects.filter(conversation=conversation, user_id=target.actor.pk).exists()):
        raise PermissionDenied("Bu içerik bildirilemez.")
    return message.sender_id


def _evidence(target):
    if target.revision is not None:
        revision = target.revision
        return dict(schema_version=1, revision_id=revision.pk, title=revision.title,
            description=revision.description, price=str(revision.price) if revision.price is not None else None,
            currency=revision.currency, location=revision.location, attributes=revision.attributes,
            category=revision.category.name, asset_ids=list(RevisionImage.objects.filter(
                revision=revision, asset__state="ready").exclude(asset__derivative="")
                .values_list("asset_id", flat=True)))
    message = target.message
    return dict(schema_version=1, message_id=message.pk, body=message.body,
                created_at=message.created_at.isoformat(), sender_id=message.sender_id)


def _submit(*, actor, target_type, target_id, reason_code, explanation, client_token):
    require_case_actor(actor=actor)
    if type(target_id) is not int or target_id < 1:
        raise ValidationError("Geçersiz içerik kimliği.")
    choices = LISTING_REASONS if target_type == "listing" else MESSAGE_REASONS
    if not isinstance(reason_code, str) or reason_code not in dict(choices):
        raise ValidationError({"reason_code": "Bu içerik için geçerli bir neden seçin."})
    explanation = normalize_text(explanation, field="explanation")
    token = parse_client_token(client_token)
    fingerprint = submission_fingerprint(operation="report", target_type=target_type,
        target_id=target_id, reason_code=reason_code, explanation=explanation)
    with transaction.atomic():
        target = lock_case_target(actor=actor, target_type=target_type, target_id=target_id)
        current = require_case_actor(actor=target.actor)
        receipt = lookup_receipt(actor_id=current.pk, operation="report", token=token, fingerprint=fingerprint)
        if receipt is not None:
            record = ContentReport.objects.get(pk=receipt.report_id, reporter_id=current.pk)
            return SubmissionResult(record, "replayed")
        now = timezone.now()
        subject_id = require_report_target(target=target, at=now)
        target_field = "revision_id" if target_type == "listing" else "message_id"
        existing = ContentReport.objects.filter(reporter_id=current.pk, **{target_field: target_id}).first()
        if existing is not None:
            record_receipt(actor_id=current.pk, operation="report", token=token,
                           fingerprint=fingerprint, report_id=existing.pk)
            return SubmissionResult(existing, "existing_target")
        enforce_action_limit(events=ContentReport.objects.filter(reporter_id=current.pk), action="report", at=now)
        report = ContentReport.objects.create(reporter=current, subject_user_id=subject_id,
            target_type=target_type, **{target_field: target_id}, reason_code=reason_code,
            explanation=explanation, evidence=_evidence(target), client_token=token, created_at=now)
        record_receipt(actor_id=current.pk, operation="report", token=token,
                       fingerprint=fingerprint, report_id=report.pk)
        append_case_event(actor_id=current.pk, report_id=report.pk, action="report_created")
        return SubmissionResult(report, "created")


def submit_listing_report(*, actor, revision_id, reason_code, explanation, client_token):
    return _submit(actor=actor, target_type="listing", target_id=revision_id,
                   reason_code=reason_code, explanation=explanation, client_token=client_token)


def submit_message_report(*, actor, message_id, reason_code, explanation, client_token):
    return _submit(actor=actor, target_type="message", target_id=message_id,
                   reason_code=reason_code, explanation=explanation, client_token=client_token)
