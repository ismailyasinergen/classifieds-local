from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category

from .listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
)
from .models import Listing
from .pricing_integrity_moderation_queue_v294 import (
    PRICING_INTEGRITY_MODERATION_QUEUE_V294,
    PRICING_INTEGRITY_QUEUE_PAGE_SIZE_V294,
    build_pricing_integrity_queue_queryset_v294,
    paginate_pricing_integrity_queue_v294,
    parse_pricing_integrity_queue_filters_v294,
)


User = get_user_model()


class PricingIntegrityModerationQueueV294Tests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="pricing-staff-v294",
            email="pricing-staff-v294@example.test",
            password="test-pass-v294",
            is_staff=True,
        )
        self.seller = User.objects.create_user(
            username="pricing-seller-v294",
            email="private-seller-v294@example.test",
            password="test-pass-v294",
        )
        self.other_user = User.objects.create_user(
            username="ordinary-user-v294",
            password="test-pass-v294",
        )
        self.category = Category.objects.create(
            name="Pricing integrity v294",
            slug="pricing-integrity-v294",
        )
        self.url = reverse("listings:pricing_integrity_moderation_queue_v294")

    def _listing(self, title, *, status=Listing.Status.APPROVED):
        return Listing.objects.create(
            owner=self.seller,
            category=self.category,
            title=title,
            description="Pricing-integrity moderation fixture.",
            price=Decimal("100.00"),
            location="Berlin",
            status=status,
            expires_at=timezone.now() + timedelta(days=30),
        )

    @staticmethod
    def _change(listing, price):
        listing.price = Decimal(price)
        listing.save(update_fields=["price"])
        listing.refresh_from_db()
        return listing.price_history.filter(previous_price__isnull=False).first()

    def _guarded(self, title, *, status=Listing.Status.APPROVED):
        listing = self._listing(title, status=status)
        self._change(listing, "200.00")
        event = self._change(listing, "150.00")
        self.assertEqual(
            event.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )
        return listing, event

    def test_queue_requires_staff_and_is_get_only(self):
        self.assertTrue(PRICING_INTEGRITY_MODERATION_QUEUE_V294)
        anonymous = self.client.get(self.url)
        self.assertEqual(anonymous.status_code, 302)

        self.client.force_login(self.other_user)
        forbidden = self.client.get(self.url)
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_queue_displays_flagged_evidence_with_semantic_private_staff_markup(self):
        listing, _event = self._guarded("Flagged pricing evidence")
        clean = self._listing("Genuine pricing change")
        self._change(clean, "80.00")
        self.client.force_login(self.staff)

        response = self.client.get(self.url)

        self.assertContains(response, "Pricing integrity")
        self.assertContains(response, listing.title)
        self.assertNotContains(response, clean.title)
        self.assertContains(response, "Restricted after a recent price increase")
        self.assertContains(response, "Current restriction")
        self.assertContains(response, "100.00 TL")
        self.assertContains(response, "<table", html=False)
        self.assertContains(response, "<caption", html=False)
        self.assertContains(response, "<time datetime=", html=False)
        self.assertNotContains(response, self.seller.email)
        self.assertNotContains(response, self.staff.email)
        self.assertNotContains(response, "raise_then_drop")
        self.assertNotContains(response, "discount_guardrail_status")
        self.assertNotContains(response, "price_change_reason")

    def test_current_and_historical_filters_use_latest_transition_and_current_price(self):
        current_listing, current_event = self._guarded("Current restriction v294")
        historical_listing, historical_event = self._guarded(
            "Historical restriction v294"
        )
        self._change(historical_listing, "90.00")
        self.client.force_login(self.staff)

        current_response = self.client.get(self.url, {"state": "current"})
        current_ids = [event.pk for event in current_response.context["events"]]
        self.assertIn(current_event.pk, current_ids)
        self.assertNotIn(historical_event.pk, current_ids)

        historical_response = self.client.get(
            self.url,
            {"state": "historical"},
        )
        historical_ids = [
            event.pk for event in historical_response.context["events"]
        ]
        self.assertIn(historical_event.pk, historical_ids)
        self.assertNotIn(current_event.pk, historical_ids)
        self.assertEqual(current_listing.price, Decimal("150.00"))

    def test_search_and_listing_status_filters_are_safe_and_combined(self):
        approved, _ = self._guarded("Needle approved v294")
        rejected, _ = self._guarded(
            "Needle rejected v294",
            status=Listing.Status.REJECTED,
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            self.url,
            {"q": "needle", "listing_status": Listing.Status.REJECTED},
        )
        listing_ids = [event.listing_id for event in response.context["events"]]
        self.assertEqual(listing_ids, [rejected.pk])
        self.assertNotIn(approved.pk, listing_ids)

        seller_search = self.client.get(self.url, {"q": self.seller.username})
        self.assertEqual(seller_search.context["page_obj"].paginator.count, 2)

    def test_invalid_filters_are_ignored_and_search_is_bounded(self):
        listing, _ = self._guarded("Invalid filter safety v294")
        filters = parse_pricing_integrity_queue_filters_v294(
            {
                "q": "x" * 500,
                "guardrail": "unknown",
                "listing_status": "unknown",
                "state": "unknown",
            }
        )
        self.assertEqual(len(filters.query), 100)
        self.assertEqual(filters.guardrail_status, "")
        self.assertEqual(filters.listing_status, "")
        self.assertEqual(filters.state, "")

        self.client.force_login(self.staff)
        response = self.client.get(
            self.url,
            {
                "guardrail": "unknown",
                "listing_status": "unknown",
                "state": "unknown",
            },
        )
        self.assertContains(response, listing.title)

    def test_deterministic_order_uses_changed_time_then_primary_key(self):
        _first_listing, first = self._guarded("First tied restriction")
        _second_listing, second = self._guarded("Second tied restriction")
        tied_at = timezone.now() - timedelta(hours=1)
        type(first).objects.filter(pk__in=[first.pk, second.pk]).update(
            changed_at=tied_at
        )

        filters = parse_pricing_integrity_queue_filters_v294({})
        ids = list(
            build_pricing_integrity_queue_queryset_v294(filters)
            .values_list("pk", flat=True)
        )
        self.assertEqual(ids, sorted([first.pk, second.pk], reverse=True))

    def test_pagination_is_bounded_and_preserves_filters(self):
        for index in range(PRICING_INTEGRITY_QUEUE_PAGE_SIZE_V294 + 1):
            self._guarded(f"Paged restriction {index:02d}")
        self.client.force_login(self.staff)

        response = self.client.get(
            self.url,
            {"state": "current", "q": "Paged", "page": 1},
        )
        self.assertEqual(len(response.context["events"]), PRICING_INTEGRITY_QUEUE_PAGE_SIZE_V294)
        self.assertContains(response, "state=current")
        self.assertContains(response, "q=Paged")
        self.assertContains(response, "page=2")

    def test_queryset_and_pagination_have_constant_query_count(self):
        self._guarded("Query one")
        filters = parse_pricing_integrity_queue_filters_v294({})

        with CaptureQueriesContext(connection) as one_capture:
            page = paginate_pricing_integrity_queue_v294(
                build_pricing_integrity_queue_queryset_v294(filters),
                1,
            )
            for event in page.object_list:
                str(event.listing.owner.username)
                str(event.listing.category.name)

        for index in range(5):
            self._guarded(f"Query extra {index}")

        with CaptureQueriesContext(connection) as many_capture:
            page = paginate_pricing_integrity_queue_v294(
                build_pricing_integrity_queue_queryset_v294(filters),
                1,
            )
            for event in page.object_list:
                str(event.listing.owner.username)
                str(event.listing.category.name)

        self.assertEqual(len(one_capture), 2)
        self.assertEqual(len(many_capture), 2)

    def test_staff_navigation_surfaces_queue_without_public_link(self):
        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("listings:listing_list"))
        self.assertContains(staff_response, self.url)
        self.assertContains(staff_response, "Pricing Integrity")

        self.client.logout()
        public_response = self.client.get(reverse("listings:listing_list"))
        self.assertNotContains(public_response, self.url)

    def test_queue_does_not_mutate_listing_or_price_history(self):
        listing, event = self._guarded("Read-only restriction v294")
        before_price = listing.price
        before_status = listing.status
        before_count = listing.price_history.count()
        self.client.force_login(self.staff)

        self.client.get(self.url, {"state": "current"})
        listing.refresh_from_db()
        event.refresh_from_db()

        self.assertEqual(listing.price, before_price)
        self.assertEqual(listing.status, before_status)
        self.assertEqual(listing.price_history.count(), before_count)
        self.assertEqual(
            event.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )

    def test_paginate_pricing_integrity_queue_v294_handles_invalid_pages(self):
        mock_queryset = list(range(100))

        valid_page = paginate_pricing_integrity_queue_v294(mock_queryset, 2)
        self.assertEqual(valid_page.number, 2)

        invalid_page = paginate_pricing_integrity_queue_v294(mock_queryset, "not-an-integer")
        self.assertEqual(invalid_page.number, 1)

        empty_page = paginate_pricing_integrity_queue_v294(mock_queryset, 9999)
        self.assertEqual(empty_page.number, 2)

    def test_v294_requires_no_schema_migration(self):
        migration_dir = Path(__file__).resolve().parent / "migrations"
        self.assertEqual(list(migration_dir.glob("*v294*.py")), [])
