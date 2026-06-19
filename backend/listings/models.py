from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from categories.models import Category


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"
        SUSPENDED = "suspended", "Suspended"

    title = models.CharField(max_length=180)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    location = models.CharField(max_length=120)
    is_featured = models.BooleanField(default=False)
    featured_priority = models.PositiveIntegerField(default=0)
    featured_until = models.DateTimeField(null=True, blank=True)
    top_listing_priority = models.PositiveIntegerField(default=0)
    top_listing_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPROVED,
    )
    suspended_due_to_seller = models.BooleanField(default=False, db_index=True)
    status_before_seller_suspension = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listings:listing_detail", kwargs={"pk": self.pk})


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="listing_images/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Image for {self.listing.title}"


class ListingFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_listings",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["user", "listing"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} saved {self.listing.title}"



class ListingReport(models.Model):
    class Reason(models.TextChoices):
        SCAM = "scam", "Scam or fraud"
        FAKE_SELLER = "fake_seller", "Fake or suspicious seller"
        MISLEADING = "misleading", "Misleading title, description, or photos"
        INCORRECT_PRICE = "incorrect_price", "Incorrect or suspicious price"
        NOT_AVAILABLE = "not_available", "Item no longer available"
        ILLEGAL = "illegal", "Illegal or restricted item"
        COUNTERFEIT = "counterfeit", "Counterfeit item"
        OFFENSIVE = "offensive", "Offensive or abusive content"
        SPAM = "spam", "Spam"
        CONTACT_INFO = "contact_info", "Contact info or external link in listing"
        WRONG_CATEGORY = "wrong_category", "Wrong category"
        PROHIBITED = "prohibited", "Prohibited item"
        DUPLICATE = "duplicate", "Duplicate listing"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWED = "reviewed", "Reviewed"
        DISMISSED = "dismissed", "Dismissed"

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_reports",
    )
    reason = models.CharField(max_length=40, choices=Reason.choices)
    reasons = models.JSONField(default=list, blank=True)
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    action_taken = models.CharField(max_length=60, blank=True, default="")
    reporter_note = models.CharField(max_length=255, blank=True)
    admin_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "reporter"],
                name="unique_report_per_user_listing",
            ),
        ]

    def get_reasons_display(self):
        labels = dict(self.Reason.choices)
        selected = self.reasons or ([self.reason] if self.reason else [])
        return ", ".join(labels.get(value, value) for value in selected)

    def __str__(self):
        return f"Report for {self.listing.title}"
