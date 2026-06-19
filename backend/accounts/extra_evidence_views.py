import hashlib
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from .models import ModerationAppeal, ModerationAppealAttachment


@login_required
def moderation_appeal_add_extra_evidence(request, pk):
    appeal = get_object_or_404(ModerationAppeal, pk=pk)

    if getattr(appeal, "appellant_id", None) != request.user.id:
        raise PermissionDenied("You can only upload evidence for your own appeal.")

    if request.method != "POST":
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    pending_status = getattr(getattr(ModerationAppeal, "Status", None), "PENDING", "pending")
    if getattr(appeal, "status", None) != pending_status:
        messages.error(request, "This appeal is no longer open for extra evidence.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    if not getattr(appeal, "extra_evidence_requested_at", None):
        messages.error(request, "Extra evidence has not been requested for this appeal.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    due_at = getattr(appeal, "extra_evidence_due_at", None)
    if due_at and due_at <= timezone.now():
        messages.error(request, "The extra evidence deadline has passed.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    files = request.FILES.getlist("attachments")
    if not files:
        messages.error(request, "Please choose at least one evidence file.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    attachment_fields = {field.name for field in ModerationAppealAttachment._meta.fields}

    file_field_name = "file"
    for field in ModerationAppealAttachment._meta.fields:
        if field.get_internal_type() == "FileField":
            file_field_name = field.name
            break

    existing_attachments = list(ModerationAppealAttachment.objects.filter(appeal=appeal))

    def attachment_size(attachment):
        for field_name in ("size", "file_size"):
            value = getattr(attachment, field_name, None)
            if value:
                return int(value)

        file_obj = getattr(attachment, file_field_name, None)
        try:
            return int(file_obj.size)
        except Exception:
            return 0

    existing_count = len(existing_attachments)
    existing_size = sum(attachment_size(attachment) for attachment in existing_attachments)

    max_files = 15
    max_total_size = 200 * 1024 * 1024

    if existing_count + len(files) > max_files:
        messages.error(request, "Maximum 15 total evidence files are allowed.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    incoming_size = sum(int(getattr(file_obj, "size", 0) or 0) for file_obj in files)
    if existing_size + incoming_size > max_total_size:
        messages.error(request, "Total appeal evidence cannot exceed 200 MB.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".mp4"}
    allowed_content_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "video/mp4",
    }

    existing_hashes = set()
    if "sha256" in attachment_fields:
        existing_hashes = set(
            ModerationAppealAttachment.objects
            .filter(appeal=appeal)
            .exclude(sha256="")
            .values_list("sha256", flat=True)
        )

    created = 0

    for uploaded_file in files:
        extension = Path(uploaded_file.name).suffix.lower()
        content_type = (getattr(uploaded_file, "content_type", "") or "").lower()

        if extension not in allowed_extensions or content_type not in allowed_content_types:
            messages.error(
                request,
                f"{uploaded_file.name}: invalid file type. Allowed: JPG, JPEG, PNG, WEBP, PDF, MP4.",
            )
            return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

        digest = None
        if "sha256" in attachment_fields:
            hasher = hashlib.sha256()
            for chunk in uploaded_file.chunks():
                hasher.update(chunk)
            digest = hasher.hexdigest()
            uploaded_file.seek(0)

            if digest in existing_hashes:
                messages.error(request, f"{uploaded_file.name}: duplicate evidence file.")
                return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

            existing_hashes.add(digest)

        attachment_kwargs = {
            "appeal": appeal,
            file_field_name: uploaded_file,
        }

        if "original_name" in attachment_fields:
            attachment_kwargs["original_name"] = uploaded_file.name

        if "content_type" in attachment_fields:
            attachment_kwargs["content_type"] = content_type

        if "size" in attachment_fields:
            attachment_kwargs["size"] = uploaded_file.size

        if "file_size" in attachment_fields:
            attachment_kwargs["file_size"] = uploaded_file.size

        if "sha256" in attachment_fields and digest:
            attachment_kwargs["sha256"] = digest

        if "uploaded_by" in attachment_fields:
            attachment_kwargs["uploaded_by"] = request.user

        if "evidence_stage" in attachment_fields:
            attachment_kwargs["evidence_stage"] = "extra"

        ModerationAppealAttachment.objects.create(**attachment_kwargs)
        created += 1

    if hasattr(appeal, "extra_evidence_fulfilled_at") and not appeal.extra_evidence_fulfilled_at:
        appeal.extra_evidence_fulfilled_at = timezone.now()
        appeal.save(update_fields=["extra_evidence_fulfilled_at"])

    messages.success(request, f"Uploaded {created} extra evidence file(s).")
    return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)
