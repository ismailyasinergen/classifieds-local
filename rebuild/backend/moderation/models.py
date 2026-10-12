import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MaxLengthValidator, RegexValidator
from django.utils import timezone


class ModerationDecision(models.Model):
    class Outcome(models.TextChoices):
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"

    revision = models.OneToOneField("listings.ListingRevision", on_delete=models.PROTECT, related_name="moderation_decision")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="moderation_decisions")
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    reason = models.TextField()
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-decided_at", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(outcome__in=["approved", "rejected"]),
                                              name="moderation_valid_decision")]


class Restriction(models.Model):
    """Only public visibility is restricted in this slice; targets are independent."""
    listing = models.ForeignKey("listings.Listing", null=True, blank=True, on_delete=models.PROTECT, related_name="visibility_restrictions")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="visibility_restrictions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_visibility_restrictions")
    reason = models.TextField()
    begins_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=(models.Q(listing__isnull=False, seller__isnull=True)
                                               | models.Q(listing__isnull=True, seller__isnull=False)),
                                   name="moderation_restriction_target_xor"),
            models.CheckConstraint(condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=models.F("begins_at")),
                                   name="moderation_restriction_valid_interval"),
        ]


class MessagingRestriction(models.Model):
    """Independent account messaging policy; public visibility is unchanged."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="messaging_restrictions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_messaging_restrictions")
    reason = models.TextField(validators=[MaxLengthValidator(2000)])
    begins_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        permissions = [("restrict_messaging", "Can restrict account messaging")]
        constraints = [
            models.CheckConstraint(condition=models.Q(reason__regex=r"\S"),
                                   name="moderation_messaging_reason_not_blank"),
            models.CheckConstraint(condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=models.F("begins_at")),
                                   name="moderation_messaging_valid_interval"),
        ]


class PriceChange(models.Model):
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="price_changes")
    revision = models.OneToOneField("listings.ListingRevision", on_delete=models.PROTECT, related_name="price_change")
    previous_revision = models.ForeignKey("listings.ListingRevision", on_delete=models.PROTECT, related_name="+")
    old_amount = models.DecimalField(max_digits=18, decimal_places=2)
    new_amount = models.DecimalField(max_digits=18, decimal_places=2)
    old_currency = models.CharField(max_length=3)
    new_currency = models.CharField(max_length=3)
    published_at = models.DateTimeField(default=timezone.now)

    @property
    def is_price_drop(self):
        return self.old_currency == self.new_currency and self.new_amount < self.old_amount

    class Meta:
        ordering = ["-published_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(old_amount__gte=0, new_amount__gte=0),
                                   name="moderation_nonnegative_price_history"),
        ]


class CaseRecord(models.Model):
    """Ordinary saves append history; privileged bulk maintenance is outside this boundary."""

    class Meta:
        abstract = True
        default_permissions = ()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Dosya geçmişi değiştirilemez.", code="immutable_case")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Dosya geçmişi silinemez.", code="immutable_case")


class ContentReport(CaseRecord):
    class TargetType(models.TextChoices):
        LISTING = "listing", "İlan"
        MESSAGE = "message", "Mesaj"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="content_reports")
    subject_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    target_type = models.CharField(max_length=7, choices=TargetType.choices)
    revision = models.ForeignKey("listings.ListingRevision", null=True, blank=True, on_delete=models.PROTECT, related_name="content_reports")
    message = models.ForeignKey("conversations.Message", null=True, blank=True, on_delete=models.PROTECT, related_name="content_reports")
    reason_code = models.CharField(max_length=20)
    explanation = models.TextField(validators=[MaxLengthValidator(2000)])
    evidence = models.JSONField()
    client_token = models.UUIDField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta(CaseRecord.Meta):
        abstract = False
        ordering = ["-created_at", "-pk"]
        permissions = [("review_reports", "Can review content reports")]
        indexes = [
            models.Index(fields=["reporter", "-created_at", "-id"], name="case_report_actor_recent"),
            models.Index(fields=["created_at", "id"], name="case_report_queue"),
        ]
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(target_type="listing", revision__isnull=False, message__isnull=True)
                | models.Q(target_type="message", revision__isnull=True, message__isnull=False)),
                name="case_report_target_xor"),
            models.CheckConstraint(condition=~models.Q(reporter=models.F("subject_user")), name="case_report_distinct_users"),
            models.CheckConstraint(condition=models.Q(explanation__regex=r"\S"), name="case_report_explanation"),
            models.UniqueConstraint(fields=["reporter", "revision"], condition=models.Q(revision__isnull=False), name="case_report_revision_unique"),
            models.UniqueConstraint(fields=["reporter", "message"], condition=models.Q(message__isnull=False), name="case_report_message_unique"),
            models.UniqueConstraint(fields=["reporter", "client_token"], name="case_report_token_unique"),
        ]


class ReportDecision(CaseRecord):
    class Action(models.TextChoices):
        NO_ACTION = "no_action", "İşlem yok"
        HIDE_LISTING = "hide_listing", "İlanı gizle"
        RESTRICT_MESSAGING = "restrict_messaging", "Mesajlaşmayı kısıtla"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(ContentReport, on_delete=models.PROTECT, related_name="decision")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    action = models.CharField(max_length=18, choices=Action.choices)
    reason = models.TextField(validators=[MaxLengthValidator(2000)])
    decided_at = models.DateTimeField(default=timezone.now)
    visibility_restriction = models.OneToOneField(Restriction, null=True, blank=True, on_delete=models.PROTECT, related_name="case_decision")
    messaging_restriction = models.OneToOneField(MessagingRestriction, null=True, blank=True, on_delete=models.PROTECT, related_name="case_decision")

    class Meta(CaseRecord.Meta):
        abstract = False
        ordering = ["-decided_at", "-pk"]
        indexes = [models.Index(fields=["-decided_at", "-id"], name="case_decision_recent")]
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(action="no_action", visibility_restriction__isnull=True, messaging_restriction__isnull=True)
                | models.Q(action="hide_listing", visibility_restriction__isnull=False, messaging_restriction__isnull=True)
                | models.Q(action="restrict_messaging", visibility_restriction__isnull=True, messaging_restriction__isnull=False)),
                name="case_decision_action_target"),
            models.CheckConstraint(condition=models.Q(reason__regex=r"\S"), name="case_decision_reason"),
        ]


class Appeal(CaseRecord):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision = models.OneToOneField(ReportDecision, on_delete=models.PROTECT, related_name="appeal")
    appellant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="case_appeals")
    explanation = models.TextField(validators=[MaxLengthValidator(2000)])
    client_token = models.UUIDField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta(CaseRecord.Meta):
        abstract = False
        ordering = ["-created_at", "-pk"]
        permissions = [("review_appeals", "Can review case appeals")]
        indexes = [models.Index(fields=["appellant", "-created_at", "-id"], name="case_appeal_actor_recent")]
        constraints = [
            models.UniqueConstraint(fields=["appellant", "client_token"], name="case_appeal_token_unique"),
            models.CheckConstraint(condition=models.Q(explanation__regex=r"\S"), name="case_appeal_explanation"),
        ]


class AppealDecision(CaseRecord):
    class Outcome(models.TextChoices):
        UPHOLD = "uphold", "Kararı koru"
        REVOKE = "revoke", "İtirazı kabul et"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appeal = models.OneToOneField(Appeal, on_delete=models.PROTECT, related_name="result")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    outcome = models.CharField(max_length=6, choices=Outcome.choices)
    reason = models.TextField(validators=[MaxLengthValidator(2000)])
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta(CaseRecord.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(condition=models.Q(outcome__in=["uphold", "revoke"]), name="case_appeal_valid_outcome"),
            models.CheckConstraint(condition=models.Q(reason__regex=r"\S"), name="case_appeal_decision_reason"),
        ]


class CaseAuditEvent(CaseRecord):
    class Action(models.TextChoices):
        REPORT_CREATED = "report_created", "Bildirim oluşturuldu"
        REPORT_DECIDED = "report_decided", "Bildirim kararı verildi"
        APPEAL_CREATED = "appeal_created", "İtiraz oluşturuldu"
        APPEAL_DECIDED = "appeal_decided", "İtiraz kararı verildi"
        EVIDENCE_VIEWED = "evidence_viewed", "Kanıt okundu"
        EVIDENCE_MEDIA_VIEWED = "evidence_media_viewed", "Kanıt görseli okundu"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    report = models.ForeignKey(ContentReport, on_delete=models.PROTECT, related_name="audit_events")
    appeal = models.ForeignKey(Appeal, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=21, choices=Action.choices)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta(CaseRecord.Meta):
        abstract = False


class CaseSubmissionReceipt(CaseRecord):
    class Operation(models.TextChoices):
        REPORT = "report", "Bildirim"
        APPEAL = "appeal", "İtiraz"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    operation = models.CharField(max_length=6, choices=Operation.choices)
    client_token = models.UUIDField()
    fingerprint = models.CharField(max_length=64, validators=[RegexValidator(r"\A[0-9a-f]{64}\Z")])
    report = models.ForeignKey(ContentReport, null=True, blank=True, on_delete=models.PROTECT, related_name="receipts")
    appeal = models.ForeignKey(Appeal, null=True, blank=True, on_delete=models.PROTECT, related_name="receipts")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta(CaseRecord.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=["actor", "operation", "client_token"], name="case_receipt_token_unique"),
            models.CheckConstraint(condition=(
                models.Q(operation="report", report__isnull=False, appeal__isnull=True)
                | models.Q(operation="appeal", report__isnull=True, appeal__isnull=False)),
                name="case_receipt_result_xor"),
        ]
