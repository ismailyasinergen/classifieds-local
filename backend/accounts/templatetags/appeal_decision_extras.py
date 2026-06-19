from django import template
from django.utils import timezone

from accounts.models import ModerationAppeal

register = template.Library()


@register.simple_tag
def appeal_decision_state(appeal):
    now = timezone.now()

    if appeal.status != ModerationAppeal.Status.PENDING:
        return {
            "ready": False,
            "state": "final_locked",
            "label": "Final decision locked",
            "reason": "This appeal already has a final approved/rejected decision.",
            "due_iso": "",
        }

    if not getattr(appeal, "extra_evidence_requested_at", None):
        return {
            "ready": True,
            "state": "ready_no_extra_request",
            "label": "Ready for final decision",
            "reason": "No extra evidence was requested.",
            "due_iso": "",
        }

    if getattr(appeal, "extra_evidence_fulfilled_at", None):
        return {
            "ready": True,
            "state": "ready_uploaded",
            "label": "Ready for final decision",
            "reason": "Seller uploaded the requested extra evidence.",
            "due_iso": "",
        }

    due_at = getattr(appeal, "extra_evidence_due_at", None)

    if due_at and due_at <= now:
        return {
            "ready": True,
            "state": "ready_deadline_passed",
            "label": "Ready for final decision",
            "reason": "The extra evidence deadline passed without seller upload.",
            "due_iso": "",
        }

    due_iso = timezone.localtime(due_at).isoformat() if due_at else ""

    return {
        "ready": False,
        "state": "waiting_deadline",
        "label": "Waiting for seller evidence",
        "reason": "The seller still has time to upload the requested extra evidence.",
        "due_iso": due_iso,
    }
