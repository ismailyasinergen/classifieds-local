from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryFilterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.category = Category.objects.create(
            name="Directory Filter Furniture",
            slug="directory-filter-furniture-v113",
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
            headline=f"{store_name} headline",
            description=f"{store_name} description",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} directory filter listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=location,
                status=Listing.Status.APPROVED,
            )

        return user, store

    def test_directory_filter_ui_renders(self):
        self.create_store_with_listings(
            "directory_filter_ui_v113",
            "Directory Filter UI Store",
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-directory-filters-v113")
        self.assertContains(response, 'name="location"')
        self.assertContains(response, 'name="min_listings"')
        self.assertContains(response, 'name="verified_only"')
        self.assertContains(response, "Filter stores")

    def test_verified_only_filter_shows_only_approved_verified_sellers(self):
        verified_user, verified_store = self.create_store_with_listings(
            "verified_directory_filter_v113",
            "Verified Directory Filter Store",
            verified=True,
        )
        unverified_user, unverified_store = self.create_store_with_listings(
            "unverified_directory_filter_v113",
            "Unverified Directory Filter Store",
            verified=False,
        )

        response = self.client.get(self.directory_url, {"verified_only": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, verified_store.name)
        self.assertContains(response, "Verified Seller")
        self.assertContains(response, "checked")
        self.assertNotContains(response, unverified_store.name)

    def test_location_filter_matches_store_and_profile_location(self):
        berlin_user, berlin_store = self.create_store_with_listings(
            "berlin_directory_filter_v113",
            "Berlin Directory Filter Store",
            location="Berlin",
        )
        munich_user, munich_store = self.create_store_with_listings(
            "munich_directory_filter_v113",
            "Munich Directory Filter Store",
            location="Munich",
        )

        response = self.client.get(self.directory_url, {"location": "Munich"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, munich_store.name)
        self.assertContains(response, 'value="Munich"')
        self.assertNotContains(response, berlin_store.name)

    def test_minimum_active_listings_filter_uses_annotated_count(self):
        small_user, small_store = self.create_store_with_listings(
            "small_directory_filter_v113",
            "Small Directory Filter Store",
            listing_count=1,
        )
        large_user, large_store = self.create_store_with_listings(
            "large_directory_filter_v113",
            "Large Directory Filter Store",
            listing_count=3,
        )

        response = self.client.get(self.directory_url, {"min_listings": "2"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, large_store.name)
        self.assertContains(response, "3 active listings")
        self.assertContains(response, 'value="2"')
        self.assertNotContains(response, small_store.name)

    def test_directory_filters_combine_with_existing_search(self):
        verified_user, verified_store = self.create_store_with_listings(
            "combo_verified_directory_filter_v113",
            "Combo Berlin Verified Store",
            location="Berlin",
            listing_count=4,
            verified=True,
        )
        wrong_location_user, wrong_location_store = self.create_store_with_listings(
            "combo_wrong_location_directory_filter_v113",
            "Combo Munich Verified Store",
            location="Munich",
            listing_count=4,
            verified=True,
        )
        too_few_user, too_few_store = self.create_store_with_listings(
            "combo_too_few_directory_filter_v113",
            "Combo Berlin Small Store",
            location="Berlin",
            listing_count=1,
            verified=True,
        )
        unverified_user, unverified_store = self.create_store_with_listings(
            "combo_unverified_directory_filter_v113",
            "Combo Berlin Unverified Store",
            location="Berlin",
            listing_count=4,
            verified=False,
        )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Combo",
                "location": "Berlin",
                "verified_only": "1",
                "min_listings": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, verified_store.name)
        self.assertNotContains(response, wrong_location_store.name)
        self.assertNotContains(response, too_few_store.name)
        self.assertNotContains(response, unverified_store.name)

    def test_invalid_min_listings_is_ignored_and_not_preserved_in_pagination(self):
        for index in range(13):
            self.create_store_with_listings(
                f"invalid_min_directory_filter_v113_{index}",
                f"Invalid Min Directory Filter Store {index:02d}",
                listing_count=1,
            )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Invalid Min",
                "min_listings": "not-a-number",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "q=Invalid+Min")
        self.assertNotContains(response, "not-a-number")
        self.assertNotContains(response, "min_listings=not-a-number")

    def test_pagination_preserves_directory_filters(self):
        for index in range(13):
            self.create_store_with_listings(
                f"paged_directory_filter_v113_{index}",
                f"Paged Directory Filter Store {index:02d}",
                location="Berlin",
                listing_count=2,
                verified=True,
            )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Paged",
                "location": "Berlin",
                "verified_only": "1",
                "min_listings": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, "q=Paged")
        self.assertContains(response, "location=Berlin")
        self.assertContains(response, "verified_only=1")
        self.assertContains(response, "min_listings=2")

    def test_filter_empty_state_uses_directory_filter_message(self):
        self.create_store_with_listings(
            "empty_state_directory_filter_v113",
            "Empty State Directory Filter Store",
            location="Berlin",
        )

        response = self.client.get(
            self.directory_url,
            {"location": "No Matching City"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No seller stores match your directory filters.")
        self.assertContains(response, "Clear")
