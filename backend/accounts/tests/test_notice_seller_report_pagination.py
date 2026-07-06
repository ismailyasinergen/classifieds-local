from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import ModerationNotice, UserReport


class NoticeSellerReportPaginationTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            username="pagination_admin",
            email="pagination_admin@classifieds.local",
            password="Testpass12345",
        )

        self.seller = User.objects.create_user(
            username="pagination_seller",
            email="pagination_seller@classifieds.local",
            password="Testpass12345",
        )

        self.buyer = User.objects.create_user(
            username="pagination_buyer",
            email="pagination_buyer@classifieds.local",
            password="Testpass12345",
        )

    def _create_notice(self, index, *, is_read=False):
        return ModerationNotice.objects.create(
            recipient=self.buyer,
            title=f"Pagination notice {index:02d}",
            body=f"Notice body {index:02d}",
            notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
            is_read=is_read,
        )

    def _create_seller_report(self, index, *, reporter=None, status=None, details_prefix="seller pagination"):
        return UserReport.objects.create(
            reported_user=self.seller,
            reporter=reporter or self.buyer,
            reasons=[UserReport.Reason.SCAM],
            details=f"{details_prefix} report {index:02d}",
            status=status or UserReport.Status.PENDING,
        )

    def test_notices_are_paginated_and_keep_read_filter(self):
        for index in range(30):
            self._create_notice(index, is_read=False)

        for index in range(3):
            self._create_notice(100 + index, is_read=True)

        self.client.force_login(self.buyer)

        response = self.client.get(reverse("accounts:moderation_notices"), {"read": "unread"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 30)
        self.assertEqual(len(response.context["notices"]), 25)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "?read=unread&page=2")

        response = self.client.get(
            reverse("accounts:moderation_notices"),
            {"read": "unread", "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 30)
        self.assertEqual(len(response.context["notices"]), 5)
        self.assertContains(response, "?read=unread&page=1")

    def test_my_seller_reports_are_paginated_and_keep_status_filter(self):
        for index in range(30):
            self._create_seller_report(index, status=UserReport.Status.PENDING)

        for index in range(3):
            self._create_seller_report(100 + index, status=UserReport.Status.REVIEWED)

        self.client.force_login(self.buyer)

        response = self.client.get(reverse("accounts:my_user_reports"), {"status": UserReport.Status.PENDING})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 30)
        self.assertEqual(len(response.context["reports"]), 25)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "?status=pending&page=2")

        response = self.client.get(
            reverse("accounts:my_user_reports"),
            {"status": UserReport.Status.PENDING, "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 30)
        self.assertEqual(len(response.context["reports"]), 5)
        self.assertContains(response, "?status=pending&page=1")

    def test_admin_seller_reports_are_paginated_and_keep_filters(self):
        for index in range(30):
            self._create_seller_report(
                index,
                status=UserReport.Status.PENDING,
                details_prefix="needle",
            )

        for index in range(3):
            self._create_seller_report(
                100 + index,
                status=UserReport.Status.REVIEWED,
                details_prefix="needle",
            )

        for index in range(2):
            self._create_seller_report(
                200 + index,
                status=UserReport.Status.PENDING,
                details_prefix="other",
            )

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("accounts:user_report_queue"),
            {"status": UserReport.Status.PENDING, "q": "needle"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 30)
        self.assertEqual(len(response.context["reports"]), 25)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "?status=pending&amp;q=needle&page=2")

        response = self.client.get(
            reverse("accounts:user_report_queue"),
            {"status": UserReport.Status.PENDING, "q": "needle", "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 30)
        self.assertEqual(len(response.context["reports"]), 5)
        self.assertContains(response, "?status=pending&amp;q=needle&page=1")
