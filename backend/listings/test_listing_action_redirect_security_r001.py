from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import Listing, ListingFavorite


class ListingActionRedirectSecurityR001Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="r001-seller",
            password="Testpass12345",
        )
        self.buyer = User.objects.create_user(
            username="r001-buyer",
            password="Testpass12345",
        )
        self.staff = User.objects.create_user(
            username="r001-staff",
            password="Testpass12345",
            is_staff=True,
        )
        self.category = Category.objects.create(
            name="R001 category",
            slug="r001-category",
        )
        self.listing = Listing.objects.create(
            title="R001 redirect listing",
            description="Redirect security regression fixture.",
            price=Decimal("100.00"),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
        )
        self.url = reverse(
            "listings:listing_favorite_toggle",
            kwargs={"pk": self.listing.pk},
        )
        self.client.force_login(self.buyer)

    def test_external_next_target_falls_back_to_listing_detail(self):
        response = self.client.post(
            self.url,
            {"next": "https://attacker.example/phishing"},
        )

        self.assertRedirects(
            response,
            self.listing.get_absolute_url(),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            ListingFavorite.objects.filter(
                user=self.buyer,
                listing=self.listing,
            ).exists()
        )

    def test_same_origin_relative_next_target_is_preserved(self):
        response = self.client.post(
            self.url,
            {"next": "/listings/?q=trusted"},
        )

        self.assertRedirects(
            response,
            "/listings/?q=trusted",
            fetch_redirect_response=False,
        )

    def test_owner_external_next_target_also_falls_back(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            self.url,
            {"next": "//attacker.example/phishing"},
        )

        self.assertRedirects(
            response,
            self.listing.get_absolute_url(),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            ListingFavorite.objects.filter(
                user=self.seller,
                listing=self.listing,
            ).exists()
        )

    def test_staff_listing_actions_reject_external_next_targets(self):
        self.client.force_login(self.staff)

        action_payloads = (
            (
                "listings:listing_feature_toggle",
                {},
            ),
            (
                "listings:listing_feature_priority_update",
                {"featured_priority": "5"},
            ),
            (
                "listings:listing_feature_days_update",
                {"featured_days": "7"},
            ),
        )

        for url_name, payload in action_payloads:
            with self.subTest(url_name=url_name):
                response = self.client.post(
                    reverse(
                        url_name,
                        kwargs={"pk": self.listing.pk},
                    ),
                    {
                        **payload,
                        "next": "https://attacker.example/phishing",
                    },
                )

                self.assertRedirects(
                    response,
                    self.listing.get_absolute_url(),
                    fetch_redirect_response=False,
                )
