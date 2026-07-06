from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryFeaturedVerifiedTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Directory Featured Verified Furniture",
            slug="directory-featured-verified-furniture-v116",
        )
        self.directory_url = reverse("accounts:seller_store_directory")

    def create_store_with_listings(
        self,
        username,
        store_name,
        location="Berlin",
        listing_count=1,
        verified=False,
        store_active=True,
        listing_status=Listing.Status.APPROVED,
        expires_at=None,
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
            headline=f"{store_name} featured verified headline.",
            description=f"{store_name} featured verified description.",
            location=location,
            is_active=store_active,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} featured verified listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=location,
                status=listing_status,
                expires_at=expires_at,
            )

        return user, store

    def featured_store_names(self, response):
        return [store.name for store in response.context["featured_verified_stores"]]

    def test_featured_verified_section_renders_on_default_directory(self):
        verified_user, verified_store = self.create_store_with_listings(
            "featured_verified_default_v116",
            "Featured Verified Default Store",
            verified=True,
            listing_count=2,
        )
        unverified_user, unverified_store = self.create_store_with_listings(
            "featured_unverified_default_v116",
            "Featured Unverified Default Store",
            verified=False,
            listing_count=3,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-featured-verified-v116")
        self.assertContains(response, "Featured verified stores")
        self.assertContains(response, "Shop trusted seller stores")
        self.assertContains(response, "Verified picks")
        self.assertContains(response, "View verified store")
        self.assertEqual(self.featured_store_names(response), [verified_store.name])

        main_store_names = [store.name for store in response.context["stores"]]
        self.assertIn(verified_store.name, main_store_names)
        self.assertIn(unverified_store.name, main_store_names)

    def test_featured_verified_section_requires_active_verified_public_store(self):
        active_user, active_store = self.create_store_with_listings(
            "featured_active_verified_v116",
            "Featured Active Verified Store",
            verified=True,
        )
        inactive_user, inactive_store = self.create_store_with_listings(
            "featured_inactive_verified_v116",
            "Featured Inactive Verified Store",
            verified=True,
            store_active=False,
        )
        pending_user, pending_store = self.create_store_with_listings(
            "featured_pending_verified_v116",
            "Featured Pending Verified Store",
            verified=True,
            listing_status=Listing.Status.PENDING,
        )
        expired_user, expired_store = self.create_store_with_listings(
            "featured_expired_verified_v116",
            "Featured Expired Verified Store",
            verified=True,
            expires_at=timezone.now() - timedelta(days=1),
        )
        unverified_user, unverified_store = self.create_store_with_listings(
            "featured_unverified_public_v116",
            "Featured Unverified Public Store",
            verified=False,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.featured_store_names(response), [active_store.name])

    def test_featured_verified_section_is_hidden_when_directory_state_is_active(self):
        self.create_store_with_listings(
            "featured_hidden_state_v116",
            "Featured Hidden State Store",
            verified=True,
            location="Berlin",
            listing_count=3,
        )

        state_queries = (
            {"q": "Hidden State"},
            {"location": "Berlin"},
            {"verified_only": "1"},
            {"min_listings": "2"},
            {"sort": "newest"},
        )

        for query_params in state_queries:
            with self.subTest(query_params=query_params):
                response = self.client.get(self.directory_url, query_params)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["featured_verified_stores"], [])
                self.assertNotContains(response, "Featured verified stores")

    def test_featured_verified_section_limits_and_orders_by_active_listing_count(self):
        smallest_user, smallest_store = self.create_store_with_listings(
            "featured_smallest_v116",
            "Featured Smallest Store",
            verified=True,
            listing_count=1,
        )
        second_user, second_store = self.create_store_with_listings(
            "featured_second_v116",
            "Featured Second Store",
            verified=True,
            listing_count=2,
        )
        third_user, third_store = self.create_store_with_listings(
            "featured_third_v116",
            "Featured Third Store",
            verified=True,
            listing_count=3,
        )
        largest_user, largest_store = self.create_store_with_listings(
            "featured_largest_v116",
            "Featured Largest Store",
            verified=True,
            listing_count=4,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["featured_verified_limit"], 3)
        self.assertEqual(
            self.featured_store_names(response),
            [largest_store.name, third_store.name, second_store.name],
        )
        self.assertNotIn(smallest_store.name, self.featured_store_names(response))

    def test_no_featured_section_when_no_verified_store_qualifies(self):
        self.create_store_with_listings(
            "featured_none_unverified_v116",
            "Featured None Unverified Store",
            verified=False,
            listing_count=2,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["featured_verified_stores"], [])
        self.assertNotContains(response, "Featured verified stores")
        self.assertContains(response, "Featured None Unverified Store")
