from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    SellerStore,
    UserProfile,
)
from categories.models import Category
from listings.listing_detail_asset_contract_v325 import (
    read_listing_detail_contract_source_v325,
)
from listings.models import Listing


V319_MARKER = "LISTING_LOCATION_ACTIONS_V319"


class ListingLocationActionsV319Tests(
    TestCase
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(settings.BASE_DIR)
        cls.template_path = (
            cls.base_dir
            / "listings"
            / "templates"
            / "listings"
            / "listing_detail.html"
        )
        cls.source = read_listing_detail_contract_source_v325(
            cls.base_dir,
        )

    def setUp(self):
        user_model = get_user_model()

        self.seller = user_model.objects.create_user(
            username="v319-seller",
            email="v319-seller@classifieds.local",
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=self.seller,
        )

        SellerStore.objects.get_or_create(
            owner=self.seller,
        )

        self.category = Category.objects.create(
            name="V319 Local Furniture",
            slug="v319-local-furniture",
        )

        self.listing = Listing.objects.create(
            title="V319 Location Listing",
            description=(
                "A listing used to verify map "
                "and location copy actions."
            ),
            price=Decimal("319.00"),
            location="Berlin Mitte & Kreuzberg",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.APPROVED,
        )

    def test_v319_marker_and_controls_are_packaged(
        self,
    ):
        fragments = (
            V319_MARKER,
            "data-listing-location-copy-v319",
            "data-listing-location-v319",
            "Open in map",
            "Copy location",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v319_map_link_uses_openstreetmap(
        self,
    ):
        fragments = (
            "https://www.openstreetmap.org/search?query=",
            "listing.location|urlencode",
            'target="_blank"',
            'rel="noopener noreferrer"',
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v319_copy_action_has_resilient_fallback(
        self,
    ):
        fragments = (
            "navigator.clipboard",
            "navigator.clipboard.writeText",
            "document.createElement(",
            '"textarea"',
            'document.execCommand("copy")',
            "Location copied.",
            "Location could not be copied.",
            "Location is unavailable.",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v319_controls_are_accessible(
        self,
    ):
        fragments = (
            'type="button"',
            'aria-describedby="listing-location-status-v319"',
            'role="status"',
            'aria-live="polite"',
            'aria-atomic="true"',
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v319_listing_page_renders_encoded_map_url(
        self,
    ):
        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'data-marker="LISTING_LOCATION_ACTIONS_V319"',
        )

        self.assertContains(
            response,
            (
                "https://www.openstreetmap.org/"
                "search?query="
                "Berlin%20Mitte%20%26%20Kreuzberg"
            ),
        )

        self.assertContains(
            response,
            (
                'data-listing-location-v319='
                '"Berlin Mitte &amp; Kreuzberg"'
            ),
        )

        self.assertContains(
            response,
            "Copy location",
        )

    def test_v319_adds_no_database_migration(
        self,
    ):
        matches = []

        for app_name in (
            "accounts",
            "listings",
        ):
            matches.extend(
                (
                    self.base_dir
                    / app_name
                    / "migrations"
                ).glob("*v319*.py")
            )

        self.assertEqual(
            matches,
            [],
        )
