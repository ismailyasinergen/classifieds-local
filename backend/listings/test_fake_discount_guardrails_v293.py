from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category

from .listing_price_alerts_v285 import get_listing_price_alert_candidates_v285
from .listing_price_drop_discovery_v276 import get_current_listing_price_drops_v276
from .listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
    FAKE_DISCOUNT_GUARDRAILS_V293,
)
from .saved_search_price_drop_notifications_v286 import (
    apply_saved_search_activity_window_v286,
)
from .models import Listing, ListingPriceAlert, ListingPriceHistory


User = get_user_model()


class FakeDiscountGuardrailsV293Tests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="integrity-seller-v293",
            password="test-pass-v293",
        )
        self.buyer = User.objects.create_user(
            username="integrity-buyer-v293",
            email="buyer-v293@example.test",
            password="test-pass-v293",
        )
        self.category = Category.objects.create(
            name="V293 Category",
            slug="v293-category",
        )
        self.listing = self._listing("V293 guarded listing")

    def _listing(self, title, price="100.00"):
        return Listing.objects.create(
            owner=self.seller,
            category=self.category,
            title=title,
            description="Sequence-based discount integrity fixture.",
            price=Decimal(price),
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )

    @staticmethod
    def _change(listing, price, *, reason=""):
        listing.price = Decimal(price)
        listing.save(
            update_fields=["price"],
            price_change_reason=reason,
        )
        listing.refresh_from_db()
        return listing.price_history.filter(previous_price__isnull=False).first()

    @staticmethod
    def _titles(response):
        return [listing.title for listing in response.context["listings"]]

    def test_contract_and_normal_reduction_remain_eligible(self):
        self.assertTrue(FAKE_DISCOUNT_GUARDRAILS_V293)
        transition = self._change(self.listing, "80.00")
        self.assertEqual(transition.discount_guardrail_status, "")
        self.assertIsNone(transition.discount_reference_price)
        self.assertTrue(transition.is_public_discount_eligible)

    def test_raise_then_drop_at_or_above_reference_is_restricted(self):
        increase = self._change(self.listing, "200.00")
        self.assertEqual(increase.discount_reference_price, Decimal("100.00"))

        restricted = self._change(self.listing, "150.00")
        self.assertEqual(
            restricted.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )
        self.assertEqual(restricted.discount_reference_price, Decimal("100.00"))
        self.assertFalse(restricted.is_public_discount_eligible)

        exact_reference = self._change(self.listing, "100.00")
        self.assertEqual(
            exact_reference.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )

    def test_price_below_preincrease_reference_clears_guardrail(self):
        self._change(self.listing, "200.00")
        eligible = self._change(self.listing, "99.99")
        self.assertEqual(eligible.discount_guardrail_status, "")
        self.assertIsNone(eligible.discount_reference_price)
        self.assertTrue(eligible.is_public_discount_eligible)

    def test_consecutive_increases_and_reductions_keep_earliest_reference(self):
        first_increase = self._change(self.listing, "150.00")
        second_increase = self._change(self.listing, "200.00")
        first_reduction = self._change(self.listing, "160.00")
        second_reduction = self._change(self.listing, "120.00")

        self.assertEqual(first_increase.discount_reference_price, Decimal("100.00"))
        self.assertEqual(second_increase.discount_reference_price, Decimal("100.00"))
        self.assertEqual(first_reduction.discount_reference_price, Decimal("100.00"))
        self.assertEqual(second_reduction.discount_reference_price, Decimal("100.00"))
        self.assertEqual(
            second_reduction.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )

    def test_confirmation_warns_before_write_and_persists_authoritative_guardrail(self):
        self._change(self.listing, "200.00")
        self.client.force_login(self.seller)
        url = reverse(
            "listings:listing_price_change_confirmation_v291",
            kwargs={"pk": self.listing.pk},
        )
        review = self.client.post(
            url,
            {
                "proposed_price": "150.00",
                "price_change_reason": ListingPriceHistory.Reason.PROMOTION,
            },
        )
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Public discount guardrail")
        self.assertContains(review, "falls below 100.00 TL")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("200.00"))

        confirmed = self.client.post(
            url,
            {"confirmation_token": review.context["confirmation_token_v291"]},
        )
        self.assertEqual(confirmed.status_code, 302)
        latest = self.listing.price_history.filter(previous_price__isnull=False).first()
        self.assertEqual(latest.reason, ListingPriceHistory.Reason.PROMOTION)
        self.assertEqual(
            latest.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )

    def test_cards_and_detail_hide_promotional_discount_but_keep_factual_timeline(self):
        self._change(self.listing, "200.00")
        self._change(self.listing, "150.00")

        self.assertEqual(get_current_listing_price_drops_v276([self.listing.pk]), {})
        response = self.client.get(self.listing.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-price-drop-v275="true"')
        self.assertContains(response, "Price history")
        self.assertContains(response, "Price increased")
        self.assertContains(response, "Price reduced")
        self.assertNotContains(response, "raise_then_drop")
        self.assertNotContains(response, "discount_reference_price")

    def test_main_and_category_discount_browse_exclude_guarded_reduction(self):
        self._change(self.listing, "200.00")
        self._change(self.listing, "150.00")
        clean = self._listing("V293 genuine reduction", price="200.00")
        self._change(clean, "150.00")

        for params in (
            {"price_drops": "1"},
            {"sort": "recent_price_drop"},
            {"sort": "biggest_price_drop"},
            {"min_price_drop_amount": "10"},
            {"min_price_drop_percent": "10"},
            {"price_drop_period": "30d"},
        ):
            response = self.client.get(reverse("listings:listing_list"), params)
            self.assertNotIn(self.listing.title, self._titles(response))
            self.assertIn(clean.title, self._titles(response))

        category = self.client.get(
            reverse("categories:category_detail", kwargs={"slug": self.category.slug}),
            {"price_drops": "1"},
        )
        self.assertNotIn(self.listing.title, self._titles(category))
        self.assertIn(clean.title, self._titles(category))

    def test_listing_price_alerts_suppress_guarded_event_but_keep_genuine_drop(self):
        self._change(self.listing, "200.00")
        guarded_alert = ListingPriceAlert.objects.create(
            user=self.buyer,
            listing=self.listing,
            baseline_price=self.listing.price,
        )
        self._change(self.listing, "150.00")

        genuine = self._listing("V293 genuine alert", price="200.00")
        genuine_alert = ListingPriceAlert.objects.create(
            user=self.buyer,
            listing=genuine,
            baseline_price=genuine.price,
        )
        self._change(genuine, "150.00")

        candidates = list(get_listing_price_alert_candidates_v285())
        self.assertNotIn(guarded_alert, candidates)
        self.assertIn(genuine_alert, candidates)

    def test_saved_search_price_drop_matching_suppresses_guarded_event(self):
        self._change(self.listing, "200.00")
        self._change(self.listing, "150.00")
        clean = self._listing("V293 saved-search genuine", price="200.00")
        self._change(clean, "150.00")
        request = RequestFactory().get(
            "/listings/",
            {"sort": "recent_price_drop"},
        )

        queryset, watches_price_drops = apply_saved_search_activity_window_v286(
            Listing.objects.filter(pk__in=[self.listing.pk, clean.pk]),
            request,
            checked_since=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(watches_price_drops)
        self.assertEqual(list(queryset.values_list("pk", flat=True)), [clean.pk])

    def test_owner_dashboard_explains_restriction_without_public_metadata(self):
        self._change(self.listing, "200.00")
        self._change(self.listing, "150.00")
        self.client.force_login(self.seller)

        response = self.client.get(reverse("accounts:seller_pricing_dashboard_v290"))
        self.assertContains(response, "Public discount restricted")
        self.assertContains(response, "falls below 100.00 TL")
        self.assertNotContains(response, "raise_then_drop")

    def test_card_discovery_query_count_stays_constant(self):
        guarded = self.listing
        self._change(guarded, "200.00")
        self._change(guarded, "150.00")
        genuine = self._listing("V293 query genuine", price="200.00")
        self._change(genuine, "150.00")

        with CaptureQueriesContext(connection) as captured:
            discoveries = get_current_listing_price_drops_v276(
                [guarded.pk, genuine.pk]
            )
        self.assertEqual(len(captured), 1)
        self.assertNotIn(guarded.pk, discoveries)
        self.assertIn(genuine.pk, discoveries)

    def test_additive_fields_are_backward_compatible(self):
        status_field = ListingPriceHistory._meta.get_field(
            "discount_guardrail_status"
        )
        reference_field = ListingPriceHistory._meta.get_field(
            "discount_reference_price"
        )
        self.assertEqual(status_field.default, "")
        self.assertTrue(status_field.blank)
        self.assertTrue(reference_field.null)
        baseline = self.listing.price_history.get(previous_price__isnull=True)
        self.assertEqual(baseline.discount_guardrail_status, "")
        self.assertIsNone(baseline.discount_reference_price)
