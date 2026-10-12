import uuid
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from .validation import CONTENT_FIELDS, normalize_draft_content
from .search.expressions import folded_location_v1, folded_title_v1, search_vector_v1


class Listing(models.Model):
    class Lifecycle(models.TextChoices):
        DRAFT = "draft", "Taslak"
        LIVE = "live", "Yayında"
        PAUSED = "paused", "Duraklatıldı"
        CLOSED = "closed", "Kapalı"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="listings")
    lifecycle = models.CharField(max_length=10, choices=Lifecycle.choices, default=Lifecycle.DRAFT)
    public_revision = models.ForeignKey("ListingRevision", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    contact_enabled = models.BooleanField(default=True, db_default=True)
    first_published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["owner", "-created_at", "-id"], name="listing_owner_recent_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(lifecycle__in=["draft", "live", "paused", "closed"]),
                                   name="listings_valid_lifecycle"),
        ]

    def clean(self):
        super().clean()
        if self.public_revision_id:
            revision = ListingRevision.objects.filter(pk=self.public_revision_id).first()
            if revision is None or revision.listing_id != self.pk or revision.status != ListingRevision.Status.APPROVED:
                raise ValidationError({"public_revision": "Yayımlanan revizyon bu ilanın onaylı revizyonu olmalıdır."})


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["user", "listing"], name="favorite_user_listing_unique")]
        indexes = [models.Index(fields=["user", "-created_at", "-id"], name="favorite_user_recent_idx")]


class ListingRevision(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        SUBMITTED = "submitted", "İncelemede"
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"
        WITHDRAWN = "withdrawn", "Geri çekildi"

    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="revisions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    edit_version = models.PositiveIntegerField(default=1)
    category = models.ForeignKey("catalog.Category", on_delete=models.PROTECT, related_name="listing_revisions")
    attribute_schema = models.ForeignKey("catalog.AttributeSchema", on_delete=models.PROTECT, related_name="listing_revisions")
    schema_version = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True, validators=[MaxLengthValidator(20000)])
    price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    location = models.CharField(max_length=160, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        permissions = [("review_listingrevision", "Can review listing revisions")]
        indexes = [
            GinIndex(search_vector_v1(), name="search_document_v1_gin",
                     condition=models.Q(status="approved")),
            GinIndex(OpClass(folded_title_v1(), name="gin_trgm_ops"),
                     name="search_title_v1_trgm", condition=models.Q(status="approved")),
            GinIndex(OpClass(folded_location_v1(), name="gin_trgm_ops"),
                     name="search_location_v1_trgm", condition=models.Q(status="approved")),
        ]
        constraints = [
            models.UniqueConstraint(fields=["listing"], condition=models.Q(status__in=["draft", "submitted"]),
                                    name="listings_one_open_revision"),
            models.CheckConstraint(condition=models.Q(edit_version__gte=1),
                                   name="listings_positive_edit_version"),
            models.CheckConstraint(condition=models.Q(schema_version__gte=1),
                                   name="listings_positive_schema_version"),
            models.CheckConstraint(condition=models.Q(price__isnull=True) | models.Q(price__gte=0),
                                   name="listings_nonnegative_price"),
            models.CheckConstraint(condition=models.Q(status__in=["draft", "submitted", "approved", "rejected", "withdrawn"]),
                                   name="listings_valid_revision_status"),
        ]

    def clean(self):
        super().clean()
        if self.attribute_schema_id:
            schema = self.attribute_schema
            if schema.category_id != self.category_id or schema.version != self.schema_version:
                raise ValidationError({"attribute_schema": "Kategori ve sürüm seçili şemayla eşleşmelidir."})
            normalize_draft_content(
                schema=schema, content={name: getattr(self, name) for name in CONTENT_FIELDS})
