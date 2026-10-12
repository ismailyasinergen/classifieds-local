from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .case_policies import require_appeal_reviewer, require_case_actor, require_report_reviewer
from .models import Appeal, ContentReport, ReportDecision

DECISION_RELATIONS = ("report", "visibility_restriction", "messaging_restriction", "appeal__result")


def my_reports(*, actor):
    current = require_case_actor(actor=actor)
    return ContentReport.objects.filter(reporter_id=current.pk).select_related("decision").order_by("-created_at", "-pk")


def my_decisions(*, actor):
    current = require_case_actor(actor=actor)
    return ReportDecision.objects.filter(report__subject_user_id=current.pk).exclude(action="no_action").select_related(
        *DECISION_RELATIONS).order_by("-decided_at", "-pk")


def pending_reports(*, actor):
    current = require_report_reviewer(actor=actor)
    return ContentReport.objects.filter(decision__isnull=True).exclude(
        Q(reporter_id=current.pk) | Q(subject_user_id=current.pk)).select_related("decision").order_by("created_at", "pk")


def pending_appeals(*, actor):
    current = require_appeal_reviewer(actor=actor)
    return Appeal.objects.filter(result__isnull=True).exclude(
        Q(appellant_id=current.pk) | Q(decision__actor_id=current.pk)
        | Q(decision__report__reporter_id=current.pk)).select_related(
            "decision__report", "result").order_by("created_at", "pk")


def target_title(report):
    return report.evidence.get("title", "Bildirilen ilan") if report.target_type == "listing" else "Bildirilen mesaj"


def report_projection(report):
    return dict(id=report.pk, target_type=report.target_type, title=target_title(report),
        reason_code=report.reason_code, explanation=report.explanation, created_at=report.created_at,
        status="resolved" if getattr(report, "decision", None) else "pending")


def decision_projection(decision):
    restriction = decision.visibility_restriction or decision.messaging_restriction
    at = timezone.now()
    state = "none"
    if restriction:
        state = ("revoked" if restriction.revoked_at else "expired" if restriction.ends_at and restriction.ends_at <= at
                 else "scheduled" if restriction.begins_at > at else "active")
    appeal = getattr(decision, "appeal", None)
    result = getattr(appeal, "result", None) if appeal else None
    return dict(id=decision.pk, target_type=decision.report.target_type, title=target_title(decision.report),
        action=decision.action, reason=decision.reason, decided_at=decision.decided_at, state=state,
        starts_at=restriction.begins_at if restriction else None,
        ends_at=restriction.ends_at if restriction else None, revoked_at=restriction.revoked_at if restriction else None,
        appeal_id=appeal.pk if appeal else None, appeal_outcome=result.outcome if result else None,
        appeal_reason=result.reason if result else None)


def report_for_reporter(*, actor, report_id):
    return report_projection(get_object_or_404(my_reports(actor=actor), pk=report_id))


def decision_for_subject(*, actor, decision_id):
    return decision_projection(get_object_or_404(my_decisions(actor=actor), pk=decision_id))


def appeal_for_appellant(*, actor, appeal_id):
    current = require_case_actor(actor=actor)
    appeal = get_object_or_404(Appeal.objects.select_related(
        "decision__report", "decision__visibility_restriction", "decision__messaging_restriction", "result"),
        pk=appeal_id, appellant_id=current.pk)
    result = getattr(appeal, "result", None)
    return dict(id=appeal.pk, decision_id=appeal.decision_id, title=target_title(appeal.decision.report),
        explanation=appeal.explanation, created_at=appeal.created_at,
        outcome=result.outcome if result else None, reason=result.reason if result else None)
