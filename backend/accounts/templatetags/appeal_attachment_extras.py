import os

from django import template

register = template.Library()


@register.filter
def attachment_name(attachment):
    return (
        getattr(attachment, "original_name", "")
        or os.path.basename(getattr(getattr(attachment, "file", None), "name", "") or "")
        or f"Evidence #{attachment.pk}"
    )


@register.filter
def attachment_size(attachment):
    for field_name in ("size", "file_size"):
        value = getattr(attachment, field_name, None)
        if value:
            return value

    file_obj = getattr(attachment, "file", None)

    try:
        return file_obj.size
    except Exception:
        return 0


@register.filter
def attachments_total_size(attachments):
    total = 0
    for attachment in attachments:
        total += int(attachment_size(attachment) or 0)
    return total


@register.filter
def attachment_kind(attachment):
    name = attachment_name(attachment).lower()
    content_type = (getattr(attachment, "content_type", "") or "").lower()

    if content_type.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "image"

    if content_type.startswith("video/") or name.endswith(".mp4"):
        return "video"

    if content_type == "application/pdf" or name.endswith(".pdf"):
        return "pdf"

    return "file"


@register.filter
def attachment_preview_url(attachment):
    return f"/accounts/appeals/attachments/{attachment.pk}/download/?preview=1"


@register.filter
def attachment_download_url(attachment):
    return f"/accounts/appeals/attachments/{attachment.pk}/download/"


@register.filter
def attachment_stage_label(attachment):
    stage = getattr(attachment, "evidence_stage", "")

    if stage == "extra":
        return "Extra evidence"

    if stage == "initial":
        return "Initial appeal evidence"

    return "Submitted evidence"


    if not appeal:
        return "Submitted evidence"

    requested_at = getattr(appeal, "extra_evidence_requested_at", None)

    timestamp_candidates = [
        value
        for value in (
            getattr(attachment, "created_at", None),
            getattr(attachment, "uploaded_at", None),
        )
        if value
    ]

    uploaded_at = min(timestamp_candidates) if timestamp_candidates else None

    if requested_at and uploaded_at and uploaded_at >= requested_at:
        return "Extra evidence"

    return "Initial appeal evidence"
