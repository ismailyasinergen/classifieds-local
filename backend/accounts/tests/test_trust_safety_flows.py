from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import (
    ModerationAppeal,
    ModerationAppealAttachment,
    ModerationNotice,
    UserProfile,
    UserReport,
)
from listings.models import Listing

try:
    from categories.models import Category
except Exception:
    Category = None


def _unique(prefix):
    return f"{prefix}-{uuid4().hex[:10]}"


def _listing_status(name, fallback):
    return getattr(getattr(Listing, "Status", object), name, fallback)


LISTING_APPROVED = _listing_status("APPROVED", "approved")
LISTING_PENDING = _listing_status("PENDING", "pending")
LISTING_SUSPENDED = _listing_status("SUSPENDED", "suspended")


class TrustSafetyFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="test_admin",
            email="test_admin@classifieds.local",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )

        self.seller = User.objects.create_user(
            username="test_seller",
            email="test_seller@classifieds.local",
            password="Testpass12345",
        )

        self.buyer = User.objects.create_user(
            username="test_buyer",
            email="test_buyer@classifieds.local",
            password="Testpass12345",
        )

        self.profile, _ = UserProfile.objects.get_or_create(user=self.seller)

    def _create_category(self):
        if Category is None:
            return None

        kwargs = {}

        for field in Category._meta.concrete_fields:
            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.has_default() or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue

            if field.null or field.blank:
                continue

            if isinstance(field, models.CharField):
                if field.choices:
                    kwargs[field.name] = field.choices[0][0]
                elif field.name == "slug":
                    kwargs[field.name] = _unique("category-slug")
                else:
                    kwargs[field.name] = _unique("category")[: field.max_length or 50]
            elif isinstance(field, models.TextField):
                kwargs[field.name] = "Test category"
            elif isinstance(field, models.BooleanField):
                kwargs[field.name] = False
            elif isinstance(field, models.IntegerField):
                kwargs[field.name] = 1
            elif isinstance(field, models.ForeignKey):
                kwargs[field.name] = None

        return Category.objects.create(**kwargs)

    def _create_listing(self, *, owner=None, status=None, title=None, **extra):
        owner = owner or self.seller
        category = self._create_category()

        kwargs = {
            "owner": owner,
            "title": title or _unique("Test listing"),
            "description": "Test listing description",
            "price": Decimal("100.00"),
            "status": status or LISTING_APPROVED,
        }

        if category is not None:
            kwargs["category"] = category

        kwargs.update(extra)

        for field in Listing._meta.concrete_fields:
            if field.name in kwargs:
                continue

            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.has_default() or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue

            if field.null or field.blank:
                continue

            if isinstance(field, models.ForeignKey):
                if field.remote_field.model == get_user_model():
                    kwargs[field.name] = owner
                elif Category is not None and field.remote_field.model == Category:
                    kwargs[field.name] = category or self._create_category()
            elif isinstance(field, models.CharField):
                if field.choices:
                    kwargs[field.name] = field.choices[0][0]
                elif field.name == "slug":
                    kwargs[field.name] = _unique("listing-slug")
                else:
                    kwargs[field.name] = _unique(field.name)[: field.max_length or 50]
            elif isinstance(field, models.TextField):
                kwargs[field.name] = f"Test value for {field.name}"
            elif isinstance(field, models.DecimalField):
                kwargs[field.name] = Decimal("100.00")
            elif isinstance(field, models.FloatField):
                kwargs[field.name] = 1.0
            elif isinstance(field, models.IntegerField):
                kwargs[field.name] = 1
            elif isinstance(field, models.BooleanField):
                kwargs[field.name] = False
            elif isinstance(field, models.DateTimeField):
                kwargs[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                kwargs[field.name] = timezone.localdate()

        return Listing.objects.create(**kwargs)

    def _suspend_seller(self):
        self.profile.seller_suspended_until = timezone.now() + timezone.timedelta(days=7)
        self.profile.seller_suspension_reason = "Automated test suspension."
        self.profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    def _create_user_report(self, *, source_listing=None):
        return UserReport.objects.create(
            reported_user=self.seller,
            reporter=self.buyer,
            source_listing=source_listing,
            reasons=[UserReport.Reason.SCAM],
            details="Buyer reported a seller safety issue.",
        )

    def test_user_report_suspend_seller_hides_active_listings_and_creates_appealable_notice(self):
        source_listing = self._create_listing(
            owner=self.seller,
            status=LISTING_APPROVED,
            title="Reported approved listing",
        )
        pending_listing = self._create_listing(
            owner=self.seller,
            status=LISTING_PENDING,
            title="Pending listing hidden by seller suspension",
        )
        listing_level_suspended = self._create_listing(
            owner=self.seller,
            status=LISTING_SUSPENDED,
            title="Listing-level suspended listing remains untouched",
        )
        listing_level_suspended.suspended_due_to_seller = False
        listing_level_suspended.status_before_seller_suspension = ""
        listing_level_suspended.save(
            update_fields=[
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )

        report = self._create_user_report(source_listing=source_listing)

        self.client.login(username="test_admin", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:user_report_suspend", args=[report.pk]),
            {
                "duration_days": "14",
                "admin_note": "Confirmed seller suspension from report queue.",
                "reporter_note": "We reviewed your report and restricted this seller.",
            },
        )

        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.profile.refresh_from_db()
        source_listing.refresh_from_db()
        pending_listing.refresh_from_db()
        listing_level_suspended.refresh_from_db()

        self.assertEqual(report.status, UserReport.Status.REVIEWED)
        self.assertEqual(report.action_taken, UserReport.Action.SUSPENDED_SELLER)
        self.assertIsNotNone(report.action_taken_at)

        self.assertTrue(self.profile.is_seller_suspended)
        self.assertEqual(
            self.profile.seller_suspension_reason,
            "Confirmed seller suspension from report queue.",
        )

        self.assertEqual(source_listing.status, LISTING_SUSPENDED)
        self.assertTrue(source_listing.suspended_due_to_seller)
        self.assertEqual(source_listing.status_before_seller_suspension, LISTING_APPROVED)

        self.assertEqual(pending_listing.status, LISTING_SUSPENDED)
        self.assertTrue(pending_listing.suspended_due_to_seller)
        self.assertEqual(pending_listing.status_before_seller_suspension, LISTING_PENDING)

        self.assertEqual(listing_level_suspended.status, LISTING_SUSPENDED)
        self.assertFalse(listing_level_suspended.suspended_due_to_seller)
        self.assertEqual(listing_level_suspended.status_before_seller_suspension, "")

        seller_notice = ModerationNotice.objects.get(
            recipient=self.seller,
            notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
            user_report=report,
        )
        self.assertIn("temporarily suspended", seller_notice.title.lower())
        self.assertIn("2 active listing(s)", seller_notice.body)
        self.assertFalse(ModerationAppeal.objects.filter(moderation_notice=seller_notice).exists())

        self.client.login(username="test_seller", password="Testpass12345")
        appeal_response = self.client.post(
            reverse("accounts:moderation_appeal_create", args=[seller_notice.pk]),
            {"message": "Please review this report-based seller suspension."},
        )

        self.assertEqual(appeal_response.status_code, 302)

        appeal = ModerationAppeal.objects.get(
            appellant=self.seller,
            moderation_notice=seller_notice,
        )
        self.assertEqual(appeal.status, ModerationAppeal.Status.PENDING)
        self.assertEqual(appeal.appeal_type, ModerationAppeal.AppealType.SELLER_ACTION)
        self.assertEqual(appeal.user_report, report)

        self.profile.refresh_from_db()
        source_listing.refresh_from_db()
        pending_listing.refresh_from_db()

        self.assertTrue(self.profile.is_seller_suspended)
        self.assertEqual(source_listing.status, LISTING_SUSPENDED)
        self.assertTrue(source_listing.suspended_due_to_seller)
        self.assertEqual(pending_listing.status, LISTING_SUSPENDED)
        self.assertTrue(pending_listing.suspended_due_to_seller)

    def test_report_suspension_appeal_approval_does_not_auto_lift_or_restore(self):
        source_listing = self._create_listing(
            owner=self.seller,
            status=LISTING_APPROVED,
            title="Report suspension appeal listing",
        )
        report = self._create_user_report(source_listing=source_listing)

        self.client.login(username="test_admin", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:user_report_suspend", args=[report.pk]),
            {
                "duration_days": "10",
                "admin_note": "Suspend seller before appeal.",
                "reporter_note": "Action was taken.",
            },
        )
        self.assertEqual(response.status_code, 302)

        seller_notice = ModerationNotice.objects.get(
            recipient=self.seller,
            notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
            user_report=report,
        )

        self.client.login(username="test_seller", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:moderation_appeal_create", args=[seller_notice.pk]),
            {"message": "I appeal this suspension."},
        )
        self.assertEqual(response.status_code, 302)

        appeal = ModerationAppeal.objects.get(
            appellant=self.seller,
            moderation_notice=seller_notice,
        )

        self.client.login(username="test_admin", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:moderation_appeal_decide", args=[appeal.pk, "approve"]),
            {
                "decision_note": "Appeal approved; manual lift still required.",
                "admin_note": "Verify no automatic restriction changes.",
                "evidence_reviewed": "yes",
            },
        )

        self.assertEqual(response.status_code, 302)

        appeal.refresh_from_db()
        self.profile.refresh_from_db()
        source_listing.refresh_from_db()

        self.assertEqual(appeal.status, ModerationAppeal.Status.APPROVED)
        self.assertTrue(self.profile.is_seller_suspended)
        self.assertEqual(source_listing.status, LISTING_SUSPENDED)
        self.assertTrue(source_listing.suspended_due_to_seller)
        self.assertEqual(source_listing.status_before_seller_suspension, LISTING_APPROVED)

    def test_lift_seller_suspension_restores_only_seller_hidden_listing(self):
        seller_hidden = self._create_listing(
            owner=self.seller,
            status=LISTING_SUSPENDED,
            title="Seller hidden listing",
        )
        seller_hidden.suspended_due_to_seller = True
        seller_hidden.status_before_seller_suspension = LISTING_APPROVED
        seller_hidden.save(
            update_fields=[
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )

        listing_level_suspended = self._create_listing(
            owner=self.seller,
            status=LISTING_SUSPENDED,
            title="Listing level suspended listing",
        )
        listing_level_suspended.suspended_due_to_seller = False
        listing_level_suspended.status_before_seller_suspension = ""
        listing_level_suspended.save(
            update_fields=[
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )

        self._suspend_seller()

        self.client.login(username="test_admin", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:trust_safety_lift_seller_suspension", args=[self.seller.pk])
        )

        self.assertEqual(response.status_code, 302)

        seller_hidden.refresh_from_db()
        listing_level_suspended.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(seller_hidden.status, LISTING_APPROVED)
        self.assertFalse(seller_hidden.suspended_due_to_seller)
        self.assertEqual(seller_hidden.status_before_seller_suspension, "")

        self.assertEqual(listing_level_suspended.status, LISTING_SUSPENDED)
        self.assertFalse(listing_level_suspended.suspended_due_to_seller)

        self.assertIsNone(self.profile.seller_suspended_until)

    def test_appeal_submission_does_not_lift_seller_restriction(self):
        self._suspend_seller()

        notice = ModerationNotice.objects.create(
            recipient=self.seller,
            title="Seller account suspended",
            body="Your seller account was suspended.",
            notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
        )

        self.client.login(username="test_seller", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:moderation_appeal_create", args=[notice.pk]),
            {"message": "Please review this seller suspension."},
        )

        self.assertEqual(response.status_code, 302)

        appeal = ModerationAppeal.objects.get(appellant=self.seller, moderation_notice=notice)
        self.assertEqual(appeal.status, ModerationAppeal.Status.PENDING)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_seller_suspended)

    def test_appeal_approval_does_not_auto_lift_or_restore(self):
        self._suspend_seller()

        listing = self._create_listing(
            owner=self.seller,
            status=LISTING_SUSPENDED,
            title="Suspended listing for appeal",
        )
        listing.suspended_due_to_seller = True
        listing.status_before_seller_suspension = LISTING_APPROVED
        listing.save(
            update_fields=[
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )

        notice = ModerationNotice.objects.create(
            recipient=self.seller,
            title="Seller account suspended",
            body="Your seller account was suspended.",
            notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
            listing=listing,
        )

        appeal = ModerationAppeal.objects.create(
            appellant=self.seller,
            moderation_notice=notice,
            listing=listing,
            appeal_type=ModerationAppeal.AppealType.SELLER_ACTION,
            status=ModerationAppeal.Status.PENDING,
            message="Please review this appeal.",
        )

        self.client.login(username="test_admin", password="Testpass12345")
        response = self.client.post(
            reverse("accounts:moderation_appeal_decide", args=[appeal.pk, "approve"]),
            {
                "decision_note": "Appeal approved for test, manual resolution still required.",
                "admin_note": "Internal test note.",
                "evidence_reviewed": "yes",
            },
        )

        self.assertEqual(response.status_code, 302)

        appeal.refresh_from_db()
        listing.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(appeal.status, ModerationAppeal.Status.APPROVED)
        self.assertTrue(self.profile.is_seller_suspended)
        self.assertEqual(listing.status, LISTING_SUSPENDED)
        self.assertTrue(listing.suspended_due_to_seller)

    def test_appeal_evidence_zip_get_route_works(self):
        appeal = ModerationAppeal.objects.create(
            appellant=self.seller,
            appeal_type=ModerationAppeal.AppealType.SELLER_ACTION,
            status=ModerationAppeal.Status.PENDING,
            message="Appeal with test evidence.",
        )

        attachment = ModerationAppealAttachment(
            appeal=appeal,
            original_name="test-evidence.pdf",
            content_type="application/pdf",
            size=12,
        )
        attachment.file.save("test-evidence.pdf", ContentFile(b"%PDF-1.4 test"), save=True)

        self.client.login(username="test_admin", password="Testpass12345")
        response = self.client.get(
            reverse("accounts:moderation_appeal_evidence_zip", args=[appeal.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("appeal_", response["Content-Disposition"])
