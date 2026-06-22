# TRUST_SAFETY_EVENT_LOG_DATE_FILTER_SAFETY_V96_TESTS
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import TrustSafetyEvent


class TrustSafetyEventLogDateFilterSafetyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="v96-event-log-admin@classifieds.local",
            username="v96_event_log_admin",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.target_user = User.objects.create_user(
            email="v96-event-log-user@classifieds.local",
            username="v96_event_log_user",
            password="Testpass12345",
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)
        self.log_url = reverse("accounts:trust_safety_event_log")
        self.export_url = reverse("accounts:trust_safety_event_log_export")

    def _aware(self, day, clock=time.min):
        return timezone.make_aware(
            datetime.combine(day, clock),
            timezone.get_current_timezone(),
        )

    def _event(self, title, created_at, event_type=TrustSafetyEvent.EventType.SELLER_WARNED):
        event = TrustSafetyEvent.objects.create(
            actor=self.admin,
            target_user=self.target_user,
            event_type=event_type,
            title=title,
            public_note=f"Public note for {title}",
            internal_note=f"Internal note for {title}",
            metadata={"source": "v96-test"},
        )
        TrustSafetyEvent.objects.filter(pk=event.pk).update(created_at=created_at)
        event.refresh_from_db()
        return event

    def test_page_date_from_and_to_are_inclusive_for_events(self):
        target_day = timezone.localdate() - timedelta(days=3)
        self._event("v96 older trust safety event", self._aware(target_day - timedelta(days=1), time.max))
        self._event("v96 target trust safety event", self._aware(target_day, time.max))
        self._event("v96 newer trust safety event", self._aware(target_day + timedelta(days=1), time.min))

        response = self.client.get(
            self.log_url,
            {"date_from": target_day.isoformat(), "date_to": target_day.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v96 target trust safety event")
        self.assertNotContains(response, "v96 older trust safety event")
        self.assertNotContains(response, "v96 newer trust safety event")
        self.assertContains(response, f'value="{target_day.isoformat()}"', count=2)
        self.assertEqual(response.context["paginator"].count, 1)

    def test_page_invalid_date_returns_no_results_and_warning(self):
        self._event("v96 event hidden by invalid date", timezone.now())

        response = self.client.get(self.log_url, {"date_from": "not-a-date"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter valid Trust &amp; Safety event dates in YYYY-MM-DD format.")
        self.assertContains(response, 'value="not-a-date"')
        self.assertContains(response, "No Trust & Safety events match this filter.")
        self.assertNotContains(response, "v96 event hidden by invalid date")
        self.assertEqual(response.context["paginator"].count, 0)

    def test_page_reversed_date_range_returns_no_results_and_warning(self):
        self._event("v96 event hidden by reversed date range", timezone.now())
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
        self.assertContains(response, "No Trust & Safety events match this filter.")
        self.assertNotContains(response, "v96 event hidden by reversed date range")
        self.assertEqual(response.context["paginator"].count, 0)

    def test_export_csv_uses_same_valid_date_filter(self):
        target_day = timezone.localdate() - timedelta(days=2)
        self._event("v96 export older event", self._aware(target_day - timedelta(days=1), time.max))
        self._event("v96 export target event", self._aware(target_day, time.max))
        self._event("v96 export newer event", self._aware(target_day + timedelta(days=1), time.min))

        response = self.client.get(
            self.export_url,
            {"date_from": target_day.isoformat(), "date_to": target_day.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        body = response.content.decode("utf-8")
        self.assertIn("event_id,event_type,created_at,title", body)
        self.assertIn("v96 export target event", body)
        self.assertNotIn("v96 export older event", body)
        self.assertNotIn("v96 export newer event", body)

    def test_export_csv_uses_same_invalid_date_filter_safety(self):
        self._event("v96 export event hidden by invalid date", timezone.now())

        response = self.client.get(self.export_url, {"date_to": "2026-99-99"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("event_id,event_type,created_at,title", body)
        self.assertNotIn("v96 export event hidden by invalid date", body)
