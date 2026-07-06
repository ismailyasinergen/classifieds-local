from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryCombinedDiscoveryPolishTests(TestCase):
    def setUp(self):
        self.directory_url = reverse("accounts:seller_store_directory")
        self.furniture = Category.objects.create(
            name="Directory Combined Furniture V119",
            slug="directory-combined-furniture-v119",
        )
        self.decor = Category.objects.create(
            name="Directory Combined Decor V119",
            slug="directory-combined-decor-v119",
        )

    def create_store_with_listings(
        self,
        username,
        store_name,
        category,
        location="Berlin",
        listing_count=1,
        verified=False,
        listing_status=Listing.Status.APPROVED,
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
            headline=f"{store_name} combined discovery headline.",
            description=f"{store_name} combined discovery description.",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} combined discovery listing.",
                price=Decimal("125.00"),
                category=category,
                owner=user,
                location=location,
                status=listing_status,
            )

        return user, store

    def store_names(self, response):
        return [store.name for store in response.context["stores"]]

    def active_chip_labels(self, response):
        return [
            chip["label"]
            for chip in response.context["directory_active_chips"]
        ]

    def test_combined_discovery_module_renders_category_and_location_sections(self):
        self.create_store_with_listings(
            "combined_discovery_berlin_v119",
            "Combined Discovery Berlin Store",
            self.furniture,
            location="Berlin",
            listing_count=2,
        )
        self.create_store_with_listings(
            "combined_discovery_munich_v119",
            "Combined Discovery Munich Store",
            self.decor,
            location="Munich",
            listing_count=1,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-combined-discovery-v119")
        self.assertContains(response, 'aria-label="Explore seller store discovery"')
        self.assertContains(response, "seller-store-combined-header-v119")
        self.assertContains(response, "seller-store-combined-grid-v119")
        self.assertContains(response, "seller-store-combined-card-v119")
        self.assertContains(response, "Explore seller stores")
        self.assertContains(response, "Browse by category or city")
        self.assertContains(response, "Shop stores by category")
        self.assertContains(response, "Shop stores by location")
        self.assertContains(response, "Categories")
        self.assertContains(response, "Locations")
        self.assertContains(response, "seller-store-category-discovery-v117")
        self.assertContains(response, "seller-store-location-discovery-v118")

    def test_active_category_and_location_state_keep_clear_links(self):
        furniture_user, furniture_store = self.create_store_with_listings(
            "combined_active_furniture_berlin_v119",
            "Combined Active Furniture Berlin Store",
            self.furniture,
            location="Berlin",
            listing_count=3,
            verified=True,
        )
        decor_user, decor_store = self.create_store_with_listings(
            "combined_active_decor_munich_v119",
            "Combined Active Decor Munich Store",
            self.decor,
            location="Munich",
            listing_count=2,
            verified=True,
        )

        response = self.client.get(
            self.directory_url,
            {
                "category": self.furniture.slug,
                "location": "Berlin",
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store_names(response), [furniture_store.name])
        self.assertContains(response, furniture_store.name)
        self.assertNotContains(response, decor_store.name)
        self.assertContains(response, "All categories")
        self.assertContains(response, "All locations")
        self.assertContains(response, "Category:")
        self.assertContains(response, "Location:")
        self.assertContains(response, "Sort:")
        self.assertContains(response, "Clear all")
        self.assertNotContains(response, "Featured verified stores")
        self.assertEqual(
            self.active_chip_labels(response),
            ["Location", "Category", "Sort"],
        )

        self.assertIn("location=Berlin", response.context["directory_category_clear_url"])
        self.assertNotIn(f"category={self.furniture.slug}", response.context["directory_category_clear_url"])
        self.assertIn(f"category={self.furniture.slug}", response.context["directory_location_clear_url"])
        self.assertNotIn("location=Berlin", response.context["directory_location_clear_url"])

    def test_category_and_location_shortcuts_preserve_query_and_sort_state(self):
        self.create_store_with_listings(
            "combined_preserve_berlin_v119",
            "Combined Preserve Berlin Store",
            self.furniture,
            location="Berlin",
            listing_count=2,
        )
        self.create_store_with_listings(
            "combined_preserve_hamburg_v119",
            "Combined Preserve Hamburg Store",
            self.decor,
            location="Hamburg",
            listing_count=1,
        )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Combined Preserve",
                "sort": "newest",
            },
        )

        self.assertEqual(response.status_code, 200)

        furniture_category = next(
            category
            for category in response.context["popular_directory_categories"]
            if category.slug == self.furniture.slug
        )
        berlin_location = next(
            location_item
            for location_item in response.context["popular_directory_locations"]
            if location_item["label"] == "Berlin"
        )

        self.assertIn("q=Combined+Preserve", furniture_category.directory_url)
        self.assertIn("sort=newest", furniture_category.directory_url)
        self.assertIn(f"category={self.furniture.slug}", furniture_category.directory_url)

        self.assertIn("q=Combined+Preserve", berlin_location["directory_url"])
        self.assertIn("sort=newest", berlin_location["directory_url"])
        self.assertIn("location=Berlin", berlin_location["directory_url"])

    def test_combined_discovery_mobile_layout_markers_render(self):
        self.create_store_with_listings(
            "combined_mobile_berlin_v119",
            "Combined Mobile Berlin Store",
            self.furniture,
            location="Berlin",
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-combined-metrics-v119")
        self.assertContains(response, "seller-store-combined-description-v119")
        self.assertContains(response, "seller-store-discovery-section-eyebrow-v119")
        self.assertContains(response, "seller-store-category-chip-v117")
        self.assertContains(response, "seller-store-location-chip-v118")

    def test_combined_discovery_module_is_hidden_without_discovery_data(self):
        self.create_store_with_listings(
            "combined_hidden_pending_v119",
            "Combined Hidden Pending Store",
            self.furniture,
            location="Berlin",
            listing_status=Listing.Status.PENDING,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["popular_directory_categories"], [])
        self.assertEqual(response.context["popular_directory_locations"], [])
        self.assertNotContains(response, 'aria-label="Explore seller store discovery"')
        self.assertNotContains(response, "Explore seller stores")
        self.assertNotContains(response, "Browse by category or city")
