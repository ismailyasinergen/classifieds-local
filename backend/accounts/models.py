from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class UserProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        NOT_REQUESTED = "not_requested", "Not Requested"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=120, blank=True)

    business_name = models.CharField(max_length=160, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NOT_REQUESTED,
    )
    verification_document = models.ImageField(
        upload_to="verification_documents/",
        null=True,
        blank=True,
    )
    verification_note = models.CharField(max_length=255, blank=True)

    seller_warning_count = models.PositiveIntegerField(default=0)
    seller_suspended_until = models.DateTimeField(null=True, blank=True)
    seller_suspension_reason = models.CharField(max_length=255, blank=True)
    seller_messaging_blocked_until = models.DateTimeField(null=True, blank=True)
    seller_messaging_block_reason = models.CharField(max_length=255, blank=True)

    @property
    def is_seller_suspended(self):
        return bool(
            self.seller_suspended_until
            and self.seller_suspended_until > timezone.now()
        )

    @property
    def is_seller_messaging_blocked(self):
        return bool(
            self.seller_messaging_blocked_until
            and self.seller_messaging_blocked_until > timezone.now()
        )

    def __str__(self):
        return self.user.username

    @property
    def is_verified_seller(self):
        return self.verification_status == self.VerificationStatus.APPROVED


class EmailVerificationState(models.Model):
    METHOD_SIGNED_LINK_V306 = "signed_link_v306"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_state",
    )
    email_snapshot = models.EmailField(
        max_length=254,
        blank=True,
        default="",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    verification_method = models.CharField(
        max_length=40,
        blank=True,
        default="",
    )
    token_version = models.PositiveBigIntegerField(
        default=0,
    )
    last_requested_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def is_verified_for_current_email(self):
        current_email = str(
            getattr(self.user, "email", "")
            or ""
        ).strip()

        return bool(
            self.verified_at
            and self.email_snapshot
            and self.email_snapshot == current_email
        )

    def __str__(self):
        return f"Email verification state for {self.user.get_username()}"


class SellerStore(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_store",
    )
    name = models.CharField(max_length=160, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    headline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    logo = models.ImageField(
        upload_to="seller_store_logos/",
        blank=True,
        null=True,
    )
    banner = models.ImageField(
        upload_to="seller_store_banners/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["is_active", "updated_at"]),
        ]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.name or self.owner.get_username()

    def get_absolute_url(self):
        return reverse("accounts:seller_store_public", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_value = self.name or self.owner.get_username() or f"seller-{self.owner_id}"
        base_slug = slugify(base_value)[:140] or f"seller-{self.owner_id}"
        candidate = base_slug
        counter = 2

        queryset = type(self).objects.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{counter}"
            candidate = f"{base_slug[:180 - len(suffix)]}{suffix}"
            counter += 1

        return candidate


class UserReport(models.Model):
    class Reason(models.TextChoices):
        FAKE_SELLER = "fake_seller", "Fake or suspicious seller"
        SCAM = "scam", "Scam or fraud attempt"
        HARASSMENT = "harassment", "Harassment or abusive behavior"
        OFF_PLATFORM_PAYMENT = "off_platform_payment", "Asked me to pay outside the platform"
        OFF_PLATFORM_CONTACT = "off_platform_contact", "Asked me to communicate outside the platform"
        IMPERSONATION = "impersonation", "Impersonation"
        SUSPICIOUS_IDENTITY = "suspicious_identity", "Suspicious verification or business identity"
        REPEATED_MISLEADING = "repeated_misleading", "Repeated misleading listings"
        NO_RESPONSE = "no_response", "No response after agreement"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWED = "reviewed", "Reviewed"
        DISMISSED = "dismissed", "Dismissed"

    class Action(models.TextChoices):
        NONE = "none", "No action"
        REVIEWED = "reviewed", "Marked reviewed"
        DISMISSED = "dismissed", "Dismissed"
        WARNED_SELLER = "warned_seller", "Warned seller"
        SUSPENDED_SELLER = "suspended_seller", "Suspended seller"
        REMOVED_VERIFICATION = "removed_verification", "Removed verification"
        ARCHIVED_LISTINGS = "archived_listings", "Archived seller listings"
        BLOCKED_MESSAGING = "blocked_messaging", "Blocked seller messaging"

    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_user_reports",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_user_reports",
    )
    source_listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_reports",
    )
    reasons = models.JSONField(default=list, blank=True)
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    action_taken = models.CharField(
        max_length=40,
        choices=Action.choices,
        default=Action.NONE,
    )
    reporter_note = models.CharField(max_length=255, blank=True)
    action_taken_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def get_reasons_display(self):
        labels = dict(self.Reason.choices)
        return ", ".join(labels.get(value, value) for value in self.reasons or [])

    def __str__(self):
        return f"Report against {self.reported_user}"



class ModerationNotice(models.Model):
    class NoticeType(models.TextChoices):
        REPORT_UPDATE = "report_update", "Report update"
        LISTING_ACTION = "listing_action", "Listing action"
        SELLER_ACTION = "seller_action", "Seller action"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="moderation_notices",
    )
    title = models.CharField(max_length=160)
    body = models.TextField()
    notice_type = models.CharField(
        max_length=40,
        choices=NoticeType.choices,
        default=NoticeType.REPORT_UPDATE,
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_notices",
    )
    listing_report = models.ForeignKey(
        "listings.ListingReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_notices",
    )
    user_report = models.ForeignKey(
        "accounts.UserReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_notices",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"



class ModerationAppeal(models.Model):
    class AppealType(models.TextChoices):
        LISTING_ACTION = "listing_action", "Listing action"
        SELLER_ACTION = "seller_action", "Seller action"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    appellant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="moderation_appeals",
    )
    moderation_notice = models.ForeignKey(
        "accounts.ModerationNotice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appeals",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_appeals",
    )
    listing_report = models.ForeignKey(
        "listings.ListingReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appeals",
    )
    user_report = models.ForeignKey(
        "accounts.UserReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appeals",
    )
    appeal_type = models.CharField(
        max_length=40,
        choices=AppealType.choices,
        default=AppealType.OTHER,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    message = models.TextField()
    admin_note = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_moderation_appeals",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # APPEAL_EXTRA_EVIDENCE_REQUEST_V1
    extra_evidence_requested_at = models.DateTimeField(null=True, blank=True)
    extra_evidence_due_at = models.DateTimeField(null=True, blank=True)
    extra_evidence_request_note = models.TextField(blank=True, default="")
    extra_evidence_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_appeal_extra_evidence_requests",
    )
    extra_evidence_fulfilled_at = models.DateTimeField(null=True, blank=True)
    extra_evidence_overdue_notice_sent_at = models.DateTimeField(null=True, blank=True)
    extra_evidence_reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Appeal #{self.pk} by {self.appellant}"



