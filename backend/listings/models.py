import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as AuditValidationError
from django.db import models, router, transaction
from django.urls import reverse
from django.utils import timezone

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

    # LISTING_PRICE_HISTORY_V275
    def save(self, *args, **kwargs):
        """
        Persist Listing normally and atomically record price transitions.

        A single baseline row represents the initial price. Subsequent rows
        are created only when the persisted price actually changes.
        """
        price_change_reason = str(
            kwargs.pop("price_change_reason", "") or ""
        ).strip()
        valid_price_change_reasons = {
            value for value, _label in ListingPriceHistory.Reason.choices
        }
        if price_change_reason not in valid_price_change_reasons:
            raise AuditValidationError(
                {"price_change_reason": "Select a valid price-change reason."}
            )

        update_fields = kwargs.get("update_fields")

        if (
            update_fields is not None
            and "price" not in set(update_fields)
        ):
            return super().save(*args, **kwargs)

        price_field = self._meta.get_field("price")
        current_price = price_field.to_python(self.price)
        self.price = current_price

        using = (
            kwargs.get("using")
            or router.db_for_write(
                type(self),
                instance=self,
            )
        )

        kwargs["using"] = using
        is_new = self._state.adding
        previous_price = None

        with transaction.atomic(using=using):
            if not is_new and self.pk:
                previous_price = (
                    type(self)
                    .objects
                    .using(using)
                    .select_for_update()
                    .filter(pk=self.pk)
                    .values_list("price", flat=True)
                    .first()
                )

            result = super().save(
                *args,
                **kwargs,
            )

            baseline_price = (
                current_price
                if previous_price is None
                else previous_price
            )

            (
                ListingPriceHistory
                .objects
                .using(using)
                .get_or_create(
                    listing_id=self.pk,
                    previous_price=None,
                    defaults={
                        "new_price": baseline_price,
                        "changed_at": (
                            self.created_at
                            or timezone.now()
                        ),
                    },
                )
            )

            if (
                previous_price is not None
                and previous_price != current_price
            ):
                (
                    ListingPriceHistory
                    .objects
                    .using(using)
                    .create(
                        listing_id=self.pk,
                        previous_price=previous_price,
                        new_price=current_price,
                        changed_at=timezone.now(),
                        reason=price_change_reason,
                    )
                )

        return result


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


    @property
    def public_seller_store(self):
        try:
            store = self.owner.seller_store
        except ObjectDoesNotExist:
            return None

        if not store.is_active:
            return None

        return store


# LISTING_PRICE_HISTORY_V275
class ListingPriceHistory(models.Model):
    class Reason(models.TextChoices):
        UNSPECIFIED = "", "No reason selected"
        MARKET_ADJUSTMENT = "market_adjustment", "Market adjustment"
        PROMOTION = "promotion", "Promotion"
        CONDITION_UPDATE = "condition_update", "Condition update"
        LISTING_CORRECTION = "listing_correction", "Listing correction"
        OTHER = "other", "Other"

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="price_history",
    )
    previous_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    new_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    changed_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )
    reason = models.CharField(
        max_length=32,
        choices=Reason.choices,
        blank=True,
        default=Reason.UNSPECIFIED,
    )

    class Meta:
        ordering = [
            "-changed_at",
            "-pk",
        ]
        indexes = [
            models.Index(
                fields=[
                    "listing",
                    "-changed_at",
                ],
                name="lst_price_hist_lc_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(
                    previous_price__isnull=True,
                ),
                name="lst_price_hist_base_uniq",
            ),
        ]

    def __str__(self):
        if self.is_baseline:
            return (
                f"{self.listing}: initial price "
                f"{self.new_price}"
            )

        return (
            f"{self.listing}: "
            f"{self.previous_price} → {self.new_price}"
        )

    @property
    def is_baseline(self):
        return self.previous_price is None

    @property
    def is_price_drop(self):
        return (
            self.previous_price is not None
            and self.new_price < self.previous_price
        )

    @property
    def is_price_increase(self):
        return (
            self.previous_price is not None
            and self.new_price > self.previous_price
        )

    @property
    def change_amount(self):
        if self.previous_price is None:
            return None

        return abs(
            self.new_price
            - self.previous_price
        )

    @property
    def change_percentage(self):
        if (
            self.previous_price is None
            or self.previous_price == 0
        ):
            return None

        percentage = (
            self.change_amount
            / abs(self.previous_price)
            * Decimal("100")
        )

        return percentage.quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )


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


# LISTING_SPECIFIC_PRICE_ALERTS_V285
class ListingPriceAlert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_price_alerts",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="price_alerts",
    )
    baseline_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    last_notified_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    last_notification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"],
                name="lst_alert_user_listing_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="lst_alert_user_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.username}: price alert for {self.listing.title}"


