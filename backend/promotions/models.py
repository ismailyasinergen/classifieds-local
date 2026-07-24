from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from listings.models import Listing

from .doping_catalog_v342 import (
    DURATION_MODE_CHOICES_V342,
    PRICE_GROUP_CHOICES_V342,
    PROMOTION_CODE_CHOICES_V342,
    DurationModeV342,
    PromotionCodeV342,
    promotion_end_at_v342,
)


class PromotionPackage(models.Model):
    class PackageType(models.TextChoices):
        FEATURED = "featured", "Featured"
        TOP = "top", "Top Listing"

    name = models.CharField(max_length=120)
    package_type = models.CharField(max_length=20, choices=PackageType.choices)
    duration_days = models.PositiveIntegerField(default=7)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    catalog_code = models.CharField(
        max_length=40,
        choices=PROMOTION_CODE_CHOICES_V342,
        blank=True,
        default="",
        db_index=True,
    )
    price_group = models.CharField(
        max_length=32,
        choices=PRICE_GROUP_CHOICES_V342,
        blank=True,
        default="",
        db_index=True,
    )
    duration_mode = models.CharField(
        max_length=24,
        choices=DURATION_MODE_CHOICES_V342,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["package_type", "duration_days", "price"]
        constraints = [
            models.UniqueConstraint(
                fields=["catalog_code", "price_group"],
                condition=~models.Q(catalog_code=""),
                name="promo_catalog_group_unique_v342",
            ),
        ]

    def __str__(self):
        return self.name


class ListingPromotion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        ACTIVE = "active", "Active"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="promotions")
    package = models.ForeignKey(PromotionPackage, on_delete=models.PROTECT, related_name="listing_promotions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listing_promotions")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    payment_reference = models.CharField(max_length=40, blank=True)
    payment_proof = models.ImageField(upload_to="promotion_payment_proofs/", null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    promotion_code_snapshot = models.CharField(
        max_length=40,
        choices=PROMOTION_CODE_CHOICES_V342,
        blank=True,
        default="",
    )
    price_group_snapshot = models.CharField(
        max_length=32,
        choices=PRICE_GROUP_CHOICES_V342,
        blank=True,
        default="",
    )
    duration_mode_snapshot = models.CharField(
        max_length=24,
        choices=DURATION_MODE_CHOICES_V342,
        blank=True,
        default="",
    )
    requested_weeks = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    unit_price_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    discount_percent_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(requested_weeks__isnull=True)
                    | models.Q(requested_weeks__in=(1, 2, 4))
                ),
                name="promo_requested_weeks_valid_v342",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(discount_percent_snapshot__gte=Decimal("0.0000"))
                    & models.Q(discount_percent_snapshot__lte=Decimal("1.0000"))
                ),
                name="promo_discount_snapshot_range_v342",
            ),
        ]

    def __str__(self):
        return f"{self.package.name} for {self.listing.title}"

    def mark_paid(self):
        self.payment_status = self.PaymentStatus.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["payment_status", "paid_at"])

    @transaction.atomic
    def activate(self):
        now = timezone.now()

        if self.promotion_code_snapshot:
            try:
                promotion_code = PromotionCodeV342(
                    self.promotion_code_snapshot
                )
                duration_mode = DurationModeV342(
                    self.duration_mode_snapshot
                )
                end_date = promotion_end_at_v342(
                    starts_at=now,
                    duration_mode=duration_mode,
                    requested_weeks=self.requested_weeks,
                    listing_expires_at=self.listing.expires_at,
                )
            except ValueError as exc:
                raise ValidationError(
                    {
                        "promotion": (
                            "Promotion activation data is invalid: "
                            f"{exc}"
                        )
                    }
                ) from exc

            self.status = self.Status.ACTIVE
            self.starts_at = now
            self.ends_at = end_date
            self.save(
                update_fields=[
                    "status",
                    "starts_at",
                    "ends_at",
                ]
            )

            if (
                promotion_code
                == PromotionCodeV342.HOMEPAGE_SHOWCASE
            ):
                self.listing.is_featured = True
                self.listing.featured_priority = (
                    self.package.priority
                )
                self.listing.featured_until = end_date
                self.listing.save(
                    update_fields=[
                        "is_featured",
                        "featured_priority",
                        "featured_until",
                    ]
                )

            elif (
                promotion_code
                == PromotionCodeV342.TOP_RANKING
            ):
                self.listing.top_listing_priority = (
                    self.package.priority
                )
                self.listing.top_listing_until = end_date
                self.listing.save(
                    update_fields=[
                        "top_listing_priority",
                        "top_listing_until",
                    ]
                )

            return

        end_date = now + timedelta(
            days=self.package.duration_days
        )

        self.status = self.Status.ACTIVE
        self.starts_at = now
        self.ends_at = end_date
        self.save(
            update_fields=[
                "status",
                "starts_at",
                "ends_at",
            ]
        )

        if (
            self.package.package_type
            == PromotionPackage.PackageType.FEATURED
        ):
            self.listing.is_featured = True
            self.listing.featured_priority = (
                self.package.priority
            )
            self.listing.featured_until = end_date
            self.listing.save(
                update_fields=[
                    "is_featured",
                    "featured_priority",
                    "featured_until",
                ]
            )

        if (
            self.package.package_type
            == PromotionPackage.PackageType.TOP
        ):
            self.listing.top_listing_priority = (
                self.package.priority
            )
            self.listing.top_listing_until = end_date
            self.listing.save(
                update_fields=[
                    "top_listing_priority",
                    "top_listing_until",
                ]
            )

    def reject(self):
        self.status = self.Status.REJECTED
        self.save(update_fields=["status"])
