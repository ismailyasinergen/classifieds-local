from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryPolishTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Directory Polish Furniture",
            slug="directory-polish-furniture-v115",
        )
        self.directory_url = reverse("accounts:seller_store_directory")

    def create_store_with_listings(
        self,
        username,
        store_name,
        location="Berlin",
        listing_count=1,
        verified=False,
    ):
        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            email=f"{username}@classifieds.local",
            password="StrongPass123!",
        )
        user.profile.location = location
        user.profile.verification_status = (
            UserProfile.VerificationStatus.APPROVED
            if verified
            else UserProfile.VerificationStatus.NOT_REQUESTED
        )
        user.profile.save(update_fields=["location", "verification_status"])

        store = SellerStore.objects.create(
            owner=user,
            name=store_name,
            headline=f"{store_name} polished storefront headline.",
            description=f"{store_name} polished storefront description.",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} directory polish listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=location,
                status=Listing.Status.APPROVED,
            )

        return user, store

    def test_directory_polish_layout_markers_render(self):
        self.create_store_with_listings(
            "directory_polish_ui_v115",
            "Directory Polish UI Store",
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-directory-shell-v115")
        self.assertContains(response, "seller-store-directory-discovery-panel-v115")
        self.assertContains(response, "seller-store-directory-filters-v115")
        self.assertContains(response, "seller-store-directory-results-summary-v115")
        self.assertContains(response, "Sorted by Most listings")

    def test_active_filter_and_sort_chips_render_with_clear_urls(self):
        self.create_store_with_listings(
            "directory_polish_chip_v115",
            "Directory Polish Chip Store",
            location="Berlin",
            listing_count=3,
            verified=True,
        )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Polish Chip",
                "location": "Berlin",
                "verified_only": "1",
                "min_listings": "2",
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-active-chips-v115")
        self.assertContains(response, "seller-store-active-chip-v115")
        self.assertContains(response, "Search:")
        self.assertContains(response, "Polish Chip")
        self.assertContains(response, "Location:")
        self.assertContains(response, "Minimum listings:")
        self.assertContains(response, "2+ active listings")
        self.assertContains(response, "Trust:")
        self.assertContains(response, "Verified only")
        self.assertContains(response, "Sort:")
        self.assertContains(response, "Store name A-Z")
        self.assertContains(response, "Clear all")

        chip_labels = [
            chip["label"] for chip in response.context["directory_active_chips"]
        ]
        self.assertEqual(
            chip_labels,
            ["Search", "Location", "Minimum listings", "Trust", "Sort"],
        )

        chip_clear_urls = {
            chip["label"]: chip["clear_url"]
            for chip in response.context["directory_active_chips"]
        }
        self.assertNotIn("q=Polish+Chip", chip_clear_urls["Search"])
        self.assertIn("location=Berlin", chip_clear_urls["Search"])
        self.assertNotIn("location=Berlin", chip_clear_urls["Location"])
        self.assertIn("q=Polish+Chip", chip_clear_urls["Location"])
        self.assertNotIn("min_listings=2", chip_clear_urls["Minimum listings"])
        self.assertNotIn("verified_only=1", chip_clear_urls["Trust"])
        self.assertNotIn("sort=name_az", chip_clear_urls["Sort"])

    def test_default_directory_has_no_active_chips_or_clear_all(self):
        self.create_store_with_listings(
            "directory_polish_default_v115",
            "Directory Polish Default Store",
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directory_active_chips"], [])
        self.assertNotContains(response, 'aria-label="Active directory filters"')
        self.assertNotContains(response, "Clear all")

    def test_store_cards_show_scan_friendly_stats_and_actions(self):
        user, store = self.create_store_with_listings(
            "directory_polish_card_v115",
            "Directory Polish Card Store",
            location="Hamburg",
            listing_count=3,
            verified=True,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-directory-card-v115")
        self.assertContains(response, "seller-store-card-header-v115")
        self.assertContains(response, "seller-store-card-stats-v115")
        self.assertContains(response, "Active listings")
        self.assertContains(response, "3 active listings")
        self.assertContains(response, "Location")
        self.assertContains(response, "Hamburg")
        self.assertContains(response, "seller-store-card-actions-v115")
        self.assertContains(
            response,
            reverse("accounts:seller_store_public", kwargs={"slug": store.slug}),
        )

    def test_sort_only_state_gets_chip_and_clear_all_link(self):
        self.create_store_with_listings(
            "directory_polish_sort_only_v115",
            "Directory Polish Sort Only Store",
        )

        response = self.client.get(self.directory_url, {"sort": "newest"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-active-chips-v115")
        self.assertContains(response, "Sort:")
        self.assertContains(response, "Newest stores")
        self.assertContains(response, "Clear all")
        self.assertEqual(
            response.context["directory_active_chips"][0]["label"],
            "Sort",
        )
        self.assertEqual(
            response.context["directory_active_chips"][0]["clear_url"],
            self.directory_url,
        )
