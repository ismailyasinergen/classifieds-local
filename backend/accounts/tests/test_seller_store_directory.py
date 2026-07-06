from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import SellerStore
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.category = Category.objects.create(
            name="Directory Furniture",
            slug="directory-furniture-v107",
        )
        self.seller = User.objects.create_user(
            username="directory_seller_v107",
            email="directory-seller-v107@classifieds.local",
            password="StrongPass123!",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Directory Seller Store",
            headline="Visible seller with approved listings.",
            description="A public directory seller.",
            location="Berlin",
        )

    def create_listing(
        self,
        owner,
        title,
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            title=title,
            description=f"{title} directory test listing.",
            price=Decimal("125.00"),
            category=self.category,
            owner=owner,
            location="Berlin",
            status=status,
            expires_at=expires_at,
        )

    def create_store_with_user(self, username, name, **store_kwargs):
        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            email=f"{username}@classifieds.local",
            password="StrongPass123!",
        )
        store = SellerStore.objects.create(
            owner=user,
            name=name,
            headline=store_kwargs.pop("headline", ""),
            description=store_kwargs.pop("description", ""),
            location=store_kwargs.pop("location", ""),
            is_active=store_kwargs.pop("is_active", True),
        )
        return user, store

    def test_directory_lists_active_store_with_approved_listing(self):
        self.create_listing(self.seller, "Directory Approved Listing")

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seller Stores")
        self.assertContains(response, "Directory Seller Store")
        self.assertContains(response, "1 active listing")
        self.assertContains(
            response,
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
        )

    def test_directory_hides_store_without_approved_public_listing(self):
        pending_user, pending_store = self.create_store_with_user(
            "pending_directory_seller_v107",
            "Pending Only Store",
        )
        no_listing_user, no_listing_store = self.create_store_with_user(
            "empty_directory_seller_v107",
            "No Listing Store",
        )
        self.create_listing(self.seller, "Visible Approved Listing")
        self.create_listing(
            pending_user,
            "Pending Hidden Listing",
            status=Listing.Status.PENDING,
        )

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Directory Seller Store")
        self.assertNotContains(response, pending_store.name)
        self.assertNotContains(response, no_listing_store.name)

    def test_directory_hides_inactive_store_even_with_approved_listing(self):
        inactive_user, inactive_store = self.create_store_with_user(
            "inactive_directory_seller_v107",
            "Inactive Directory Store",
            is_active=False,
        )
        self.create_listing(inactive_user, "Inactive Store Approved Listing")

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, inactive_store.name)

    def test_directory_hides_expired_approved_listing_store(self):
        expired_user, expired_store = self.create_store_with_user(
            "expired_directory_seller_v107",
            "Expired Directory Store",
        )
        self.create_listing(
            expired_user,
            "Expired Approved Listing",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, expired_store.name)

    def test_directory_search_matches_store_name_location_and_seller(self):
        self.create_listing(self.seller, "Directory Search Listing")
        munich_user, munich_store = self.create_store_with_user(
            "munich_store_owner_v107",
            "Alpine Market Store",
            location="Munich",
            headline="Bavaria seller storefront",
        )
        self.create_listing(munich_user, "Munich Store Listing")

        name_response = self.client.get(
            reverse("accounts:seller_store_directory"),
            {"q": "Alpine"},
        )
        self.assertEqual(name_response.status_code, 200)
        self.assertContains(name_response, munich_store.name)
        self.assertNotContains(name_response, self.store.name)

        location_response = self.client.get(
            reverse("accounts:seller_store_directory"),
            {"q": "Munich"},
        )
        self.assertEqual(location_response.status_code, 200)
        self.assertContains(location_response, munich_store.name)

        seller_response = self.client.get(
            reverse("accounts:seller_store_directory"),
            {"q": "directory_seller_v107"},
        )
        self.assertEqual(seller_response.status_code, 200)
        self.assertContains(seller_response, self.store.name)

    def test_directory_search_empty_state(self):
        self.create_listing(self.seller, "Visible Directory Listing")

        response = self.client.get(
            reverse("accounts:seller_store_directory"),
            {"q": "no-match-v107"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No seller stores match your search.")
        self.assertContains(response, "Clear")

    def test_header_navigation_links_to_store_directory(self):
        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stores")
        self.assertContains(response, reverse("accounts:seller_store_directory"))
