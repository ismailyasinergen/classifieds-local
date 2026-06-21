# ACTION_LOG_DATE_FILTER_SAFETY_V94_TESTS
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal


class TrustSafetyActionLogDateFilterSafetyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="v94-action-log-admin@classifieds.local",
            username="v94_action_log_admin",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.appellant = User.objects.create_user(
            email="v94-action-log-user@classifieds.local",
            username="v94_action_log_user",
            password="Testpass12345",
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)
        self.log_url = reverse("accounts:trust_safety_action_log")
        self.export_url = reverse("accounts:trust_safety_action_log_export")

    def _aware(self, day, clock=time.min):
        return timezone.make_aware(
            datetime.combine(day, clock),
            timezone.get_current_timezone(),
        )

    def _appeal_decision(self, decision_note, reviewed_at, status=ModerationAppeal.Status.APPROVED):
        return ModerationAppeal.objects.create(
            appellant=self.appellant,
            message=f"Message for {decision_note}",
            status=status,
            decision_note=decision_note,
            admin_note=f"Internal note for {decision_note}",
            reviewed_by=self.admin,
            reviewed_at=reviewed_at,
        )

    def test_page_date_from_and_to_are_inclusive_for_appeal_decisions(self):
        target_day = timezone.localdate() - timedelta(days=5)
        self._appeal_decision(
            "v94 older action log decision",
            self._aware(target_day - timedelta(days=1), time.max),
        )
        self._appeal_decision(
            "v94 target action log decision",
            self._aware(target_day, time.max),
        )
        self._appeal_decision(
            "v94 newer action log decision",
            self._aware(target_day + timedelta(days=1), time.min),
        )

        response = self.client.get(
            self.log_url,
            {"type": "appeal", "date_from": target_day.isoformat(), "date_to": target_day.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v94 target action log decision")
        self.assertNotContains(response, "v94 older action log decision")
        self.assertNotContains(response, "v94 newer action log decision")
        self.assertContains(response, f'value="{target_day.isoformat()}"', count=2)
        self.assertEqual(response.context["paginator"].count, 1)

    def test_page_invalid_date_returns_no_results_and_warning(self):
        self._appeal_decision(
            "v94 action log decision hidden by invalid date",
            timezone.now(),
        )

        response = self.client.get(self.log_url, {"date_from": "not-a-date"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter valid action log dates in YYYY-MM-DD format.")
        self.assertContains(response, 'value="not-a-date"')
        self.assertContains(response, "No actions match this filter.")
        self.assertNotContains(response, "v94 action log decision hidden by invalid date")
        self.assertEqual(response.context["paginator"].count, 0)

    def test_page_reversed_date_range_returns_no_results_and_warning(self):
        self._appeal_decision(
            "v94 action log decision hidden by reversed range",
            timezone.now(),
        )
        today = timezone.localdate()

        response = self.client.get(
            self.log_url,
            {
                "date_from": today.isoformat(),
                "date_to": (today - timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "From date cannot be after To date.")
        self.assertContains(response, "No actions match this filter.")
        self.assertNotContains(response, "v94 action log decision hidden by reversed range")
        self.assertEqual(response.context["paginator"].count, 0)

    def test_export_csv_uses_same_valid_date_filter(self):
        target_day = timezone.localdate() - timedelta(days=4)
        self._appeal_decision(
            "v94 export older decision",
            self._aware(target_day - timedelta(days=1), time.max),
        )
        self._appeal_decision(
            "v94 export target decision",
            self._aware(target_day, time.max),
        )
        self._appeal_decision(
            "v94 export newer decision",
            self._aware(target_day + timedelta(days=1), time.min),
        )

        response = self.client.get(
            self.export_url,
            {"type": "appeal", "date_from": target_day.isoformat(), "date_to": target_day.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        body = response.content.decode("utf-8")
        self.assertIn("record_type,record_id,status,action,date", body)
        self.assertIn("v94 export target decision", body)
        self.assertNotIn("v94 export older decision", body)
        self.assertNotIn("v94 export newer decision", body)

    def test_export_csv_uses_same_invalid_date_filter_safety(self):
        self._appeal_decision(
            "v94 export decision hidden by invalid date",
            timezone.now(),
        )

        response = self.client.get(self.export_url, {"date_to": "2026-99-99"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("record_type,record_id,status,action,date", body)
        self.assertNotIn("v94 export decision hidden by invalid date", body)
