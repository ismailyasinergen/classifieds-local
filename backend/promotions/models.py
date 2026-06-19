from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from listings.models import Listing


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["package_type", "duration_days", "price"]

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
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.package.name} for {self.listing.title}"

    def mark_paid(self):
        self.payment_status = self.PaymentStatus.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["payment_status", "paid_at"])

    def activate(self):
        now = timezone.now()
        end_date = now + timedelta(days=self.package.duration_days)

        self.status = self.Status.ACTIVE
        self.starts_at = now
        self.ends_at = end_date
        self.save(update_fields=["status", "starts_at", "ends_at"])

        if self.package.package_type == PromotionPackage.PackageType.FEATURED:
            self.listing.is_featured = True
            self.listing.featured_priority = self.package.priority
            self.listing.featured_until = end_date
            self.listing.save(update_fields=["is_featured", "featured_priority", "featured_until"])

        if self.package.package_type == PromotionPackage.PackageType.TOP:
            self.listing.top_listing_priority = self.package.priority
            self.listing.top_listing_until = end_date
            self.listing.save(update_fields=["top_listing_priority", "top_listing_until"])

    def reject(self):
        self.status = self.Status.REJECTED
        self.save(update_fields=["status"])
