from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.listing_price_alert_management_v289 import (
    PRICE_ALERT_MANAGEMENT_PAGE_SIZE_V289,
    build_price_alert_management_page_v289,
)
from listings.models import (
    Listing,
    ListingPriceAlert,
    NotificationDeliveryEvent,
    NotificationDeliveryPreference,
)


class PriceAlertManagementUiV289Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            username="v289-buyer",
            email="v289-buyer@classifieds.local",
            password="Testpass12345",
        )
        self.other = User.objects.create_user(
            username="v289-other",
            email="v289-other@classifieds.local",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            username="v289-seller",
            email="v289-seller@classifieds.local",
            password="Testpass12345",
        )
        self.category = Category.objects.create(name="V289", slug="v289")
        self.listing = self._listing("V289 public listing")
        self.url = reverse("listings:listing_price_alert_management_v289")

    def _listing(
        self,
        title,
        *,
        price="80.00",
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            title=title,
            description="V289 price-alert management fixture.",
            price=Decimal(price),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=status,
            expires_at=(
                expires_at
                if expires_at is not None
                else timezone.now() + timedelta(days=30)
            ),
        )

    def _alert(self, listing=None, *, user=None, baseline="100.00"):
        return ListingPriceAlert.objects.create(
            user=user or self.buyer,
            listing=listing or self.listing,
            baseline_price=Decimal(baseline),
        )

    def _remove_url(self, alert):
        return reverse(
            "listings:listing_price_alert_remove_v289",
            kwargs={"pk": alert.pk},
        )

    def test_management_page_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={self.url}",
        )

    def test_page_lists_only_current_users_alerts_with_public_details(self):
        own = self._alert()
        other_listing = self._listing("Other user's private subscription")
        self._alert(other_listing, user=self.other)
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "V289 public listing")
        self.assertContains(response, "Price when added")
        self.assertContains(response, "100.00 TL")
        self.assertContains(response, "Current price")
        self.assertContains(response, "80.00 TL")
        self.assertContains(response, own.listing.get_absolute_url())
        self.assertNotContains(response, "Other user's private subscription")

    def test_nonpublic_and_expired_listings_hide_current_details(self):
        pending = self._listing(
            "V289 confidential pending title",
            price="712.34",
            status=Listing.Status.PENDING,
        )
        expired = self._listing(
            "V289 confidential expired title",
            price="845.67",
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self._alert(pending)
        self._alert(expired)
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "Listing unavailable", count=2)
        self.assertContains(response, "Paused while listing is unavailable", count=2)
        self.assertNotContains(response, pending.title)
        self.assertNotContains(response, expired.title)
        self.assertNotContains(response, "712.34 TL")
        self.assertNotContains(response, "845.67 TL")
        self.assertNotContains(response, pending.get_absolute_url())
        self.assertNotContains(response, expired.get_absolute_url())

    def test_remove_post_deletes_owned_alert_and_redirects(self):
        alert = self._alert()
        self.client.force_login(self.buyer)

        response = self.client.post(self._remove_url(alert))

        self.assertRedirects(response, self.url)
        self.assertFalse(ListingPriceAlert.objects.filter(pk=alert.pk).exists())

    def test_remove_cannot_access_another_users_alert(self):
        alert = self._alert(user=self.other)
        self.client.force_login(self.buyer)

        response = self.client.post(self._remove_url(alert))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ListingPriceAlert.objects.filter(pk=alert.pk).exists())

    def test_remove_requires_post_and_csrf(self):
        alert = self._alert()
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self._remove_url(alert)).status_code, 405)

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.buyer)
        self.assertEqual(csrf_client.post(self._remove_url(alert)).status_code, 403)
        self.assertTrue(ListingPriceAlert.objects.filter(pk=alert.pk).exists())

    def test_unavailable_alert_can_still_be_removed(self):
        listing = self._listing(
            "V289 archived removable",
            status=Listing.Status.ARCHIVED,
        )
        alert = self._alert(listing)
        self.client.force_login(self.buyer)

        response = self.client.post(self._remove_url(alert))

        self.assertRedirects(response, self.url)
        self.assertFalse(ListingPriceAlert.objects.filter(pk=alert.pk).exists())

    def test_global_preference_off_keeps_subscription_and_shows_status(self):
        alert = self._alert()
        NotificationDeliveryPreference.objects.create(
            user=self.buyer,
            listing_price_alert_email_enabled=False,
        )
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "Listing price-alert emails are off")
        self.assertContains(response, "Your subscriptions remain saved")
        self.assertContains(response, "Email delivery disabled")
        self.assertContains(
            response,
            reverse("accounts:notification_delivery_preferences_v288"),
        )
        self.assertTrue(ListingPriceAlert.objects.filter(pk=alert.pk).exists())

    def test_missing_preference_retains_backward_compatible_enabled_state(self):
        self._alert()
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        self.assertNotContains(response, "Listing price-alert emails are off")
        self.assertFalse(NotificationDeliveryPreference.objects.exists())

    def test_last_delivery_and_created_dates_use_semantic_time_elements(self):
        alert = self._alert()
        alert.last_notification_sent_at = timezone.now()
        alert.save(update_fields=["last_notification_sent_at"])
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "Last email sent")
        self.assertContains(response, "<time", count=2)
        self.assertContains(response, 'datetime="')

    def test_empty_state_is_clear_and_actionable(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        self.assertContains(response, "No price alerts yet")
        self.assertContains(response, "Alert me to price drops")
        self.assertContains(response, reverse("listings:listing_list"))

    def test_pagination_is_bounded_and_preserves_deterministic_order(self):
        alerts = []
        for index in range(PRICE_ALERT_MANAGEMENT_PAGE_SIZE_V289 + 1):
            listing = self._listing(f"V289 paged {index:02d}")
            alerts.append(self._alert(listing))
        shared_time = timezone.now() - timedelta(hours=1)
        ListingPriceAlert.objects.filter(pk__in=[item.pk for item in alerts]).update(
            created_at=shared_time,
        )
        self.client.force_login(self.buyer)

        first = self.client.get(self.url)
        second = self.client.get(self.url, {"page": 2})

        first_ids = [item.pk for item in first.context["page_obj"].object_list]
        self.assertEqual(first_ids, sorted(first_ids, reverse=True))
        self.assertEqual(len(first_ids), PRICE_ALERT_MANAGEMENT_PAGE_SIZE_V289)
        self.assertEqual(len(second.context["page_obj"].object_list), 1)
        self.assertContains(first, "Page 1 of 2")
        self.assertContains(second, "Page 2 of 2")

    def test_management_query_count_does_not_grow_per_alert(self):
        for index in range(6):
            self._alert(self._listing(f"V289 query {index}"))

        with CaptureQueriesContext(connection) as captured:
            management = build_price_alert_management_page_v289(self.buyer)
            values = [
                (entry.alert.listing.title, entry.alert.listing.category.name)
                for entry in management.entries
            ]

        self.assertEqual(len(values), 6)
        self.assertLessEqual(len(captured), 3)

    def test_template_has_accessible_list_status_and_remove_controls(self):
        alert = self._alert()
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        self.assertContains(response, '<h1>Price alerts</h1>')
        self.assertContains(response, 'aria-label="Listing price alerts"')
        self.assertContains(response, 'data-price-alert-entry-v289="true"')
        self.assertContains(
            response,
            f'aria-label="Remove price alert for {alert.listing.title}"',
        )

    def test_navigation_surfaces_management_without_exposing_event_ledger(self):
        self._alert()
        NotificationDeliveryEvent.objects.create(
            recipient=self.buyer,
            listing=self.listing,
            listing_price_alert=ListingPriceAlert.objects.get(),
            notification_type="listing_price_drop",
            event_key="a" * 64,
        )
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertNotContains(response, "a" * 64)
        self.assertNotContains(response, "attempt_count")
        self.assertContains(self.client.get(reverse("accounts:dashboard")), self.url)
        self.assertContains(
            self.client.get(reverse("accounts:notification_delivery_preferences_v288")),
            self.url,
        )

    def test_existing_listing_detail_toggle_remains_compatible(self):
        self.client.force_login(self.buyer)
        toggle = reverse(
            "listings:listing_price_alert_toggle_v285",
            kwargs={"pk": self.listing.pk},
        )
        response = self.client.post(toggle)
        self.assertRedirects(
            response,
            self.listing.get_absolute_url(),
            fetch_redirect_response=False,
        )
        self.assertTrue(ListingPriceAlert.objects.filter(user=self.buyer).exists())
