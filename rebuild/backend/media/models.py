import uuid
from django.conf import settings
from django.db import models
from .storage import original_name, private_storage


class MediaAsset(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "İşleniyor"
        READY = "ready", "Hazır"
        FAILED = "failed", "İşlenemedi"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="media_assets")
    storage_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    original = models.FileField(storage=private_storage, upload_to=original_name, max_length=200)
    derivative = models.FileField(storage=private_storage, max_length=200, blank=True)
    source_mime = models.CharField(max_length=20)
    source_bytes = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=40, blank=True)
    last_enqueued_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["state", "last_enqueued_at"], name="media_pending_enqueue_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(state__in=["pending", "ready", "failed"]),
                                   name="media_valid_asset_state"),
            models.CheckConstraint(condition=models.Q(attempts__lte=3), name="media_bounded_attempts"),
            models.CheckConstraint(condition=models.Q(width__gt=0, height__gt=0, source_bytes__gt=0),
                                   name="media_positive_dimensions_bytes"),
        ]


class RevisionImage(models.Model):
    revision = models.ForeignKey("listings.ListingRevision", on_delete=models.PROTECT, related_name="images")
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="revision_images")
    position = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["revision", "asset"], name="media_unique_revision_asset"),
            models.UniqueConstraint(fields=["revision", "position"], name="media_unique_revision_position"),
            models.CheckConstraint(condition=models.Q(position__gte=0), name="media_nonnegative_position"),
        ]