class ModerationAppealAttachment(models.Model):
    # EVIDENCE_STAGE_INITIAL_EXTRA_V1
    class EvidenceStage(models.TextChoices):
        INITIAL = "initial", "Initial appeal evidence"
        EXTRA = "extra", "Extra evidence"

    evidence_stage = models.CharField(
        max_length=20,
        choices=EvidenceStage.choices,
        default=EvidenceStage.INITIAL,
    )

    appeal = models.ForeignKey(
        "accounts.ModerationAppeal",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="appeal_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    @property
    def is_image(self):
        return (self.content_type or "").startswith("image/")

    @property
    def is_video(self):
        return (self.content_type or "").startswith("video/")

    @property
    def is_pdf(self):
        return self.content_type == "application/pdf"

    @property
    def size_mb(self):
        if not self.size:
            return 0
        return round(self.size / 1024 / 1024, 2)

    def __str__(self):
        return self.original_name



# TRUST_SAFETY_EVENT_MODEL_V1
class TrustSafetyEvent(models.Model):
    class EventType(models.TextChoices):
        LISTING_REPORT_REVIEWED = "listing_report_reviewed", "Listing report reviewed"
        LISTING_SUSPENDED = "listing_suspended", "Listing suspended"
        LISTING_ARCHIVED = "listing_archived", "Listing archived"
        LISTING_RESTORED = "listing_restored", "Listing restored"

        SELLER_REPORT_REVIEWED = "seller_report_reviewed", "Seller report reviewed"
        SELLER_WARNED = "seller_warned", "Seller warned"
        SELLER_SUSPENDED = "seller_suspended", "Seller suspended"
        SELLER_SUSPENSION_LIFTED = "seller_suspension_lifted", "Seller suspension lifted"
        SELLER_VERIFICATION_REMOVED = "seller_verification_removed", "Seller verification removed"
        SELLER_LISTINGS_ARCHIVED = "seller_listings_archived", "Seller listings archived"
        SELLER_MESSAGING_BLOCKED = "seller_messaging_blocked", "Seller messaging blocked"

        APPEAL_SUBMITTED = "appeal_submitted", "Appeal submitted"
        APPEAL_APPROVED = "appeal_approved", "Appeal approved"
        APPEAL_REJECTED = "appeal_rejected", "Appeal rejected"
        APPEAL_REOPENED = "appeal_reopened", "Appeal reopened"

        NOTICE_SENT = "notice_sent", "Notice sent"
        AUDIT_REPAIR = "audit_repair", "Audit repair"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_safety_events_performed",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_safety_events_about",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_safety_events",
    )
    listing_report = models.ForeignKey(
        "listings.ListingReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_safety_events",
    )
    user_report = models.ForeignKey(
        "accounts.UserReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_safety_events",
    )
    appeal = models.ForeignKey(
        "accounts.ModerationAppeal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_safety_events",
    )

    event_type = models.CharField(max_length=80, choices=EventType.choices, db_index=True)
    title = models.CharField(max_length=255)
    public_note = models.TextField(blank=True, default="")
    internal_note = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["target_user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} #{self.pk}"
