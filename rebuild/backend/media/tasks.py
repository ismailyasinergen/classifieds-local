from datetime import timedelta
import os
from pathlib import Path
import tempfile

from celery import shared_task
from PIL import Image, ImageOps
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import MediaAsset
from .validation import decode_image


def _write_derivative(asset):
    with asset.original.open("rb") as original:
        data = original.read(settings.MEDIA_MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.MEDIA_MAX_UPLOAD_BYTES:
        raise ValueError("Source too large")
    image, format, width, height = decode_image(data)
    try:
        oriented = ImageOps.exif_transpose(image)
        try:
            oriented.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            # Fresh pixel-only image removes EXIF/GPS, comments, ICC and other source metadata.
            clean = Image.new("RGB", oriented.size, "white")
            if "A" in oriented.getbands() or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                clean.paste(rgba, mask=rgba.getchannel("A"))
                rgba.close()
            else:
                clean.paste(oriented.convert("RGB"))
            name = f"derivatives/{asset.storage_key.hex}.jpg"
            target = Path(asset.derivative.storage.path(name))
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary_name = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as temporary:
                    temporary_name = temporary.name
                    clean.save(temporary, format="JPEG", quality=85)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.chmod(temporary_name, 0o600)
                os.replace(temporary_name, target)
            finally:
                clean.close()
                if temporary_name and os.path.exists(temporary_name):
                    os.unlink(temporary_name)
            return name
        finally:
            oriented.close()
    finally:
        image.close()


@shared_task(acks_late=True, reject_on_worker_lost=True, soft_time_limit=45, time_limit=60)
def process_image(asset_id: int) -> None:
    # Standalone worker locks only MediaAsset, and never later acquires a parent lock.
    with transaction.atomic():
        asset = MediaAsset.objects.select_for_update().filter(pk=asset_id).first()
        if asset is None or asset.state != MediaAsset.State.PENDING:
            return
        if asset.attempts >= 3:
            asset.state = MediaAsset.State.FAILED
            asset.error_code = "attempt_limit"
            asset.save(update_fields=["state", "error_code", "updated_at"])
            return
        asset.attempts += 1
        try:
            name = _write_derivative(asset)
        except Exception:
            # Safe failure code only; never expose source paths or decoder details.
            asset.state = MediaAsset.State.FAILED
            asset.error_code = "processing_failed"
        else:
            asset.derivative.name = name
            asset.state = MediaAsset.State.READY
            asset.error_code = ""
            asset.processed_at = timezone.now()
        asset.save(update_fields=["attempts", "state", "error_code", "derivative",
                                  "processed_at", "updated_at"])


@shared_task
def rescue_pending_images() -> None:
    from .services import enqueue_processing

    cutoff = timezone.now() - timedelta(seconds=60)
    ids = list(MediaAsset.objects.filter(state=MediaAsset.State.PENDING)
               .filter(Q(last_enqueued_at__isnull=True) | Q(last_enqueued_at__lte=cutoff))
               .order_by("created_at", "pk").values_list("pk", flat=True)[:100])
    for asset_id in ids:
        enqueue_processing(asset_id)
