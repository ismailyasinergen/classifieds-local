import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.listing_detail_asset_contract_v325 import (
    read_listing_detail_contract_source_v325,
)
from listings.models import Listing, ListingFavorite


V321_MARKER = "MOBILE_LISTING_BUYER_ACTION_BAR_V321"


class ListingMobileBuyerActionBarV321Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_path = (
            Path(settings.BASE_DIR)
            / "listings"
            / "templates"
            / "listings"
            / "listing_detail.html"
        )

    def setUp(self):
        user_model = get_user_model()
        self.seller = user_model.objects.create_user(
            username="v321-seller",
            password="StrongPass123!",
        )
        self.buyer = user_model.objects.create_user(
            username="v321-buyer",
            password="StrongPass123!",
        )
        self.staff = user_model.objects.create_user(
            username="v321-staff",
            password="StrongPass123!",
            is_staff=True,
        )
        self.category = Category.objects.create(
            name="V321 mobile actions",
            slug="v321-mobile-actions",
        )
        self.listing = Listing.objects.create(
            title="V321 buyer action listing",
            description="Mobile buyer action bar regression fixture.",
            price=Decimal("321.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.APPROVED,
        )
        self.detail_url = reverse(
            "listings:listing_detail",
            kwargs={"pk": self.listing.pk},
        )
        self.contact_url = reverse(
            "conversations:listing_contact",
            kwargs={"pk": self.listing.pk},
        )
        self.favorite_url = reverse(
            "listings:listing_favorite_toggle",
            kwargs={"pk": self.listing.pk},
        )

    def test_anonymous_bar_uses_login_flows_and_share_fallback(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<body class="listing-detail-page-v321">',
            count=1,
        )
        self.assertContains(
            response,
            f'data-marker="{V321_MARKER}"',
            count=1,
        )
        self.assertContains(response, "Login to message")
        self.assertContains(response, "Sign in to save")
        self.assertContains(
            response,
            f"/accounts/login/?next={self.contact_url}",
        )
        self.assertContains(
            response,
            f"/accounts/login/?next={self.detail_url}",
        )
        rendered_share_buttons = re.findall(
            r"<button\b[^>]*\bdata-listing-share-v317(?:\s|=|>)",
            response.content.decode(),
        )
        self.assertEqual(len(rendered_share_buttons), 2)

    def test_authenticated_buyer_bar_preserves_post_and_csrf(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url)

        self.assertContains(
            response,
            f'data-marker="{V321_MARKER}"',
            count=1,
        )
        self.assertContains(
            response,
            f'href="{self.contact_url}"',
        )
        self.assertContains(
            response,
            f'action="{self.favorite_url}"',
            count=2,
        )
        self.assertContains(
            response,
            'class="mobile-buyer-action-form-v321"',
        )
        self.assertContains(response, "Save listing")
        self.assertContains(response, "csrfmiddlewaretoken")

        ListingFavorite.objects.create(
            user=self.buyer,
            listing=self.listing,
        )
        saved_response = self.client.get(self.detail_url)
        self.assertContains(saved_response, "Remove saved")

    def test_owner_and_staff_do_not_receive_buyer_bar(self):
        for user in (self.seller, self.staff):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.detail_url)

                self.assertEqual(response.status_code, 200)
                self.assertNotContains(
                    response,
                    f'data-marker="{V321_MARKER}"',
                )

    def test_v321_mobile_safe_area_and_print_contract_is_packaged(self):
        source = read_listing_detail_contract_source_v325(
            Path(settings.BASE_DIR),
        )

        for fragment in (
            ".mobile-buyer-action-bar-v321",
            "@media (max-width: 760px)",
            "position: fixed;",
            "env(safe-area-inset-bottom)",
            "min-height: 44px;",
            "body.listing-detail-page-v321",
            "@media print",
            "querySelectorAll(",
            '"[data-listing-share-v317]"',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_v321_adds_no_database_migration(self):
        matches = []
        for app_name in ("accounts", "listings"):
            matches.extend(
                (
                    Path(settings.BASE_DIR)
                    / app_name
                    / "migrations"
                ).glob("*v321*.py")
            )

        self.assertEqual(matches, [])
