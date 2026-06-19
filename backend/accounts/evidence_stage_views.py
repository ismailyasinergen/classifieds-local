from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect

from .models import ModerationAppealAttachment, TrustSafetyEvent


@staff_member_required
def moderation_appeal_attachment_update_stage(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required.")

    attachment = get_object_or_404(ModerationAppealAttachment, pk=pk)
    old_stage = attachment.evidence_stage
    new_stage = request.POST.get("evidence_stage")

    if new_stage not in {"initial", "extra"}:
        return HttpResponseBadRequest("Invalid evidence stage.")

    if old_stage != new_stage:
        attachment.evidence_stage = new_stage
        attachment.save(update_fields=["evidence_stage"])

        try:
            fields = {field.name for field in TrustSafetyEvent._meta.fields}
            data = {}

            if "actor" in fields:
                data["actor"] = request.user
            if "user" in fields:
                data["user"] = getattr(attachment.appeal, "appellant", None)
            if "event_type" in fields:
                data["event_type"] = "appeal_evidence_stage_corrected"
            if "action" in fields:
                data["action"] = "appeal_evidence_stage_corrected"
            if "object_type" in fields:
                data["object_type"] = "moderation_appeal_attachment"
            if "object_id" in fields:
                data["object_id"] = str(attachment.pk)
            if "target_model" in fields:
                data["target_model"] = "ModerationAppealAttachment"
            if "target_id" in fields:
                data["target_id"] = str(attachment.pk)
            if "metadata" in fields:
                data["metadata"] = {
                    "appeal_id": attachment.appeal_id,
                    "attachment_id": attachment.pk,
                    "old_stage": old_stage,
                    "new_stage": new_stage,
                }
            if "details" in fields:
                data["details"] = (
                    f"Appeal evidence label changed from {old_stage} to {new_stage} "
                    f"for attachment #{attachment.pk} on appeal #{attachment.appeal_id}."
                )
            if "note" in fields:
                data["note"] = (
                    f"Appeal evidence label changed from {old_stage} to {new_stage} "
                    f"for attachment #{attachment.pk} on appeal #{attachment.appeal_id}."
                )

            if data:
                TrustSafetyEvent.objects.create(**data)
        except Exception:
            # Label correction must not fail only because audit schema differs.
            pass

        messages.success(request, "Evidence label updated.")
    else:
        messages.info(request, "Evidence label was already set to that value.")

    return redirect("accounts:moderation_appeal_admin_detail", pk=attachment.appeal_id)