# NOTIFICATION_DELIVERY_DEDUPLICATION_V287
class NotificationDeliveryEvent(models.Model):
    class NotificationType(models.TextChoices):
        LISTING_PRICE_DROP = "listing_price_drop", "Listing price drop"
        SAVED_SEARCH_NEW_LISTING = (
            "saved_search_new_listing",
            "Saved-search new listing",
        )
        SAVED_SEARCH_PRICE_DROP = (
            "saved_search_price_drop",
            "Saved-search price drop",
        )

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notification_delivery_events",
    )
    listing = models.ForeignKey(
        Listing,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notification_delivery_events",
    )
    listing_price_alert = models.ForeignKey(
        ListingPriceAlert,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_events",
    )
    saved_search = models.ForeignKey(
        "SavedSearch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_events",
    )
    price_transition = models.ForeignKey(
        ListingPriceHistory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notification_delivery_events",
    )
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
    )
    channel = models.CharField(max_length=16, default="email")
    event_key = models.CharField(max_length=64, unique=True)
    target_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    transition_changed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    claim_token = models.UUIDField(null=True, blank=True, editable=False)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error_category = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["notification_type", "status", "-created_at"],
                name="notif_type_status_created_idx",
            ),
            models.Index(
                fields=["recipient", "-created_at"],
                name="notif_recipient_created_idx",
            ),
            models.Index(
                fields=["saved_search", "status"],
                name="notif_search_status_idx",
            ),
            models.Index(
                fields=["listing_price_alert", "status"],
                name="notif_alert_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="processing")
                    | (
                        models.Q(claim_token__isnull=False)
                        & models.Q(processing_started_at__isnull=False)
                    )
                ),
                name="notif_processing_claim_required",
            ),
        ]

    def __str__(self):
        return f"{self.notification_type}:{self.status}:{self.event_key[:12]}"


# NOTIFICATION_DELIVERY_PREFERENCES_V288
class NotificationDeliveryPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_delivery_preference",
    )
    listing_price_alert_email_enabled = models.BooleanField(default=True)
    saved_search_new_listing_email_enabled = models.BooleanField(default=True)
    saved_search_price_drop_email_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self):
        return f"Notification preferences for {self.user}"





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
    # SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
    email_notifications_enabled = models.BooleanField(default=False)
    last_notification_checked_at = models.DateTimeField(null=True, blank=True)
    last_notification_sent_at = models.DateTimeField(null=True, blank=True)
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

        # SELLER_STORE_SAVED_SEARCH_CREATE_INTEGRATION_V122
        # Prefer the canonical stored querystring when present so saved-search
        # redirects keep the same deterministic parameter ordering used by the
        # save/create helper.
        if self.querystring:
            return f"{base_path}?{self.querystring}"

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

    # SELLER_STORE_SAVED_SEARCH_MANAGEMENT_POLISH_V123
    @property
    def is_seller_store_directory_search(self):
        from django.urls import reverse

        try:
            seller_store_directory_path = reverse("accounts:seller_store_directory")
        except Exception:
            return False

        return (self.path or "").rstrip("/") == seller_store_directory_path.rstrip("/")

    @property
    def search_source_label(self):
        if self.is_seller_store_directory_search:
            return "Seller stores"

        return "Listings"

    @property
    def search_source_css_class(self):
        if self.is_seller_store_directory_search:
            return "is-seller-store"

        return "is-listing"

    @property
    def run_action_label(self):
        if self.is_seller_store_directory_search:
            return "Run store search"

        return "Run search"

    # SAVED_SEARCH_UX_POLISH_V78
    @property
    def filter_summaries(self):
        from .saved_searches import summarize_saved_search_params

        return summarize_saved_search_params(self.query_params)

    @property
    def filter_count(self):
        return len(self.filter_summaries)

    @property
    def summary_sentence(self):
        from .saved_searches import saved_search_summary_sentence

        return saved_search_summary_sentence(self.query_params)

    # SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
    @property
    def email_notification_status_label(self):
        if self.email_notifications_enabled:
            return "Email alerts on"

        return "Email alerts off"


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

# V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION
V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION = (
    "V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION"
)


class SavedSearchNotificationAuditEventQuerySet(models.QuerySet):
    immutable_error_message = (
        "Saved-search notification audit events are append-only."
    )

    def update(self, **kwargs):
        raise AuditValidationError(self.immutable_error_message)

    def delete(self):
        raise AuditValidationError(self.immutable_error_message)

    def bulk_update(self, objs, fields, batch_size=None):
        raise AuditValidationError(self.immutable_error_message)


