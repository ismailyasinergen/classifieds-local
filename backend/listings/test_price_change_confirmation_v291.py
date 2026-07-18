from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from categories.models import Category

from .listing_price_change_confirmation_v291 import (
    PRICE_CHANGE_TOKEN_MAX_AGE_SECONDS_V291,
)
from .models import Listing


User = get_user_model()


class SellerPriceChangeConfirmationV291Tests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="price-owner-v291",
            password="test-pass-v291",
        )
        self.other_user = User.objects.create_user(
            username="other-owner-v291",
            password="test-pass-v291",
        )
        self.category = Category.objects.create(
            name="V291 Category",
            slug="v291-category",
        )
        self.listing = Listing.objects.create(
            owner=self.owner,
            category=self.category,
            title="V291 Listing",
            description="A listing with confirmed price changes.",
            price=Decimal("100.00"),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )
        self.url = reverse(
            "listings:listing_price_change_confirmation_v291",
            kwargs={"pk": self.listing.pk},
        )

    def _login(self):
        self.client.force_login(self.owner)

    def _proposal(self, price="75.00"):
        response = self.client.post(self.url, {"proposed_price": price})
        self.assertEqual(response.status_code, 200)
        return response

    def _token(self, price="75.00"):
        return self._proposal(price).context["confirmation_token_v291"]

    def test_login_and_owner_scope_are_preserved(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_displays_accessible_current_price_form(self):
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change listing price")
        self.assertContains(response, "Current price: <strong>100.00 TL</strong>", html=True)
        self.assertContains(response, 'label for="id_proposed_price"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_proposal_is_read_only_and_shows_reduction_summary(self):
        self._login()
        response = self._proposal("66.67")

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("100.00"))
        self.assertEqual(self.listing.price_history.count(), 1)
        self.assertContains(response, "Confirm price change")
        self.assertContains(response, "Price reduced")
        self.assertContains(response, "33.33 TL")
        self.assertContains(response, "33.33%")

    def test_increase_and_zero_base_percentage_are_safe(self):
        self._login()
        response = self._proposal("125.00")
        self.assertContains(response, "Price increased")
        self.assertContains(response, "25%")

        zero_listing = Listing.objects.create(
            owner=self.owner,
            category=self.category,
            title="Free v291 listing",
            description="Zero base guard.",
            price=Decimal("0.00"),
            location="Berlin",
        )
        response = self.client.post(
            reverse(
                "listings:listing_price_change_confirmation_v291",
                kwargs={"pk": zero_listing.pk},
            ),
            {"proposed_price": "5.00"},
        )
        self.assertContains(response, "Percentage unavailable")

    def test_invalid_and_same_price_do_not_create_history(self):
        self._login()
        response = self.client.post(self.url, {"proposed_price": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a number")

        response = self.client.post(self.url, {"proposed_price": "-1.00"})
        self.assertContains(response, "Ensure this value is greater than or equal to 0.00")

        response = self.client.post(self.url, {"proposed_price": "100.00"})
        self.assertRedirects(
            response,
            self.url,
            fetch_redirect_response=False,
        )
        self.assertEqual(self.listing.price_history.count(), 1)

    def test_confirmation_records_exactly_one_transition_and_pending_status(self):
        self._login()
        token = self._token("75.50")
        response = self.client.post(self.url, {"confirmation_token": token})
        self.assertRedirects(
            response,
            reverse("accounts:seller_pricing_dashboard_v290"),
            fetch_redirect_response=False,
        )

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("75.50"))
        self.assertEqual(self.listing.status, Listing.Status.PENDING)
        transitions = self.listing.price_history.filter(previous_price__isnull=False)
        self.assertEqual(transitions.count(), 1)
        transition = transitions.get()
        self.assertEqual(transition.previous_price, Decimal("100.00"))
        self.assertEqual(transition.new_price, Decimal("75.50"))

    def test_repeated_confirmation_is_stale_and_does_not_duplicate_transition(self):
        self._login()
        token = self._token("80.00")
        first = self.client.post(self.url, {"confirmation_token": token})
        self.assertEqual(first.status_code, 302)
        second = self.client.post(self.url, {"confirmation_token": token})
        self.assertEqual(second.status_code, 409)
        self.assertContains(
            second,
            "The listing price changed after you reviewed it",
            status_code=409,
        )
        self.assertEqual(
            self.listing.price_history.filter(previous_price__isnull=False).count(),
            1,
        )

    def test_concurrent_change_invalidates_reviewed_price(self):
        self._login()
        token = self._token("70.00")
        self.listing.price = Decimal("90.00")
        self.listing.save(update_fields=["price"])

        response = self.client.post(self.url, {"confirmation_token": token})
        self.assertEqual(response.status_code, 409)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("90.00"))
        self.assertEqual(
            self.listing.price_history.filter(previous_price__isnull=False).count(),
            1,
        )

    def test_tampered_expired_and_mismatched_tokens_are_rejected(self):
        self._login()
        token = self._token("85.00")
        tampered = f"{token[:-1]}{'a' if token[-1] != 'a' else 'b'}"
        response = self.client.post(self.url, {"confirmation_token": tampered})
        self.assertEqual(response.status_code, 400)

        with patch(
            "listings.listing_price_change_confirmation_v291._load_confirmation_token_v291",
            side_effect=signing.SignatureExpired("expired"),
        ):
            response = self.client.post(self.url, {"confirmation_token": token})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PRICE_CHANGE_TOKEN_MAX_AGE_SECONDS_V291, 900)

        self.client.force_login(self.other_user)
        other_listing = Listing.objects.create(
            owner=self.other_user,
            category=self.category,
            title="Other v291 listing",
            description="Owner token scope.",
            price=Decimal("100.00"),
            location="Berlin",
        )
        other_url = reverse(
            "listings:listing_price_change_confirmation_v291",
            kwargs={"pk": other_listing.pk},
        )
        response = self.client.post(other_url, {"confirmation_token": token})
        self.assertEqual(response.status_code, 400)

    def test_suspended_seller_cannot_propose_or_confirm(self):
        self._login()
        token = self._token("75.00")
        profile, _created = UserProfile.objects.get_or_create(user=self.owner)
        profile.seller_suspended_until = timezone.now() + timedelta(days=1)
        profile.save(update_fields=["seller_suspended_until"])

        get_response = self.client.get(self.url)
        post_response = self.client.post(self.url, {"confirmation_token": token})
        self.assertEqual(get_response.status_code, 302)
        self.assertEqual(post_response.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("100.00"))

    def test_csrf_is_required_for_price_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(self.url, {"proposed_price": "75.00"})
        self.assertEqual(response.status_code, 403)

    def test_dashboard_and_general_edit_point_to_confirmed_flow(self):
        self._login()
        dashboard = self.client.get(reverse("accounts:seller_pricing_dashboard_v290"))
        self.assertContains(dashboard, self.url)
        self.assertContains(dashboard, "Change price")

        edit_url = reverse("listings:listing_update", kwargs={"pk": self.listing.pk})
        edit = self.client.get(edit_url)
        self.assertContains(edit, 'name="price"', html=False)
        self.assertContains(edit, "disabled")
        self.assertContains(edit, self.url)

    def test_general_edit_preserves_price_while_saving_other_fields(self):
        self._login()
        response = self.client.post(
            reverse("listings:listing_update", kwargs={"pk": self.listing.pk}),
            {
                "title": "Updated title v291",
                "description": self.listing.description,
                "price": "1.00",
                "category": self.category.pk,
                "location": self.listing.location,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Updated title v291")
        self.assertEqual(self.listing.price, Decimal("100.00"))
        self.assertEqual(self.listing.price_history.count(), 1)

    def test_confirmation_view_uses_bounded_queries(self):
        self._login()
        with self.assertNumQueries(13):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
