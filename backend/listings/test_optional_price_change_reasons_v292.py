from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from categories.models import Category

from .models import Listing, ListingPriceHistory


User = get_user_model()


class OptionalPriceChangeReasonsV292Tests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="reason-owner-v292",
            password="test-pass-v292",
        )
        self.other_user = User.objects.create_user(
            username="reason-other-v292",
            password="test-pass-v292",
        )
        self.category = Category.objects.create(
            name="V292 Category",
            slug="v292-category",
        )
        self.listing = Listing.objects.create(
            owner=self.owner,
            category=self.category,
            title="V292 Listing",
            description="A listing with optional structured reasons.",
            price=Decimal("100.00"),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )
        self.url = reverse(
            "listings:listing_price_change_confirmation_v291",
            kwargs={"pk": self.listing.pk},
        )
        self.client.force_login(self.owner)

    def _review(self, *, price="80.00", reason=""):
        return self.client.post(
            self.url,
            {
                "proposed_price": price,
                "price_change_reason": reason,
            },
        )

    def _confirm(self, *, price="80.00", reason="", extra=None):
        review = self._review(price=price, reason=reason)
        self.assertEqual(review.status_code, 200)
        payload = {
            "confirmation_token": review.context["confirmation_token_v291"]
        }
        payload.update(extra or {})
        return self.client.post(self.url, payload)

    def _latest_transition(self):
        return self.listing.price_history.filter(
            previous_price__isnull=False
        ).first()

    def test_form_exposes_optional_allowlisted_reason_choices(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Reason (optional)")
        self.assertContains(response, 'name="price_change_reason"')
        for value, label in ListingPriceHistory.Reason.choices:
            self.assertContains(response, f'value="{value}"')
            self.assertContains(response, label)

    def test_blank_reason_preserves_legacy_behavior(self):
        response = self._confirm(price="90.00")
        self.assertEqual(response.status_code, 302)
        transition = self._latest_transition()
        self.assertEqual(transition.reason, "")
        self.assertEqual(transition.get_reason_display(), "No reason selected")

    def test_each_structured_reason_can_be_recorded(self):
        prices = ["95.00", "90.00", "85.00", "80.00", "75.00"]
        reasons = [
            ListingPriceHistory.Reason.MARKET_ADJUSTMENT,
            ListingPriceHistory.Reason.PROMOTION,
            ListingPriceHistory.Reason.CONDITION_UPDATE,
            ListingPriceHistory.Reason.LISTING_CORRECTION,
            ListingPriceHistory.Reason.OTHER,
        ]
        for price, reason in zip(prices, reasons, strict=True):
            self.listing.price = Decimal(price)
            self.listing.save(
                update_fields=["price"],
                price_change_reason=reason,
            )

        recorded = list(
            self.listing.price_history.filter(previous_price__isnull=False)
            .order_by("pk")
            .values_list("reason", flat=True)
        )
        self.assertEqual(recorded, reasons)

    def test_review_and_confirmation_display_and_store_selected_reason(self):
        review = self._review(
            price="75.00",
            reason=ListingPriceHistory.Reason.PROMOTION,
        )
        self.assertContains(review, "Reason")
        self.assertContains(review, "Promotion")
        self.assertEqual(self.listing.price_history.count(), 1)

        response = self.client.post(
            self.url,
            {"confirmation_token": review.context["confirmation_token_v291"]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self._latest_transition().reason,
            ListingPriceHistory.Reason.PROMOTION,
        )

    def test_reason_is_bound_to_signed_review_and_post_override_is_ignored(self):
        response = self._confirm(
            price="70.00",
            reason=ListingPriceHistory.Reason.MARKET_ADJUSTMENT,
            extra={"price_change_reason": ListingPriceHistory.Reason.OTHER},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self._latest_transition().reason,
            ListingPriceHistory.Reason.MARKET_ADJUSTMENT,
        )

    def test_invalid_form_reason_is_rejected_without_a_write(self):
        response = self._review(price="80.00", reason="private-free-text")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("100.00"))
        self.assertEqual(self.listing.price_history.count(), 1)

    def test_model_boundary_rejects_invalid_reason(self):
        self.listing.price = Decimal("80.00")
        with self.assertRaises(ValidationError):
            self.listing.save(
                update_fields=["price"],
                price_change_reason="unapproved_reason",
            )
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("100.00"))
        self.assertEqual(self.listing.price_history.count(), 1)

    def test_baseline_and_noop_save_never_gain_a_reason(self):
        baseline = self.listing.price_history.get(previous_price__isnull=True)
        self.assertEqual(baseline.reason, "")

        self.listing.save(
            update_fields=["price"],
            price_change_reason=ListingPriceHistory.Reason.PROMOTION,
        )
        self.assertEqual(self.listing.price_history.count(), 1)
        baseline.refresh_from_db()
        self.assertEqual(baseline.reason, "")

    def test_stale_confirmation_does_not_attach_reason_to_another_change(self):
        review = self._review(
            price="70.00",
            reason=ListingPriceHistory.Reason.CONDITION_UPDATE,
        )
        self.listing.price = Decimal("90.00")
        self.listing.save(update_fields=["price"])

        response = self.client.post(
            self.url,
            {"confirmation_token": review.context["confirmation_token_v291"]},
        )
        self.assertEqual(response.status_code, 409)
        transitions = self.listing.price_history.filter(previous_price__isnull=False)
        self.assertEqual(transitions.count(), 1)
        self.assertEqual(transitions.get().reason, "")

    def test_owner_dashboard_displays_reason_without_leaking_other_seller_data(self):
        self._confirm(
            price="80.00",
            reason=ListingPriceHistory.Reason.LISTING_CORRECTION,
        )
        other_listing = Listing.objects.create(
            owner=self.other_user,
            category=self.category,
            title="Private other seller price",
            description="Owner isolation.",
            price=Decimal("500.00"),
            location="Berlin",
        )
        other_listing.price = Decimal("400.00")
        other_listing.save(
            update_fields=["price"],
            price_change_reason=ListingPriceHistory.Reason.PROMOTION,
        )

        response = self.client.get(reverse("accounts:seller_pricing_dashboard_v290"))
        self.assertContains(response, "Reason: Listing correction")
        self.assertNotContains(response, other_listing.title)
        self.assertNotContains(response, "Reason: Promotion")

    def test_public_price_history_does_not_expose_reason_code_or_label(self):
        self.listing.price = Decimal("80.00")
        self.listing.save(
            update_fields=["price"],
            price_change_reason=ListingPriceHistory.Reason.PROMOTION,
        )
        self.client.logout()

        response = self.client.get(self.listing.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price history")
        self.assertNotContains(response, "Promotion")
        self.assertNotContains(response, "market_adjustment")
        self.assertNotContains(response, "price_change_reason")

    def test_existing_direct_price_changes_default_to_unspecified(self):
        self.listing.price = Decimal("88.00")
        self.listing.save(update_fields=["price"])
        self.assertEqual(self._latest_transition().reason, "")

    def test_reason_field_is_backward_compatible_and_bounded(self):
        field = ListingPriceHistory._meta.get_field("reason")
        self.assertEqual(field.default, ListingPriceHistory.Reason.UNSPECIFIED)
        self.assertTrue(field.blank)
        self.assertEqual(field.max_length, 32)
