from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectorySortingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Directory Sorting Furniture",
            slug="directory-sorting-furniture-v114",
        )
        self.directory_url = reverse("accounts:seller_store_directory")

    def create_store_with_listings(
        self,
        username,
        store_name,
        listing_count=1,
        verified=False,
        created_at=None,
        location="Berlin",
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

        if created_at is not None:
            SellerStore.objects.filter(pk=store.pk).update(created_at=created_at)
            store.refresh_from_db()

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} directory sorting listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=location,
                status=Listing.Status.APPROVED,
            )

        return user, store

    def store_names(self, response):
        return [store.name for store in response.context["stores"]]

    def test_directory_sort_ui_renders_options(self):
        self.create_store_with_listings(
            "directory_sort_ui_v114",
            "Directory Sort UI Store",
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-directory-sorting-v114")
        self.assertContains(response, 'name="sort"')
        self.assertContains(response, "Most listings")
        self.assertContains(response, "Store name A-Z")
        self.assertContains(response, "Newest stores")
        self.assertContains(response, "Verified sellers first")

    def test_default_sort_keeps_most_listings_first(self):
        small_user, small_store = self.create_store_with_listings(
            "small_directory_sort_v114",
            "Small Directory Sort Store",
            listing_count=1,
        )
        large_user, large_store = self.create_store_with_listings(
            "large_directory_sort_v114",
            "Large Directory Sort Store",
            listing_count=3,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.store_names(response),
            [large_store.name, small_store.name],
        )
        self.assertEqual(response.context["selected_directory_sort"], "most_listings")

    def test_name_az_sort_orders_by_store_name(self):
        beta_user, beta_store = self.create_store_with_listings(
            "beta_directory_sort_v114",
            "Beta Directory Sort Store",
            listing_count=2,
        )
        alpha_user, alpha_store = self.create_store_with_listings(
            "alpha_directory_sort_v114",
            "Alpha Directory Sort Store",
            listing_count=2,
        )

        response = self.client.get(self.directory_url, {"sort": "name_az"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.store_names(response),
            [alpha_store.name, beta_store.name],
        )
        self.assertEqual(response.context["selected_directory_sort"], "name_az")

    def test_newest_sort_orders_newest_store_first(self):
        now = timezone.now()
        old_user, old_store = self.create_store_with_listings(
            "old_directory_sort_v114",
            "Old Directory Sort Store",
            created_at=now - timedelta(days=10),
        )
        new_user, new_store = self.create_store_with_listings(
            "new_directory_sort_v114",
            "New Directory Sort Store",
            created_at=now,
        )

        response = self.client.get(self.directory_url, {"sort": "newest"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.store_names(response),
            [new_store.name, old_store.name],
        )

    def test_verified_first_sort_orders_verified_sellers_before_unverified(self):
        unverified_user, unverified_store = self.create_store_with_listings(
            "unverified_directory_sort_v114",
            "Unverified Directory Sort Store",
            listing_count=5,
            verified=False,
        )
        verified_user, verified_store = self.create_store_with_listings(
            "verified_directory_sort_v114",
            "Verified Directory Sort Store",
            listing_count=1,
            verified=True,
        )

        response = self.client.get(self.directory_url, {"sort": "verified_first"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.store_names(response),
            [verified_store.name, unverified_store.name],
        )
        self.assertEqual(response.context["selected_directory_sort"], "verified_first")

    def test_invalid_sort_falls_back_to_default_and_is_not_preserved(self):
        for index in range(13):
            self.create_store_with_listings(
                f"invalid_directory_sort_v114_{index}",
                f"Invalid Directory Sort Store {index:02d}",
                listing_count=1,
            )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Invalid Directory",
                "sort": "unsafe-sort",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_directory_sort"], "most_listings")
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "q=Invalid+Directory")
        self.assertNotContains(response, "unsafe-sort")
        self.assertNotContains(response, "sort=unsafe-sort")

    def test_pagination_preserves_sort_and_directory_filters(self):
        for index in range(13):
            self.create_store_with_listings(
                f"paged_directory_sort_v114_{index}",
                f"Paged Directory Sort Store {index:02d}",
                listing_count=2,
                verified=True,
                location="Berlin",
            )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Paged",
                "location": "Berlin",
                "verified_only": "1",
                "min_listings": "2",
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, "q=Paged")
        self.assertContains(response, "location=Berlin")
        self.assertContains(response, "verified_only=1")
        self.assertContains(response, "min_listings=2")
        self.assertContains(response, "sort=name_az")
