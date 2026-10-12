from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from . import case_queries as queries
from .case_evidence import read_case_evidence
from .case_forms import ReportForm, ReportDecisionForm
from .case_http import case_view, form_page, history_page
from .case_locking import lock_case_target
from .report_decisions import decide_report
from .reports import require_report_target, submit_listing_report, submit_message_report


def _report(request, target_type, target_id):
    # POST authorization stays in the service so exact replay survives later hiding.
    if request.method == "GET":
        with transaction.atomic():
            target = lock_case_target(actor=request.user, target_type=target_type, target_id=target_id)
            require_report_target(target=target, at=timezone.now())
    form = ReportForm(request.POST if request.method == "POST" else None, target_type=target_type)
    def submit(data):
        service = submit_listing_report if target_type == "listing" else submit_message_report
        target = {"revision_id" if target_type == "listing" else "message_id": target_id}
        result = service(actor=request.user, **target, **data)
        if result.disposition == "existing_target":
            messages.info(request, "Bu içerik için önceki bildiriminiz gösteriliyor; yeni açıklama kaydedilmedi.")
        return redirect("moderation:report_detail", report_id=result.record.pk)
    return form_page(request, "report_form", form, {}, submit)


@require_http_methods(["GET", "POST"])
@case_view
def report_listing(request, revision_id):
    return _report(request, "listing", revision_id)


@require_http_methods(["GET", "POST"])
@case_view
def report_message(request, message_id):
    return _report(request, "message", message_id)


@require_GET
@case_view
def my_reports(request):
    return history_page(request, "my_reports", queries.my_reports(actor=request.user), queries.report_projection)


@require_GET
@case_view
def report_detail(request, report_id):
    return render(request, "moderation/cases/report_detail.html", {
        "item": queries.report_for_reporter(actor=request.user, report_id=report_id)})


@require_GET
@case_view
def my_decisions(request):
    return history_page(request, "my_decisions", queries.my_decisions(actor=request.user), queries.decision_projection)


@require_GET
@case_view
def decision_detail(request, decision_id):
    return render(request, "moderation/cases/decision_detail.html", {
        "item": queries.decision_for_subject(actor=request.user, decision_id=decision_id)})


@require_GET
@case_view
def report_queue(request):
    return history_page(request, "report_queue", queries.pending_reports(actor=request.user), queries.report_projection)


@require_http_methods(["GET", "POST"])
@case_view
def review_report(request, report_id):
    case = read_case_evidence(actor=request.user, report_id=report_id)
    form = ReportDecisionForm(request.POST if request.method == "POST" else None,
        target_type=case["target_type"], initial={"expected_public_revision_id": case["evidence"].get("revision_id")})
    def submit(data):
        decide_report(actor=request.user, report_id=report_id, **data)
        return redirect("moderation:review_report", report_id=report_id)
    return form_page(request, "review_report", form, {"case": case}, submit)
