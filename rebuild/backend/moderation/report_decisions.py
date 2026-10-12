from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .case_audit import append_case_event
from .case_inputs import CaseConflict, normalize_text
from .case_locking import lock_report_case
from .case_policies import require_report_reviewer
from .messaging import restrict_messaging
from .models import ReportDecision, Restriction


def decide_report(*, actor, report_id, action, reason, expected_public_revision_id=None, ends_at=None):
    reason = normalize_text(reason, field="reason")
    if action not in ReportDecision.Action.values:
        raise ValidationError({"action": "Geçerli bir karar seçin."})
    if ends_at is not None and (not isinstance(ends_at, datetime) or timezone.is_naive(ends_at)):
        raise ValidationError({"ends_at": "Saat dilimi içeren geçerli bitiş zamanı girin."})
    if action != "restrict_messaging" and ends_at is not None:
        raise ValidationError({"ends_at": "Bu karar bitiş zamanı kullanmaz."})
    with transaction.atomic():
        case = lock_report_case(actor=actor, report_id=report_id)
        report, target = case.report, case.target
        current = require_report_reviewer(actor=target.actor, report=report)
        subject_id = target.listing.owner_id if target.listing else target.message.sender_id
        if report.subject_user_id != subject_id:
            raise CaseConflict("identity_changed")
        if ((action == "hide_listing" and report.target_type != "listing")
                or (action == "restrict_messaging" and report.target_type != "message")):
            raise ValidationError({"action": "Karar bildirilen içerik türüyle eşleşmiyor."})
        if action == "restrict_messaging" and not current.has_perm("moderation.restrict_messaging"):
            raise PermissionDenied("Mesajlaşma kısıtlama izniniz yok.")
        if case.decision is not None:
            decision = case.decision
            previous_end = decision.messaging_restriction.ends_at if decision.messaging_restriction_id else None
            if ((decision.actor_id, decision.action, decision.reason, previous_end)
                    != (current.pk, action, reason, ends_at)
                    or (action == "hide_listing" and expected_public_revision_id != report.revision_id)):
                raise CaseConflict("decision_conflict")
            return decision
        now = timezone.now()
        visibility = messaging = None
        if action == "hide_listing":
            if (type(expected_public_revision_id) is not int
                    or target.listing.public_revision_id != report.revision_id
                    or expected_public_revision_id != report.revision_id
                    or target.listing.lifecycle != "live"):
                raise CaseConflict("stale_public_revision")
            visibility = Restriction.objects.create(listing=target.listing, actor=current,
                                                     reason=reason, begins_at=now)
        elif action == "restrict_messaging":
            if ends_at is None or ends_at <= now:
                raise ValidationError({"ends_at": "Gelecekteki bir bitiş zamanı girin."})
            messaging = restrict_messaging(actor=current, user_id=report.subject_user_id,
                                            reason=reason, ends_at=ends_at)
        decision = ReportDecision.objects.create(report=report, actor=current, action=action,
            reason=reason, decided_at=now, visibility_restriction=visibility, messaging_restriction=messaging)
        append_case_event(actor_id=current.pk, report_id=report.pk, action="report_decided")
        return decision
