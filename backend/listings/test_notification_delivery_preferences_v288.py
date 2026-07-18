from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import (
    Listing,
    ListingPriceAlert,
    NotificationDeliveryEvent,
    NotificationDeliveryPreference,
    SavedSearch,
)
from listings.notification_delivery_deduplication_v287 import (
    build_saved_search_event_specs_v287,
)
from listings.notification_delivery_preferences_v288 import (
    PREFERENCE_SUPPRESSION_REASON_V288,
    apply_notification_preferences_v288,
)
from listings.saved_search_notification_email_sender import (
    send_saved_search_notification_email,
)
from listings.saved_search_notifications import build_saved_search_match_preview


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="alerts@classifieds.local",
)
class NotificationDeliveryPreferencesV288Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            username="v288-buyer",
            email="v288-buyer@classifieds.local",
            password="Testpass12345",
        )
        self.other = User.objects.create_user(
            username="v288-other",
            email="v288-other@classifieds.local",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            username="v288-seller",
            email="v288-seller@classifieds.local",
            password="Testpass12345",
        )
        self.category = Category.objects.create(name="V288", slug="v288")
        self.listing = self._listing("V288 ordinary listing")
        mail.outbox = []

    def _listing(self, title, *, price="100.00", created_days_ago=0):
        listing = Listing.objects.create(
            title=title,
            description="V288 notification preference fixture.",
            price=Decimal(price),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )
        if created_days_ago:
            Listing.objects.filter(pk=listing.pk).update(
                created_at=timezone.now() - timedelta(days=created_days_ago),
            )
            listing.refresh_from_db()
        return listing

    def _reduce(self, listing, price):
        listing.price = Decimal(price)
        listing.save(update_fields=["price"])
        listing.refresh_from_db()

    def _alert(self, listing=None):
        listing = listing or self.listing
        return ListingPriceAlert.objects.create(
            user=self.buyer,
            listing=listing,
            baseline_price=listing.price,
        )

    def _saved_search(self, *, params=None, enabled=True, checked_days_ago=1):
        params = params or {"q": "V288"}
        return SavedSearch.objects.create(
            user=self.buyer,
            name="V288 saved search",
            path=reverse("listings:listing_list"),
            query_params=params,
            querystring="&".join(
                f"{key}={value}" for key, value in sorted(params.items())
            ),
            email_notifications_enabled=enabled,
            last_notification_checked_at=(
                timezone.now() - timedelta(days=checked_days_ago)
            ),
        )

    def _preference(self, **overrides):
        defaults = {
            "listing_price_alert_email_enabled": True,
            "saved_search_new_listing_email_enabled": True,
            "saved_search_price_drop_email_enabled": True,
        }
        defaults.update(overrides)
        return NotificationDeliveryPreference.objects.create(
            user=self.buyer,
            **defaults,
        )

    def test_settings_get_creates_backward_compatible_enabled_defaults(self):
        self.client.force_login(self.buyer)
        response = self.client.get(
            reverse("accounts:notification_delivery_preferences_v288")
        )

        self.assertEqual(response.status_code, 200)
        preference = NotificationDeliveryPreference.objects.get(user=self.buyer)
        self.assertTrue(preference.listing_price_alert_email_enabled)
        self.assertTrue(preference.saved_search_new_listing_email_enabled)
        self.assertTrue(preference.saved_search_price_drop_email_enabled)

    def test_missing_preference_preserves_existing_listing_alert_delivery(self):
        alert = self._alert()
        self._reduce(self.listing, "80.00")

        call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        alert.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(alert.last_notified_price, Decimal("80.00"))
        self.assertFalse(NotificationDeliveryPreference.objects.exists())

    def test_anonymous_redirect_and_post_updates_only_authenticated_user(self):
        url = reverse("accounts:notification_delivery_preferences_v288")
        self.assertRedirects(
            self.client.get(url),
            f"{reverse('accounts:login')}?next={url}",
        )
        own = self._preference()
        other = NotificationDeliveryPreference.objects.create(user=self.other)
        self.client.force_login(self.buyer)

        response = self.client.post(
            url,
            {
                "saved_search_new_listing_email_enabled": "on",
            },
        )

        self.assertRedirects(response, url)
        own.refresh_from_db()
        other.refresh_from_db()
        self.assertFalse(own.listing_price_alert_email_enabled)
        self.assertTrue(own.saved_search_new_listing_email_enabled)
        self.assertFalse(own.saved_search_price_drop_email_enabled)
        self.assertTrue(other.listing_price_alert_email_enabled)
        self.assertTrue(other.saved_search_new_listing_email_enabled)
        self.assertTrue(other.saved_search_price_drop_email_enabled)

    def test_settings_post_requires_csrf(self):
        self._preference()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)
        response = client.post(
            reverse("accounts:notification_delivery_preferences_v288"),
            {"listing_price_alert_email_enabled": "on"},
        )
        self.assertEqual(response.status_code, 403)

    def test_settings_template_is_accessible_and_linked_from_account_ui(self):
        self.client.force_login(self.buyer)
        url = reverse("accounts:notification_delivery_preferences_v288")
        response = self.client.get(url)

        self.assertContains(response, "Notification preferences")
        self.assertContains(response, "Listing price-alert emails")
        self.assertContains(response, "Saved-search new-listing emails")
        self.assertContains(response, "Saved-search price-drop emails")
        self.assertContains(response, 'aria-describedby="id_listing_price_alert_email_enabled_helptext"')
        self.assertContains(response, "Individual saved")
        self.assertContains(response, "searches must also have email notifications enabled")
        self.assertContains(self.client.get(reverse("accounts:dashboard")), url)
        self.assertContains(self.client.get(reverse("accounts:profile")), url)

    def test_listing_alert_disabled_is_terminal_without_consuming_sent_state(self):
        preference = self._preference(
            listing_price_alert_email_enabled=False,
        )
        alert = self._alert()
        self._reduce(self.listing, "80.00")
        output = StringIO()

        call_command("check_listing_price_alerts", "--send", stdout=output)
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        alert.refresh_from_db()
        event = NotificationDeliveryEvent.objects.get()
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(alert.last_notified_price)
        self.assertIsNone(alert.last_notification_sent_at)
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.SKIPPED)
        self.assertEqual(event.attempt_count, 0)
        self.assertEqual(event.last_error_category, PREFERENCE_SUPPRESSION_REASON_V288)
        self.assertEqual(NotificationDeliveryEvent.objects.count(), 1)
        self.assertIn("1 preference-suppressed", output.getvalue())
        self.assertFalse(preference.listing_price_alert_email_enabled)

    def test_reenabling_does_not_send_stale_listing_event_but_future_drop_sends(self):
        preference = self._preference(
            listing_price_alert_email_enabled=False,
        )
        self._alert()
        self._reduce(self.listing, "80.00")
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        preference.listing_price_alert_email_enabled = True
        preference.save(update_fields=["listing_price_alert_email_enabled"])
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 0)

        self._reduce(self.listing, "70.00")
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            NotificationDeliveryEvent.objects.filter(status="sent").count(),
            1,
        )

    def test_saved_search_new_listing_disabled_advances_check_without_backlog(self):
        self._preference(saved_search_new_listing_email_enabled=False)
        saved_search = self._saved_search(params={"q": "ordinary"})
        before = saved_search.last_notification_checked_at

        call_command("check_saved_search_notifications", "--send", stdout=StringIO())
        saved_search.refresh_from_db()
        call_command("check_saved_search_notifications", "--send", stdout=StringIO())

        event = NotificationDeliveryEvent.objects.get()
        self.assertEqual(len(mail.outbox), 0)
        self.assertGreater(saved_search.last_notification_checked_at, before)
        self.assertIsNone(saved_search.last_notification_sent_at)
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.SKIPPED)
        self.assertEqual(event.attempt_count, 0)
        self.assertEqual(NotificationDeliveryEvent.objects.count(), 1)

    def test_saved_search_price_drop_preference_is_independent(self):
        self._preference(saved_search_price_drop_email_enabled=False)
        ordinary = self._saved_search(params={"q": "ordinary"})
        price_listing = self._listing(
            "V288 price candidate",
            created_days_ago=10,
        )
        price_search = self._saved_search(params={"price_drops": "1"})
        self._reduce(price_listing, "80.00")

        call_command("check_saved_search_notifications", "--send", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            set(NotificationDeliveryEvent.objects.values_list("status", flat=True)),
            {NotificationDeliveryEvent.Status.SENT, NotificationDeliveryEvent.Status.SKIPPED},
        )
        ordinary.refresh_from_db()
        price_search.refresh_from_db()
        self.assertIsNotNone(ordinary.last_notification_sent_at)
        self.assertIsNone(price_search.last_notification_sent_at)

    def test_per_saved_search_disable_and_global_preferences_use_and_semantics(self):
        self._preference()
        saved_search = self._saved_search(enabled=False)

        call_command("check_saved_search_notifications", "--send", stdout=StringIO())

        saved_search.refresh_from_db()
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(NotificationDeliveryEvent.objects.exists())
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_mature_sender_suppresses_disabled_type_before_email_attempt(self):
        self._preference(saved_search_new_listing_email_enabled=False)
        saved_search = self._saved_search(params={"q": "ordinary"})
        preview = build_saved_search_match_preview(saved_search)

        result = send_saved_search_notification_email(
            saved_search,
            match_count=preview.match_count,
            matching_listings=preview.listings,
            execute_send=True,
        )

        self.assertEqual(result["delivered_count"], 0)
        self.assertEqual(result["preference_suppressed"], 1)
        self.assertEqual(len(mail.outbox), 0)
        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_sent_at)
        audit_event = saved_search.notification_audit_events.get()
        self.assertEqual(audit_event.event_type, "skipped_notifications_disabled")
        self.assertEqual(audit_event.reason_code, "global_preference_disabled")

    def test_disabling_after_failure_terminally_suppresses_retry(self):
        preference = self._preference()
        self._alert()
        self._reduce(self.listing, "80.00")
        with patch(
            "listings.management.commands.check_listing_price_alerts.send_listing_price_alert_v285",
            return_value=0,
        ):
            call_command("check_listing_price_alerts", "--send", stdout=StringIO())
        event = NotificationDeliveryEvent.objects.get()
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.FAILED)
        self.assertEqual(event.attempt_count, 1)

        preference.listing_price_alert_email_enabled = False
        preference.save(update_fields=["listing_price_alert_email_enabled"])
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        event.refresh_from_db()
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.SKIPPED)
        self.assertEqual(event.attempt_count, 1)
        self.assertEqual(event.last_error_category, PREFERENCE_SUPPRESSION_REASON_V288)

    def test_preference_partition_query_count_is_constant(self):
        self._preference(saved_search_new_listing_email_enabled=False)
        for index in range(4):
            self._listing(f"V288 batch {index}")
        preview = build_saved_search_match_preview(self._saved_search())
        specs = build_saved_search_event_specs_v287(preview)

        with CaptureQueriesContext(connection) as captured:
            decision = apply_notification_preferences_v288(specs)

        self.assertEqual(len(decision.suppressed_specs), 5)
        self.assertLessEqual(len(captured), 4)

    def test_admin_is_staff_only_and_preference_rows_are_read_only(self):
        url = reverse("admin:listings_notificationdeliverypreference_changelist")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(url).status_code, 302)
        staff = get_user_model().objects.create_superuser(
            username="v288-staff",
            email="v288-staff@classifieds.local",
            password="Testpass12345",
        )
        self.client.force_login(staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        model_admin = __import__("listings.admin", fromlist=["admin"]).admin.site._registry[
            NotificationDeliveryPreference
        ]
        self.assertFalse(model_admin.has_add_permission(response.wsgi_request))
        self.assertFalse(model_admin.has_change_permission(response.wsgi_request))
        self.assertFalse(model_admin.has_delete_permission(response.wsgi_request))

    def test_command_output_reports_suppression_without_recipient_address(self):
        self._preference(saved_search_new_listing_email_enabled=False)
        saved_search = self._saved_search(params={"q": "ordinary"})
        output = StringIO()

        call_command(
            "check_saved_search_notifications",
            "--send",
            "--saved-search-id",
            str(saved_search.pk),
            stdout=output,
        )

        self.assertIn("preference-suppressed", output.getvalue())
        self.assertNotIn(self.buyer.email, output.getvalue())

    def test_migration_is_additive_after_v287_and_defaults_are_enabled(self):
        migration = import_module(
            "listings.migrations.0021_notification_delivery_preference_v288"
        ).Migration
        self.assertIn(
            ("listings", "0020_notification_delivery_event_v287"),
            migration.dependencies,
        )
        operation = migration.operations[0]
        fields = dict(operation.fields)
        self.assertTrue(fields["listing_price_alert_email_enabled"].default)
        self.assertTrue(fields["saved_search_new_listing_email_enabled"].default)
        self.assertTrue(fields["saved_search_price_drop_email_enabled"].default)
