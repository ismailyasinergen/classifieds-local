from django.db import migrations


def backfill_evidence_stage(apps, schema_editor):
    ModerationAppealAttachment = apps.get_model("accounts", "ModerationAppealAttachment")

    for attachment in ModerationAppealAttachment.objects.select_related("appeal").all():
        name = (
            getattr(attachment, "original_name", "")
            or getattr(getattr(attachment, "file", None), "name", "")
            or ""
        )

        lower_name = name.lower()

        if (
            lower_name.startswith("extra_")
            or "/extra_" in lower_name
            or "extra_requested" in lower_name
            or "followup" in lower_name
        ):
            stage = "extra"
        elif (
            lower_name.startswith("initial_")
            or "/initial_" in lower_name
            or "initial_original" in lower_name
        ):
            stage = "initial"
        else:
            requested_at = getattr(attachment.appeal, "extra_evidence_requested_at", None)
            uploaded_at = getattr(attachment, "created_at", None) or getattr(attachment, "uploaded_at", None)

            if requested_at and uploaded_at and uploaded_at >= requested_at:
                stage = "extra"
            else:
                stage = "initial"

        if getattr(attachment, "evidence_stage", None) != stage:
            attachment.evidence_stage = stage
            attachment.save(update_fields=["evidence_stage"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_moderationappealattachment_evidence_stage"),
    ]

    operations = [
        migrations.RunPython(backfill_evidence_stage, noop_reverse),
    ]
