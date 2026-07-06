from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryEmptyStateSuggestionTests(TestCase):
    def setUp(self):
        self.directory_url = reverse("accounts:seller_store_directory")
        self.furniture = Category.objects.create(
            name="Directory Empty Furniture V120",
            slug="directory-empty-furniture-v120",
        )
        self.decor = Category.objects.create(
            name="Directory Empty Decor V120",
            slug="directory-empty-decor-v120",
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
            headline=f"{store_name} empty-state suggestion headline.",
            description=f"{store_name} empty-state suggestion description.",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} empty-state suggestion listing.",
                price=Decimal("125.00"),
                category=category,
                owner=user,
                location=location,
                status=listing_status,
            )

        return user, store

    def test_search_empty_state_shows_category_and_location_suggestions(self):
        self.create_store_with_listings(
            "directory_empty_search_berlin_v120",
            "Directory Empty Search Berlin Store",
            self.furniture,
            location="Berlin",
            listing_count=2,
        )
        self.create_store_with_listings(
            "directory_empty_search_munich_v120",
            "Directory Empty Search Munich Store",
            self.decor,
            location="Munich",
            listing_count=1,
        )

        response = self.client.get(self.directory_url, {"q": "no-match-v120"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-empty-state-v120")
        self.assertContains(response, 'aria-label="Seller store empty-state suggestions"')
        self.assertContains(response, "No seller stores match your search.")
        self.assertContains(response, "Try a broader keyword")
        self.assertContains(response, "Clear all filters")
        self.assertContains(response, "Try a category")
        self.assertContains(response, "Try a location")
        self.assertContains(response, "Directory Empty Furniture V120")
        self.assertContains(response, "Berlin")
        self.assertContains(response, "seller-store-empty-suggestion-chip-v120")
        self.assertEqual(len(response.context["directory_empty_category_suggestions"]), 2)
        self.assertEqual(len(response.context["directory_empty_location_suggestions"]), 2)

    def test_filter_empty_state_shows_filter_message_and_active_shortcuts(self):
        self.create_store_with_listings(
            "directory_empty_filter_berlin_v120",
            "Directory Empty Filter Berlin Store",
            self.furniture,
            location="Berlin",
            listing_count=2,
            verified=True,
        )
        self.create_store_with_listings(
            "directory_empty_filter_hamburg_v120",
            "Directory Empty Filter Hamburg Store",
            self.decor,
            location="Hamburg",
            listing_count=1,
            verified=True,
        )

        response = self.client.get(
            self.directory_url,
            {
                "location": "No Matching City",
                "verified_only": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No seller stores match your directory filters.")
        self.assertContains(response, "Your current filters are too narrow")
        self.assertContains(response, "Clear all filters")
        self.assertContains(response, "Try a category")
        self.assertContains(response, "Try a location")
        self.assertNotContains(response, "Featured verified stores")

    def test_suggestion_urls_clear_failed_filters_but_preserve_non_default_sort(self):
        self.create_store_with_listings(
            "directory_empty_url_berlin_v120",
            "Directory Empty URL Berlin Store",
            self.furniture,
            location="Berlin",
            listing_count=2,
        )

        response = self.client.get(
            self.directory_url,
            {
                "q": "no-match-v120",
                "location": "No Matching City",
                "min_listings": "9",
                "verified_only": "1",
                "sort": "newest",
            },
        )

        self.assertEqual(response.status_code, 200)

        category_url = response.context["directory_empty_category_suggestions"][0]["url"]
        location_url = response.context["directory_empty_location_suggestions"][0]["url"]

        self.assertIn(f"category={self.furniture.slug}", category_url)
        self.assertIn("location=Berlin", location_url)
        self.assertIn("sort=newest", category_url)
        self.assertIn("sort=newest", location_url)

        for url in (category_url, location_url):
            self.assertNotIn("q=no-match-v120", url)
            self.assertNotIn("No+Matching+City", url)
            self.assertNotIn("min_listings=9", url)
            self.assertNotIn("verified_only=1", url)

    def test_empty_state_suggestions_are_limited(self):
        for index in range(6):
            category = Category.objects.create(
                name=f"Directory Empty Limit Category {index} V120",
                slug=f"directory-empty-limit-category-{index}-v120",
            )
            self.create_store_with_listings(
                f"directory_empty_limit_{index}_v120",
                f"Directory Empty Limit Store {index}",
                category,
                location=f"City {index}",
                listing_count=1,
            )

        response = self.client.get(self.directory_url, {"q": "missing-limit-v120"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directory_empty_suggestion_limit"], 4)
        self.assertEqual(len(response.context["directory_empty_category_suggestions"]), 4)
        self.assertEqual(len(response.context["directory_empty_location_suggestions"]), 4)

    def test_no_active_stores_empty_state_has_no_suggestions(self):
        self.create_store_with_listings(
            "directory_empty_pending_v120",
            "Directory Empty Pending Store",
            self.furniture,
            location="Berlin",
            listing_status=Listing.Status.PENDING,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active seller stores are available yet.")
        self.assertNotContains(response, "Try a category")
        self.assertNotContains(response, "Try a location")
        self.assertEqual(response.context["directory_empty_category_suggestions"], [])
        self.assertEqual(response.context["directory_empty_location_suggestions"], [])