class SavedSearchNotificationAuditEvent(models.Model):
    class EventType(models.TextChoices):
        EVALUATION_STARTED = (
            "evaluation_started",
            "Evaluation started",
        )
        SKIPPED_NOTIFICATIONS_DISABLED = (
            "skipped_notifications_disabled",
            "Skipped: notifications disabled",
        )
        SKIPPED_MISSING_RECIPIENT = (
            "skipped_missing_recipient",
            "Skipped: missing recipient",
        )
        DRY_RUN_RENDERED = (
            "dry_run_rendered",
            "Dry-run rendered",
        )
        DELIVERY_ATTEMPTED = (
            "delivery_attempted",
            "Delivery attempted",
        )
        DELIVERY_SUCCEEDED = (
            "delivery_succeeded",
            "Delivery succeeded",
        )
        DELIVERY_FAILED = (
            "delivery_failed",
            "Delivery failed",
        )
        SENT_TIMESTAMP_RECORDED = (
            "sent_timestamp_recorded",
            "Sent timestamp recorded",
        )
        ROLLBACK_PREVIEWED = (
            "rollback_previewed",
            "Rollback previewed",
        )
        ROLLBACK_APPLIED = (
            "rollback_applied",
            "Rollback applied",
        )

    class Outcome(models.TextChoices):
        PENDING = "pending", "Pending"
        SKIPPED = "skipped", "Skipped"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled back"

    class ActorType(models.TextChoices):
        SYSTEM = "system", "System"
        SCHEDULER = "scheduler", "Scheduler"
        OPERATOR = "operator", "Operator"
        MANAGEMENT_COMMAND = (
            "management_command",
            "Management command",
        )
        TEST_BACKEND = "test_backend", "Test backend"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    saved_search = models.ForeignKey(
        SavedSearch,
        on_delete=models.PROTECT,
        related_name="notification_audit_events",
    )

    owner_id_snapshot = models.CharField(
        max_length=64,
    )

    event_type = models.CharField(
        max_length=64,
        choices=EventType.choices,
    )

    outcome = models.CharField(
        max_length=32,
        choices=Outcome.choices,
    )

    reason_code = models.CharField(
        max_length=96,
        blank=True,
    )

    occurred_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    batch_id = models.UUIDField(
        null=True,
        blank=True,
    )

    correlation_id = models.UUIDField()

    delivery_attempt_id = models.UUIDField(
        null=True,
        blank=True,
    )

    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
    )

    notification_fingerprint = models.CharField(
        max_length=64,
    )

    rollback_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="rollback_events",
    )

    actor_type = models.CharField(
        max_length=32,
        choices=ActorType.choices,
    )

    actor_identifier = models.CharField(
        max_length=128,
        blank=True,
    )

    source = models.CharField(
        max_length=128,
    )

    checked_at_before = models.DateTimeField(
        null=True,
        blank=True,
    )

    checked_at_after = models.DateTimeField(
        null=True,
        blank=True,
    )

    sent_at_before = models.DateTimeField(
        null=True,
        blank=True,
    )

    sent_at_after = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    objects = SavedSearchNotificationAuditEventQuerySet.as_manager()

    class Meta:
        db_table = "listings_savedsearchnotificationauditevent"
        ordering = (
            "-occurred_at",
            "-created_at",
        )
        get_latest_by = "occurred_at"

        indexes = [
            models.Index(
                fields=(
                    "saved_search",
                    "occurred_at",
                ),
                name="ssna_saved_occ_idx",
            ),
            models.Index(
                fields=(
                    "event_type",
                    "occurred_at",
                ),
                name="ssna_event_occ_idx",
            ),
            models.Index(
                fields=(
                    "outcome",
                    "occurred_at",
                ),
                name="ssna_outcome_occ_idx",
            ),
            models.Index(
                fields=("batch_id",),
                name="ssna_batch_idx",
            ),
            models.Index(
                fields=("correlation_id",),
                name="ssna_corr_idx",
            ),
            models.Index(
                fields=("delivery_attempt_id",),
                name="ssna_attempt_idx",
            ),
            models.Index(
                fields=("notification_fingerprint",),
                name="ssna_fingerprint_idx",
            ),
            models.Index(
                fields=("rollback_of",),
                name="ssna_rollback_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(
                        event_type__in=(
                            "rollback_previewed",
                            "rollback_applied",
                        )
                    )
                    | models.Q(
                        rollback_of__isnull=False,
                    )
                ),
                name="ssna_rollback_link_required",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(
                        event_type__in=(
                            "delivery_attempted",
                            "delivery_succeeded",
                            "delivery_failed",
                        )
                    )
                    | models.Q(
                        delivery_attempt_id__isnull=False,
                    )
                ),
                name="ssna_delivery_attempt_required",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditValidationError(
                "Saved-search notification audit events "
                "cannot be updated."
            )

        if kwargs.get("force_update"):
            raise AuditValidationError(
                "Saved-search notification audit events "
                "cannot be force-updated."
            )

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditValidationError(
            "Saved-search notification audit events "
            "cannot be deleted."
        )

    def __str__(self):
        return (
            f"{self.event_type}:"
            f"{self.outcome}:"
            f"{self.pk}"
        )
