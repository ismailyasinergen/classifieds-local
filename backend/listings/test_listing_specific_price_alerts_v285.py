from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.listing_price_alerts_v285 import (
    get_listing_price_alert_candidates_v285,
)
from listings.models import Listing, ListingPriceAlert


class ListingSpecificPriceAlertsV285Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="v285-seller",
            email="v285-seller@classifieds.local",
            password="Testpass12345",
        )
        self.buyer = User.objects.create_user(
            username="v285-buyer",
            email="v285-buyer@classifieds.local",
            password="Testpass12345",
        )
        self.category = Category.objects.create(
            name="V285 category",
            slug="v285-category",
        )
        self.listing = self._listing("V285 alert listing")

    def _listing(self, title, *, price="100.00", status=Listing.Status.APPROVED):
        return Listing.objects.create(
            title=title,
            description="V285 price alert fixture.",
            price=Decimal(price),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=status,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def _toggle_url(self, listing=None):
        return reverse(
            "listings:listing_price_alert_toggle_v285",
            kwargs={"pk": (listing or self.listing).pk},
        )

    def _subscribe(self, listing=None, user=None):
        listing = listing or self.listing
        return ListingPriceAlert.objects.create(
            user=user or self.buyer,
            listing=listing,
            baseline_price=listing.price,
        )

    def _set_price(self, listing, value):
        listing.price = Decimal(value)
        listing.save(update_fields=["price"])
        listing.refresh_from_db()

    def test_toggle_requires_authentication_and_post(self):
        response = self.client.post(self._toggle_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

        self.client.force_login(self.buyer)
        response = self.client.get(self._toggle_url())
        self.assertEqual(response.status_code, 405)
        self.assertFalse(ListingPriceAlert.objects.exists())

    def test_toggle_creates_private_baseline_then_removes_subscription(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            self._toggle_url(),
            {"next": self.listing.get_absolute_url()},
        )
        self.assertRedirects(
            response,
            self.listing.get_absolute_url(),
            fetch_redirect_response=False,
        )
        alert = ListingPriceAlert.objects.get()
        self.assertEqual(alert.user, self.buyer)
        self.assertEqual(alert.baseline_price, Decimal("100.00"))

        self.client.post(self._toggle_url())
        self.assertFalse(ListingPriceAlert.objects.exists())

    def test_toggle_blocks_owner_nonpublic_expired_and_external_redirect(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self._toggle_url()).status_code, 403)

        self.client.force_login(self.buyer)
        pending = self._listing(
            "V285 pending",
            status=Listing.Status.PENDING,
        )
        self.assertEqual(
            self.client.post(self._toggle_url(pending)).status_code,
            404,
        )
        Listing.objects.filter(pk=self.listing.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.client.post(self._toggle_url()).status_code, 404)

        active = self._listing("V285 safe redirect")
        response = self.client.post(
            self._toggle_url(active),
            {"next": "https://attacker.example/redirect"},
        )
        self.assertRedirects(
            response,
            active.get_absolute_url(),
            fetch_redirect_response=False,
        )

    def test_detail_renders_accessible_private_alert_state_for_eligible_buyer(self):
        self.client.force_login(self.buyer)
        detail_url = self.listing.get_absolute_url()

        response = self.client.get(detail_url)
        self.assertContains(response, "Alert me to price drops")
        self.assertContains(response, 'aria-pressed="false"')
        self.assertContains(response, "Email me after this listing records")

        self._subscribe()
        response = self.client.get(detail_url)
        self.assertContains(response, "Stop price alert")
        self.assertContains(response, 'aria-pressed="true"')
        self.assertNotContains(response, str(self.buyer.pk))

        self.client.logout()
        response = self.client.get(detail_url)
        self.assertNotContains(response, "Stop price alert")
        self.assertNotContains(response, "Alert me to price drops")

    def test_valid_current_reduction_is_candidate_and_delivery_is_deduplicated_by_price(self):
        alert = self._subscribe()
        self._set_price(self.listing, "80.00")

        self.assertEqual(
            list(get_listing_price_alert_candidates_v285()),
            [alert],
        )

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            output = StringIO()
            call_command(
                "check_listing_price_alerts",
                "--send",
                "--site-base-url",
                "https://classifieds.local",
                stdout=output,
            )
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn("Price drop: V285 alert listing", mail.outbox[0].subject)
            self.assertIn("100.00 TL", mail.outbox[0].body)
            self.assertIn("80.00 TL", mail.outbox[0].body)
            self.assertNotIn(self.seller.email, mail.outbox[0].body)

            call_command("check_listing_price_alerts", "--send", stdout=StringIO())
            self.assertEqual(len(mail.outbox), 1)

        alert.refresh_from_db()
        self.assertEqual(alert.last_notified_price, Decimal("80.00"))
        self.assertIsNotNone(alert.last_notification_sent_at)

    def test_dry_run_does_not_send_or_advance_state(self):
        alert = self._subscribe()
        self._set_price(self.listing, "75.00")

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        ):
            output = StringIO()
            call_command("check_listing_price_alerts", stdout=output)

        alert.refresh_from_db()
        self.assertIn("Mode: DRY RUN", output.getvalue())
        self.assertEqual(len(getattr(mail, "outbox", [])), 0)
        self.assertIsNone(alert.last_notified_price)

    def test_missing_recipient_is_skipped_without_advancing_state(self):
        self.buyer.email = ""
        self.buyer.save(update_fields=["email"])
        alert = self._subscribe()
        self._set_price(self.listing, "70.00")

        output = StringIO()
        call_command("check_listing_price_alerts", "--send", stdout=output)

        alert.refresh_from_db()
        self.assertIn("subscriber has no email address", output.getvalue())
        self.assertIsNone(alert.last_notified_price)
        self.assertIsNone(alert.last_notification_sent_at)

    def test_stale_mismatch_and_latest_increase_are_not_candidates(self):
        stale = self._subscribe()
        self._set_price(self.listing, "80.00")
        Listing.objects.filter(pk=self.listing.pk).update(price=Decimal("70.00"))

        increased_listing = self._listing("V285 increased")
        increased = self._subscribe(increased_listing)
        self._set_price(increased_listing, "70.00")
        self._set_price(increased_listing, "80.00")

        candidates = list(get_listing_price_alert_candidates_v285())
        self.assertNotIn(stale, candidates)
        self.assertNotIn(increased, candidates)

    def test_baseline_nonreduced_and_nonpublic_listings_are_not_candidates(self):
        baseline = self._subscribe()
        pending_listing = self._listing("V285 later pending")
        pending = self._subscribe(pending_listing)
        self._set_price(pending_listing, "60.00")
        Listing.objects.filter(pk=pending_listing.pk).update(
            status=Listing.Status.PENDING
        )

        candidates = list(get_listing_price_alert_candidates_v285())
        self.assertNotIn(baseline, candidates)
        self.assertNotIn(pending, candidates)

    def test_candidate_query_count_is_constant_when_alert_count_grows(self):
        for index in range(5):
            listing = self._listing(f"V285 query listing {index}")
            self._subscribe(listing)
            self._set_price(listing, "50.00")

        with CaptureQueriesContext(connection) as captured:
            candidates = list(get_listing_price_alert_candidates_v285())
            values = [
                (alert.user.email, alert.listing.title)
                for alert in candidates
            ]

        self.assertEqual(len(captured), 1)
        self.assertEqual(len(values), 5)

    def test_csrf_protection_applies_to_toggle(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)

        response = client.post(self._toggle_url())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ListingPriceAlert.objects.exists())
