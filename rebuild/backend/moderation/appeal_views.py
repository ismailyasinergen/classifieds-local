from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from . import case_queries as queries
from .appeals import submit_appeal as create_appeal, decide_appeal
from .case_evidence import read_case_evidence
from .case_forms import AppealForm, AppealDecisionForm
from .case_http import case_view, form_page, history_page
from .models import Appeal


@require_http_methods(["GET", "POST"])
@case_view
def submit_appeal(request, decision_id):
    decision = queries.decision_for_subject(actor=request.user, decision_id=decision_id)
    form = AppealForm(request.POST if request.method == "POST" else None)
    def submit(data):
        result = create_appeal(actor=request.user, decision_id=decision_id, **data)
        if result.disposition == "existing_target":
            messages.info(request, "Bu karar için önceki itirazınız gösteriliyor; yeni açıklama kaydedilmedi.")
        return redirect("moderation:appeal_detail", appeal_id=result.record.pk)
    return form_page(request, "appeal_form", form, {"item": decision}, submit)


@require_GET
@case_view
def appeal_detail(request, appeal_id):
    return render(request, "moderation/cases/appeal_detail.html", {
        "item": queries.appeal_for_appellant(actor=request.user, appeal_id=appeal_id)})


@require_GET
@case_view
def appeal_queue(request):
    return history_page(request, "appeal_queue", queries.pending_appeals(actor=request.user),
        lambda row: {"id": row.pk, "title": queries.target_title(row.decision.report), "created_at": row.created_at})


@require_http_methods(["GET", "POST"])
@case_view
def review_appeal(request, appeal_id):
    appeal = get_object_or_404(Appeal.objects.only("decision__report_id").select_related("decision"), pk=appeal_id)
    case = read_case_evidence(actor=request.user, report_id=appeal.decision.report_id, appeal_id=appeal_id)
    form = AppealDecisionForm(request.POST if request.method == "POST" else None)
    def submit(data):
        decide_appeal(actor=request.user, appeal_id=appeal_id, **data)
        return redirect("moderation:review_appeal", appeal_id=appeal_id)
    return form_page(request, "review_appeal", form, {"case": case}, submit)
