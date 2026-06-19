# PRIVATE_MEDIA_VIEWS_V1
from pathlib import Path

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404


PRIVATE_FIELD_NAMES = {
    "verification_document",
    "verification_file",
    "business_document",
    "document_file",
    "identity_document",
    "payment_proof",
    "proof",
    "proof_file",
    "receipt",
    "receipt_file",
    "payment_receipt",
    "transfer_receipt",
    "bank_receipt",
    "file",
}

PRIVATE_PATH_PARTS = {
    "appeal_attachments",
    "verification",
    "verification_documents",
    "verification_docs",
    "seller_verification",
    "payment_proofs",
    "promotion_proofs",
    "proofs",
    "receipts",
    "payment_receipts",
}


def _safe_filename(name):
    name = Path(name or "private-file").name
    name = name.replace("/", "_").replace("\\", "_")
    return name or "private-file"


def _same_user(user, candidate):
    return bool(candidate and getattr(candidate, "id", None) == user.id)


def _user_can_access_object_file(user, obj):
    if not user.is_authenticated:
        return False

    if user.is_staff:
        return True

    user_fields = [
        "user",
        "owner",
        "seller",
        "appellant",
        "recipient",
        "reporter",
        "buyer",
        "customer",
        "created_by",
        "submitted_by",
        "requested_by",
    ]

    for field_name in user_fields:
        candidate = getattr(obj, field_name, None)
        if _same_user(user, candidate):
            return True

    listing = getattr(obj, "listing", None) or getattr(obj, "source_listing", None)
    if listing and _same_user(user, getattr(listing, "owner", None)):
        return True

    appeal = getattr(obj, "appeal", None)
    if appeal and _same_user(user, getattr(appeal, "appellant", None)):
        return True

    notice = getattr(obj, "moderation_notice", None)
    if notice and _same_user(user, getattr(notice, "recipient", None)):
        return True

    profile_user = getattr(obj, "profile", None)
    if profile_user and _same_user(user, getattr(profile_user, "user", None)):
        return True

    return False


@login_required
def private_file_download(request, app_label, model_name, pk, field_name):
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        raise Http404("File not found.")

    obj = get_object_or_404(model, pk=pk)

    try:
        field = model._meta.get_field(field_name)
    except FieldDoesNotExist:
        raise Http404("File not found.")

    if not isinstance(field, (models.FileField, models.ImageField)):
        raise Http404("File not found.")

    file_obj = getattr(obj, field_name, None)

    if not file_obj:
        raise Http404("File not found.")

    file_name_lower = str(getattr(file_obj, "name", "") or "").lower()
    field_name_lower = field_name.lower()

    is_private_field = field_name_lower in PRIVATE_FIELD_NAMES
    is_private_path = any(part in file_name_lower for part in PRIVATE_PATH_PARTS)

    if not is_private_field and not is_private_path:
        raise Http404("File not found.")

    if not _user_can_access_object_file(request.user, obj):
        raise Http404("File not found.")

    try:
        file_handle = file_obj.open("rb")
    except FileNotFoundError:
        raise Http404("File not found.")

    as_attachment = request.GET.get("download") == "1"
    filename = _safe_filename(getattr(file_obj, "name", ""))

    if hasattr(obj, "original_name") and getattr(obj, "original_name"):
        filename = _safe_filename(obj.original_name)

    response = FileResponse(
        file_handle,
        content_type=getattr(obj, "content_type", "") or "application/octet-stream",
        as_attachment=as_attachment,
        filename=filename,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
