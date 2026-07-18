from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.seller_pricing_dashboard_v290 import (
    SELLER_PRICING_PAGE_SIZE_V290,
    build_seller_pricing_dashboard_v290,
)
from categories.models import Category
from listings.models import Listing, ListingPriceHistory


class SellerPricingDashboardV290Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="v290-seller",
            email="v290-seller@classifieds.local",
            password="Testpass12345",
        )
        self.other = User.objects.create_user(
            username="v290-other",
            email="v290-other@classifieds.local",
            password="Testpass12345",
        )
        self.category = Category.objects.create(name="V290", slug="v290")
        self.url = reverse("accounts:seller_pricing_dashboard_v290")

    def _listing(
        self,
        title,
        *,
        owner=None,
        price="100.00",
        status=Listing.Status.APPROVED,
    ):
        return Listing.objects.create(
            title=title,
            description="V290 seller pricing fixture.",
            price=Decimal(price),
            category=self.category,
            owner=owner or self.seller,
            location="Berlin",
            status=status,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def _change_price(self, listing, price):
        listing.price = Decimal(price)
        listing.save(update_fields=["price"])
        return ListingPriceHistory.objects.filter(
            listing=listing,
            previous_price__isnull=False,
        ).latest("changed_at")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={self.url}",
        )

    def test_dashboard_is_owner_scoped_and_shows_owned_nonpublic_listing(self):
        own = self._listing("Owned pending price", status=Listing.Status.PENDING)
        other = self._listing("Other seller secret", owner=self.other, price="987.65")
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, own.title)
        self.assertContains(response, "Pending approval")
        self.assertContains(
            response,
            reverse(
                "listings:listing_price_change_confirmation_v291",
                args=[own.pk],
            ),
        )
        self.assertNotContains(response, other.title)
        self.assertNotContains(response, "987.65 TL")

    def test_summary_counts_owned_listing_statuses(self):
        self._listing("Approved")
        self._listing("Pending", status=Listing.Status.PENDING)
        self._listing("Archived", status=Listing.Status.ARCHIVED)
        self._listing("Other", owner=self.other)
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertEqual(
            response.context["pricing_summary_v290"],
            {"total": 3, "approved": 1, "pending": 1, "archived": 1},
        )

    def test_reduction_displays_prices_amount_percentage_and_time(self):
        listing = self._listing("Reduced", price="120.00")
        self._change_price(listing, "90.00")
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "Price reduced")
        self.assertContains(response, "120.00 TL → 90.00 TL")
        self.assertContains(response, "Change: 30.00 TL (25%)")
        self.assertContains(response, "Matches latest recorded change")
        self.assertContains(response, "<time")
        self.assertContains(response, 'datetime="')

    def test_increase_displays_nonnegative_amount_and_decimal_percentage(self):
        listing = self._listing("Increased", price="80.00")
        self._change_price(listing, "90.00")
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "Price increased")
        self.assertContains(response, "Change: 10.00 TL (12.5%)")

    def test_zero_previous_price_uses_safe_percentage_fallback(self):
        listing = self._listing("Zero base", price="0.00")
        self._change_price(listing, "10.00")
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "Price increased")
        self.assertContains(response, "Percentage unavailable")
        self.assertNotContains(response, "Infinity")

    def test_baseline_only_listing_has_initial_price_and_no_change(self):
        self._listing("Baseline only", price="55.50")
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "55.50 TL", count=2)
        self.assertContains(response, "No price changes")
        self.assertContains(response, "Never")

    def test_latest_real_transition_ignores_equal_price_noop(self):
        listing = self._listing("No-op ignored", price="100.00")
        real = self._change_price(listing, "80.00")
        ListingPriceHistory.objects.create(
            listing=listing,
            previous_price=Decimal("80.00"),
            new_price=Decimal("80.00"),
            changed_at=real.changed_at + timedelta(minutes=1),
        )
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "100.00 TL → 80.00 TL")
        self.assertContains(response, "Price reduced")

    def test_stale_latest_transition_is_not_marked_as_current(self):
        listing = self._listing("Stale record", price="100.00")
        self._change_price(listing, "80.00")
        Listing.objects.filter(pk=listing.pk).update(price=Decimal("70.00"))
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "70.00 TL")
        self.assertContains(response, "100.00 TL → 80.00 TL")
        self.assertNotContains(response, "Matches latest recorded change")

    def test_recent_change_order_is_deterministic_and_baselines_are_last(self):
        older = self._listing("Older change")
        newer = self._listing("Newer tie")
        newest_pk = self._listing("Newest tie")
        baseline = self._listing("No transition")
        older_transition = self._change_price(older, "90.00")
        newer_transition = self._change_price(newer, "90.00")
        newest_transition = self._change_price(newest_pk, "90.00")
        shared = timezone.now() - timedelta(hours=1)
        ListingPriceHistory.objects.filter(
            pk__in=[newer_transition.pk, newest_transition.pk],
        ).update(changed_at=shared)
        ListingPriceHistory.objects.filter(pk=older_transition.pk).update(
            changed_at=shared - timedelta(hours=1),
        )

        dashboard = build_seller_pricing_dashboard_v290(self.seller)
        ids = [entry.listing.pk for entry in dashboard.entries]

        self.assertEqual(ids[:3], [newest_pk.pk, newer.pk, older.pk])
        self.assertEqual(ids[-1], baseline.pk)

    def test_status_filter_is_allowlisted_and_invalid_value_is_ignored(self):
        approved = self._listing("Approved filtered")
        pending = self._listing("Pending filtered", status=Listing.Status.PENDING)
        self.client.force_login(self.seller)

        filtered = self.client.get(self.url, {"status": "pending"})
        invalid = self.client.get(self.url, {"status": "not-a-status"})

        self.assertContains(filtered, pending.title)
        self.assertNotContains(filtered, approved.title)
        self.assertEqual(filtered.context["status_filter_v290"], "pending")
        self.assertContains(invalid, approved.title)
        self.assertContains(invalid, pending.title)
        self.assertEqual(invalid.context["status_filter_v290"], "")

    def test_supported_price_and_newest_sorts_keep_stable_ties(self):
        low_old = self._listing("Low old", price="50.00")
        low_new = self._listing("Low new", price="50.00")
        high = self._listing("High", price="100.00")
        shared = timezone.now() - timedelta(hours=1)
        Listing.objects.filter(pk__in=[low_old.pk, low_new.pk]).update(created_at=shared)

        low_ids = [
            entry.listing.pk
            for entry in build_seller_pricing_dashboard_v290(
                self.seller,
                sort="price_low",
            ).entries
        ]
        high_ids = [
            entry.listing.pk
            for entry in build_seller_pricing_dashboard_v290(
                self.seller,
                sort="price_high",
            ).entries
        ]
        newest_ids = [
            entry.listing.pk
            for entry in build_seller_pricing_dashboard_v290(
                self.seller,
                sort="newest",
            ).entries
        ]

        self.assertEqual(low_ids[:2], [low_old.pk, low_new.pk])
        self.assertEqual(high_ids[0], high.pk)
        self.assertEqual(newest_ids[:2], [high.pk, low_new.pk])

    def test_invalid_sort_uses_safe_recent_change_fallback(self):
        listing = self._listing("Changed first")
        baseline = self._listing("Unchanged last")
        self._change_price(listing, "90.00")

        dashboard = build_seller_pricing_dashboard_v290(
            self.seller,
            sort="DROP TABLE",
        )

        self.assertEqual(dashboard.sort_value, "recent_change")
        self.assertEqual(dashboard.entries[0].listing, listing)
        self.assertEqual(dashboard.entries[-1].listing, baseline)

    def test_pagination_is_bounded_and_preserves_canonical_filters(self):
        for index in range(SELLER_PRICING_PAGE_SIZE_V290 + 1):
            self._listing(f"Paged {index:02d}", status=Listing.Status.PENDING)
        self.client.force_login(self.seller)

        first = self.client.get(
            self.url,
            {"status": "pending", "sort": "price_high"},
        )
        second = self.client.get(
            self.url,
            {"status": "pending", "sort": "price_high", "page": 2},
        )

        self.assertEqual(len(first.context["pricing_entries_v290"]), 20)
        self.assertEqual(len(second.context["pricing_entries_v290"]), 1)
        self.assertContains(first, "status=pending&amp;sort=price_high&amp;page=2")
        self.assertContains(first, "Page 1 of 2")

    def test_query_count_is_stable_and_has_no_per_listing_history_queries(self):
        for index in range(8):
            listing = self._listing(f"Query {index}")
            self._change_price(listing, str(90 - index))

        with CaptureQueriesContext(connection) as captured:
            dashboard = build_seller_pricing_dashboard_v290(self.seller)
            rendered_values = [
                (entry.listing.title, entry.listing.category.name, entry.absolute_change)
                for entry in dashboard.entries
            ]

        self.assertEqual(len(rendered_values), 8)
        self.assertLessEqual(len(captured), 3)

    def test_template_navigation_accessibility_and_privacy_contract(self):
        self._listing("Accessible pricing")
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "<h1>Seller pricing</h1>")
        self.assertContains(response, 'aria-label="Seller pricing filters"')
        self.assertContains(response, "<caption>Pricing history summary for your listings</caption>")
        self.assertContains(response, '<th scope="col">')
        self.assertContains(response, '<th scope="row">')
        self.assertNotContains(response, "NotificationDeliveryEvent")
        self.assertNotContains(response, "event_key")
        self.assertNotContains(response, "price_history_id")
        self.assertContains(self.client.get(reverse("accounts:dashboard")), self.url)

    def test_empty_state_is_actionable(self):
        self.client.force_login(self.seller)
        response = self.client.get(self.url)
        self.assertContains(response, "No listings found")
        self.assertContains(response, "Post listing")
        self.assertContains(response, reverse("listings:listing_create"))
