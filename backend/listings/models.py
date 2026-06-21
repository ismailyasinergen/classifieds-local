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
    attributes = models.JSONField(default=dict, blank=True)
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

    ATTRIBUTE_LABELS = {
        "brand": "Brand",
        "model_name": "Model / Series",
        "model_year": "Year",
        "mileage": "Mileage / KM",
        "fuel_type": "Fuel Type",
        "transmission": "Transmission",
        "color": "Color",
        "condition": "Condition",
        "warranty": "Warranty",
        "accepts_exchange": "Accepts Exchange",
    }

    ATTRIBUTE_VALUE_LABELS = {
        "fuel_type": {
            "gasoline": "Gasoline",
            "diesel": "Diesel",
            "hybrid": "Hybrid",
            "electric": "Electric",
            "lpg": "LPG",
            "other": "Other",
        },
        "transmission": {
            "manual": "Manual",
            "automatic": "Automatic",
            "semi_automatic": "Semi-automatic",
            "other": "Other",
        },
        "condition": {
            "new": "New",
            "used": "Used",
            "damaged": "Damaged",
            "other": "Other",
        },
        "warranty": {True: "Yes", False: "No", "true": "Yes", "false": "No"},
        "accepts_exchange": {True: "Yes", False: "No", "true": "Yes", "false": "No"},
    }

    def get_absolute_url(self):
        return reverse("listings:listing_detail", kwargs={"pk": self.pk})

    @property
    def display_attributes(self):
        from .attribute_schema import get_display_attributes

        return get_display_attributes(self)

    @property
    def card_highlights(self):
        from .attribute_schema import get_card_highlights

        return get_card_highlights(self)


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





# SAVED_SEARCH_FOUNDATION_V77
class SavedSearch(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_searches",
    )
    name = models.CharField(max_length=120, blank=True)
    path = models.CharField(max_length=255, default="/listings/")
    query_params = models.JSONField(default=dict)
    querystring = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"], name="saved_search_user_updated_idx"),
        ]

    def __str__(self):
        return self.name or self.display_name

    @property
    def display_name(self):
        if self.name:
            return self.name

        parts = []
        category = self.query_params.get("category")
        q = self.query_params.get("q")
        location = self.query_params.get("location")

        if category:
            parts.append(str(category).replace("-", " ").title())
        if q:
            parts.append(str(q))
        if location:
            parts.append(str(location))

        min_price = self.query_params.get("min_price")
        max_price = self.query_params.get("max_price")
        if min_price:
            parts.append(f"Min {min_price} TL")
        if max_price:
            parts.append(f"Max {max_price} TL")

        if not parts:
            parts.append("Saved search")

        return " · ".join(parts)

    def get_absolute_url(self):
        from django.urls import reverse
        from django.utils.http import urlencode

        base_path = self.path or reverse("listings:listing_list")
        pairs = []

        for key, value in (self.query_params or {}).items():
            if isinstance(value, list):
                for item in value:
                    pairs.append((key, item))
            else:
                pairs.append((key, value))

        querystring = urlencode(pairs, doseq=True)
        if querystring:
            return f"{base_path}?{querystring}"

        return base_path


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
