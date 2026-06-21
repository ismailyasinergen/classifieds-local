# APPEAL_QUEUE_DATE_FILTER_SAFETY_V93_TESTS
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal


class ModerationAppealQueueDateFilterSafetyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="v93-appeal-admin@classifieds.local",
            username="v93_appeal_admin",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.appellant = User.objects.create_user(
            email="v93-appeal-user@classifieds.local",
            username="v93_appeal_user",
            password="Testpass12345",
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)
        self.queue_url = reverse("accounts:moderation_appeal_queue")

    def _appeal(self, message):
        return ModerationAppeal.objects.create(
            appellant=self.appellant,
            message=message,
            status=ModerationAppeal.Status.PENDING,
        )

    def test_queue_date_from_and_to_are_inclusive_for_created_at_dates(self):
        older = self._appeal("v93 older appeal")
        target = self._appeal("v93 target appeal")
        newer = self._appeal("v93 newer appeal")

        target_day = timezone.localdate() - timedelta(days=5)
        older.created_at = timezone.make_aware(
            timezone.datetime.combine(target_day - timedelta(days=1), timezone.datetime.min.time()),
            timezone.get_current_timezone(),
        )
        target.created_at = timezone.make_aware(
            timezone.datetime.combine(target_day, timezone.datetime.max.time()),
            timezone.get_current_timezone(),
        )
        newer.created_at = timezone.make_aware(
            timezone.datetime.combine(target_day + timedelta(days=1), timezone.datetime.min.time()),
            timezone.get_current_timezone(),
        )
        older.save(update_fields=["created_at"])
        target.save(update_fields=["created_at"])
        newer.save(update_fields=["created_at"])

        response = self.client.get(
            self.queue_url,
            {"date_from": target_day.isoformat(), "date_to": target_day.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v93 target appeal")
        self.assertNotContains(response, "v93 older appeal")
        self.assertNotContains(response, "v93 newer appeal")
        self.assertContains(response, f"value=\"{target_day.isoformat()}\"", count=2)

    def test_queue_invalid_date_returns_no_results_and_warning(self):
        self._appeal("v93 visible appeal should be hidden by invalid date")

        response = self.client.get(self.queue_url, {"date_from": "not-a-date"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter valid appeal queue dates in YYYY-MM-DD format.")
        self.assertContains(response, "value=\"not-a-date\"")
        self.assertNotContains(response, "v93 visible appeal should be hidden by invalid date")
        self.assertEqual(response.context["paginator"].count, 0)

    def test_queue_reversed_date_range_returns_no_results_and_warning(self):
        self._appeal("v93 visible appeal should be hidden by reversed date range")
        today = timezone.localdate()

        response = self.client.get(
            self.queue_url,
            {
                "date_from": today.isoformat(),
                "date_to": (today - timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "From date cannot be after To date.")
        self.assertNotContains(response, "v93 visible appeal should be hidden by reversed date range")
        self.assertEqual(response.context["paginator"].count, 0)

    def test_export_csv_uses_same_invalid_date_filter_safety(self):
        self._appeal("v93 export appeal should be hidden by invalid date")
        export_url = reverse("accounts:moderation_appeal_export_csv")

        response = self.client.get(export_url, {"date_to": "2026-99-99"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("appeal_id,status,appeal_type,created_at", body)
        self.assertNotIn("v93 export appeal should be hidden by invalid date", body)
