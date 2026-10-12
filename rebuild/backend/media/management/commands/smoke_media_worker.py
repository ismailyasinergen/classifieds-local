"""Deliberate synthetic records in the NEW dev DB, processed by the normal worker."""
from io import BytesIO
import json
from time import monotonic, sleep
from uuid import uuid4

from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.services import create_listing_draft
from media.models import MediaAsset
from media.services import attach_image
from media.tasks import process_image


class Command(BaseCommand):
    help = "Create synthetic new-development media and observe the normal Celery worker."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=30)
        parser.add_argument("--asset-id", type=int, help="Inspect an existing synthetic smoke asset.")

    def handle(self, *args, **options):
        if not settings.DEBUG or getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            raise CommandError("Run only in the new development stack with a real broker.")
        timeout = options["timeout"]
        if not 1 <= timeout <= 45:
            raise CommandError("Timeout must be between 1 and 45 seconds.")
        if options["asset_id"]:
            asset = MediaAsset.objects.select_related("owner").get(pk=options["asset_id"])
            if not asset.owner.email.endswith("@media-smoke.invalid"):
                raise CommandError("Only this command's synthetic records can be inspected.")
            self.stdout.write(json.dumps(self.evidence(asset)))
            return

        token = uuid4().hex
        owner = User.objects.create_user(f"{token}@media-smoke.invalid")
        category = Category.objects.create(name="Synthetic media smoke", slug=f"media-smoke-{token}")
        AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
        revision = create_listing_draft(actor=owner, category_id=category.pk, content={})
        buffer = BytesIO()
        Image.new("RGB", (64, 48), "green").save(buffer, format="PNG")
        asset = attach_image(actor=owner, revision_id=revision.pk, uploaded_file=SimpleUploadedFile(
            "synthetic.png", buffer.getvalue(), content_type="image/png"))
        self.stdout.write(json.dumps({"event": "enqueued", "asset_id": asset.pk,
                                     "revision_id": revision.pk, "listing_id": str(revision.listing_id)}))
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            asset.refresh_from_db()
            if asset.state == MediaAsset.State.READY:
                break
            if asset.state == MediaAsset.State.FAILED:
                raise CommandError(f"Worker failed synthetic asset {asset.pk}: {asset.error_code}")
            sleep(0.25)
        if asset.state != MediaAsset.State.READY:
            raise CommandError(f"Worker timeout; inspect synthetic asset {asset.pk}.")
        first_name = asset.derivative.name
        replay = process_image.delay(asset.pk)
        # The task ID lets the report correlate the replay with normal worker logs.
        self.stdout.write(json.dumps({"event": "ready", **self.evidence(asset), "replay_task_id": replay.id}))
        # A bounded wait permits replay execution; worker logs separately prove delivery.
        sleep(1)
        asset.refresh_from_db()
        if asset.attempts != 1 or asset.derivative.name != first_name:
            raise CommandError("Repeated worker processing changed the result.")
        self.stdout.write(json.dumps({"event": "replay_stable", **self.evidence(asset)}))

    def evidence(self, asset):
        exists = bool(asset.derivative.name and asset.derivative.storage.exists(asset.derivative.name))
        metadata_free = False
        derivative_format = None
        if exists:
            with asset.derivative.open("rb") as source, Image.open(source) as image:
                derivative_format = image.format
                metadata_free = not image.getexif() and "exif" not in image.info
        return {"asset_id": asset.pk, "state": asset.state, "attempts": asset.attempts,
                "derivative_exists": exists, "derivative_format": derivative_format,
                "metadata_free": metadata_free, "link_count": asset.revision_images.count()}
