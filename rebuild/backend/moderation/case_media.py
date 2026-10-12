from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from media.models import MediaAsset
from .case_audit import append_case_event
from .case_evidence import authorized_case
from .case_http import case_view
from .models import Appeal


@require_GET
@case_view
def case_media(request, report_id, asset_id, *, appeal_id=None):
    report, appeal = authorized_case(actor=request.user, report_id=report_id, appeal_id=appeal_id)
    if report.target_type != "listing" or asset_id not in report.evidence.get("asset_ids", []):
        raise Http404()
    asset = get_object_or_404(MediaAsset.objects.filter(state="ready").exclude(derivative=""),
        pk=asset_id, revision_images__revision_id=report.revision_id)
    try:
        stream = asset.derivative.open("rb")
    except OSError:
        raise Http404() from None
    try:
        with transaction.atomic():
            append_case_event(actor_id=request.user.pk, report_id=report.pk,
                appeal_id=appeal.pk if appeal else None, action="evidence_media_viewed")
    except Exception:
        stream.close()
        raise
    response = FileResponse(stream, content_type="image/jpeg", filename="case-preview.jpg")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "same-origin"
    return response


@require_GET
@case_view
def appeal_case_media(request, appeal_id, asset_id):
    appeal = get_object_or_404(Appeal.objects.select_related("decision"), pk=appeal_id)
    return case_media(request, appeal.decision.report_id, asset_id, appeal_id=appeal.pk)
