from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404

from .case_audit import append_case_event
from .case_policies import require_appeal_reviewer, require_report_reviewer
from .case_queries import decision_projection
from .models import Appeal, ContentReport
from .policies import visible_listings


def authorized_case(*, actor, report_id, appeal_id=None):
    report = get_object_or_404(ContentReport.objects.select_related("revision__listing", "message",
        "decision__visibility_restriction", "decision__messaging_restriction", "decision__appeal__result"), pk=report_id)
    appeal = None
    if appeal_id is None:
        require_report_reviewer(actor=actor, report=report)
    else:
        appeal = get_object_or_404(Appeal.objects.select_related("decision__report", "result"),
                                   pk=appeal_id, decision__report_id=report.pk)
        require_appeal_reviewer(actor=actor, decision=appeal.decision)
    evidence = report.evidence
    if not isinstance(evidence, dict) or evidence.get("schema_version") != 1:
        raise Http404()
    if report.target_type == "listing":
        if report.revision_id != evidence.get("revision_id"):
            raise Http404()
    elif (report.message_id != evidence.get("message_id")
            or report.message.sender_id != evidence.get("sender_id")
            or report.message.sender_id != report.subject_user_id):
        raise Http404()
    return report, appeal


def read_case_evidence(*, actor, report_id, appeal_id=None):
    with transaction.atomic():
        report, appeal = authorized_case(actor=actor, report_id=report_id, appeal_id=appeal_id)
        fields = ("schema_version", "revision_id", "title", "description", "price", "currency", "location",
                  "attributes", "category", "asset_ids") if report.target_type == "listing" else (
                  "schema_version", "message_id", "body", "created_at", "sender_id")
        result = dict(report_id=report.pk, target_type=report.target_type,
            reason_code=report.reason_code, explanation=report.explanation,
            evidence={field: report.evidence[field] for field in fields if field in report.evidence},
            decision_id=getattr(report, "decision", None).pk if getattr(report, "decision", None) else None,
            appeal_id=appeal.pk if appeal else None, appeal_explanation=appeal.explanation if appeal else None)
        decision = getattr(report, "decision", None)
        result["decision"] = decision_projection(decision) if decision else None
        if report.target_type == "listing":
            listing = report.revision.listing
            result["current_target"] = {
                "public_revision_id": listing.public_revision_id, "lifecycle": listing.lifecycle,
                "visible": visible_listings().filter(pk=listing.pk).exists(),
                "reported_revision_is_current": listing.public_revision_id == report.revision_id,
            }
        append_case_event(actor_id=actor.pk, report_id=report.pk,
                           appeal_id=appeal.pk if appeal else None, action="evidence_viewed")
        return result
