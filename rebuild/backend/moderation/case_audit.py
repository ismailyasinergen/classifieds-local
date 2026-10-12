from .models import CaseAuditEvent
from .submission_receipts import require_atomic


def append_case_event(*, actor_id, report_id, action, appeal_id=None):
    require_atomic()
    return CaseAuditEvent.objects.create(actor_id=actor_id, report_id=report_id,
                                         action=action, appeal_id=appeal_id)
