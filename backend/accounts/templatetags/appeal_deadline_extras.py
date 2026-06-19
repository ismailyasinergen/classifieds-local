from datetime import timedelta

from django import template
from django.utils import timezone

from accounts.models import ModerationAppeal

register = template.Library()


@register.simple_tag
def appeal_deadline_counts():
    now = timezone.now()
    due_soon_limit = now + timedelta(days=15)

    base = ModerationAppeal.objects.filter(
        status=ModerationAppeal.Status.PENDING,
    )

    requested_unfulfilled = base.filter(
        extra_evidence_requested_at__isnull=False,
        extra_evidence_due_at__isnull=False,
        extra_evidence_fulfilled_at__isnull=True,
    )

    return {
        "overdue": requested_unfulfilled.filter(extra_evidence_due_at__lte=now).count(),
        "due_soon": requested_unfulfilled.filter(
            extra_evidence_due_at__gt=now,
            extra_evidence_due_at__lte=due_soon_limit,
        ).count(),
        "waiting": requested_unfulfilled.filter(extra_evidence_due_at__gt=due_soon_limit).count(),
        "uploaded": base.filter(
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=False,
        ).count(),
        "not_requested": base.filter(extra_evidence_requested_at__isnull=True).count(),
    }
