from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryLocationDiscoveryTests(TestCase):
    def setUp(self):
        self.directory_url = reverse("accounts:seller_store_directory")
        self.category = Category.objects.create(
            name="Directory Location Discovery V118",
            slug="directory-location-discovery-v118",
        )

    def create_store_with_listings(
        self,
        username,
        store_name,
        store_location="Berlin",
        profile_location=None,
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
        user.profile.location = (
            profile_location if profile_location is not None else store_location
        )
        user.profile.verification_status = (
            UserProfile.VerificationStatus.APPROVED
            if verified
            else UserProfile.VerificationStatus.NOT_REQUESTED
        )
        user.profile.save(update_fields=["location", "verification_status"])

        store = SellerStore.objects.create(
            owner=user,
            name=store_name,
            headline=f"{store_name} location discovery headline.",
            description=f"{store_name} location discovery description.",
            location=store_location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} directory location discovery listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=store_location or profile_location or "Not specified",
                status=listing_status,
            )

        return user, store

    def store_names(self, response):
        return [store.name for store in response.context["stores"]]

    def popular_location_labels(self, response):
        return [
            location_item["label"]
            for location_item in response.context["popular_directory_locations"]
        ]

    def active_chip_labels(self, response):
        return [
            chip["label"]
            for chip in response.context["directory_active_chips"]
        ]

    def test_location_discovery_chips_render_with_active_store_counts(self):
        first_user, first_store = self.create_store_with_listings(
            "directory_location_berlin_first_v118",
            "Directory Location Berlin First Store",
            store_location="Berlin",
            listing_count=2,
        )
        second_user, second_store = self.create_store_with_listings(
            "directory_location_berlin_second_v118",
            "Directory Location Berlin Second Store",
            store_location="Berlin",
            listing_count=1,
        )
        munich_user, munich_store = self.create_store_with_listings(
            "directory_location_munich_v118",
            "Directory Location Munich Store",
            store_location="Munich",
            listing_count=1,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-location-discovery-v118")
        self.assertContains(response, "Shop stores by location")
        self.assertContains(response, "Find active seller stores near")
        self.assertContains(response, "seller-store-location-chip-v118")
        self.assertContains(response, "Berlin")
        self.assertContains(response, "2 stores")
        self.assertContains(response, "Munich")
        self.assertContains(response, "1 store")
        self.assertContains(response, "location=Berlin")
        self.assertEqual(response.context["directory_location_limit"], 8)
        self.assertEqual(
            self.popular_location_labels(response)[:2],
            ["Berlin", "Munich"],
        )

    def test_location_discovery_uses_profile_location_when_store_location_is_blank(self):
        user, store = self.create_store_with_listings(
            "directory_location_profile_fallback_v118",
            "Directory Location Profile Fallback Store",
            store_location="",
            profile_location="Hamburg",
            listing_count=1,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hamburg")
        self.assertContains(response, "location=Hamburg")
        self.assertIn("Hamburg", self.popular_location_labels(response))

    def test_location_chip_filter_limits_directory_to_matching_stores(self):
        berlin_user, berlin_store = self.create_store_with_listings(
            "directory_location_filter_berlin_v118",
            "Directory Location Filter Berlin Store",
            store_location="Berlin",
            listing_count=2,
            verified=True,
        )
        munich_user, munich_store = self.create_store_with_listings(
            "directory_location_filter_munich_v118",
            "Directory Location Filter Munich Store",
            store_location="Munich",
            listing_count=3,
            verified=True,
        )

        response = self.client.get(self.directory_url, {"location": "Berlin"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store_names(response), [berlin_store.name])
        self.assertContains(response, berlin_store.name)
        self.assertNotContains(response, munich_store.name)
        self.assertContains(response, "Location:")
        self.assertContains(response, "Berlin")
        self.assertContains(response, "All locations")
        self.assertContains(response, "Clear all")
        self.assertNotContains(response, "Featured verified stores")
        self.assertIn("Location", self.active_chip_labels(response))
        selected_locations = [
            location_item
            for location_item in response.context["popular_directory_locations"]
            if location_item["is_selected"]
        ]
        self.assertEqual([location_item["label"] for location_item in selected_locations], ["Berlin"])

    def test_location_chip_urls_preserve_category_sort_and_search_state(self):
        category = Category.objects.create(
            name="Directory Location URL Category V118",
            slug="directory-location-url-category-v118",
        )
        user, store = self.create_store_with_listings(
            "directory_location_url_v118",
            "Directory Location URL Store",
            store_location="Berlin",
            listing_count=13,
        )
        Listing.objects.filter(owner=user).update(category=category)

        response = self.client.get(
            self.directory_url,
            {
                "q": "Directory Location URL",
                "category": category.slug,
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "q=Directory+Location+URL")
        self.assertContains(response, f"category={category.slug}")
        self.assertContains(response, "sort=name_az")
        self.assertContains(response, "location=Berlin")

    def test_location_filter_is_preserved_in_pagination_and_category_urls(self):
        for index in range(13):
            self.create_store_with_listings(
                f"directory_location_paged_v118_{index}",
                f"Directory Location Paged Store {index:02d}",
                store_location="Berlin",
                listing_count=2,
            )

        response = self.client.get(
            self.directory_url,
            {
                "location": "Berlin",
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, "location=Berlin")
        self.assertContains(response, "sort=name_az")

    def test_location_discovery_is_hidden_when_no_active_store_locations_exist(self):
        self.create_store_with_listings(
            "directory_location_pending_v118",
            "Directory Location Pending Store",
            store_location="Berlin",
            profile_location="Berlin",
            listing_status=Listing.Status.PENDING,
        )
        self.create_store_with_listings(
            "directory_location_blank_v118",
            "Directory Location Blank Store",
            store_location="",
            profile_location="",
            listing_status=Listing.Status.APPROVED,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["popular_directory_locations"], [])
        self.assertNotContains(response, "Shop stores by location")
        self.assertNotContains(response, 'aria-label="Popular store locations"')
