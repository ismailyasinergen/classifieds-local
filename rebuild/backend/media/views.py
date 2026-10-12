from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from listings.policies import require_active_actor
from .models import MediaAsset


def _authorized_asset(request, asset_id):
    require_active_actor(actor=request.user)
    asset = get_object_or_404(MediaAsset, pk=asset_id)
    if asset.owner_id != request.user.pk and not request.user.has_perm("listings.review_listingrevision"):
        raise PermissionDenied("Bu görseli görüntüleme yetkiniz yok.")
    return asset


def _private_response(response):
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _file_response(asset, field, mime, filename, *, as_attachment=True):
    file = getattr(asset, field)
    if not file.name:
        raise Http404()
    try:
        stream = file.open("rb")
    except FileNotFoundError:
        raise Http404() from None
    response = FileResponse(stream, content_type=mime, as_attachment=as_attachment, filename=filename)
    return _private_response(response)


@require_GET
def original(request, asset_id):
    asset = _authorized_asset(request, asset_id)
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[asset.source_mime]
    return _file_response(asset, "original", asset.source_mime, f"original.{extension}")


@require_GET
def derivative(request, asset_id):
    asset = _authorized_asset(request, asset_id)
    if asset.state != MediaAsset.State.READY:
        raise Http404()
    return _file_response(asset, "derivative", "image/jpeg", "preview.jpg", as_attachment=False)


@require_GET
def status(request, asset_id):
    asset = _authorized_asset(request, asset_id)
    return _private_response(JsonResponse({
        "id": asset.pk, "state": asset.state, "label": asset.get_state_display(),
        "attempts": asset.attempts, "error": asset.error_code,
        "can_retry": asset.state == MediaAsset.State.FAILED and asset.attempts < 3,
    }))
