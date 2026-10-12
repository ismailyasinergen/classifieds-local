import uuid
from django.conf import settings
from django.db import models


class PromotionProduct(models.Model):
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    duration_seconds = models.PositiveIntegerField()
    placement = models.CharField(max_length=16, default="search")
    terms_version = models.CharField(max_length=32)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="promotion_product_amount"),
            models.CheckConstraint(condition=models.Q(duration_seconds__gte=1, duration_seconds__lte=2592000), name="promotion_product_duration"),
            models.CheckConstraint(condition=models.Q(placement="search"), name="promotion_product_placement"),
        ]


class Purchase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT)
    product = models.ForeignKey(PromotionProduct, on_delete=models.PROTECT)
    key = models.UUIDField()
    product_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    duration_seconds = models.PositiveIntegerField()
    placement = models.CharField(max_length=16)
    terms_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "key"], name="promotion_purchase_key"),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="promotion_purchase_amount"),
            models.CheckConstraint(condition=models.Q(duration_seconds__gte=1, duration_seconds__lte=2592000), name="promotion_purchase_duration"),
            models.CheckConstraint(condition=models.Q(placement="search"), name="promotion_purchase_placement"),
        ]


class DemoEvidence(models.Model):
    purchase = models.OneToOneField(Purchase, on_delete=models.PROTECT)
    kind = models.CharField(max_length=32, default="demo_no_payment", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(kind="demo_no_payment"), name="promotion_demo_evidence_kind")]


class Activation(models.Model):
    purchase = models.OneToOneField(Purchase, on_delete=models.PROTECT)
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="promotions")
    placement = models.CharField(max_length=16, default="search")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_at__gt=models.F("starts_at")), name="promotion_activation_interval"),
            models.CheckConstraint(condition=models.Q(placement="search"), name="promotion_activation_placement"),
        ]
        indexes = [models.Index(fields=["listing", "placement", "ends_at"], name="promotion_listing_end_idx")]