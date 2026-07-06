from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore
from categories.models import Category
from listings.models import Listing


class SellerStorefrontPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="storefront_polish_seller",
            email="storefront-polish-seller@classifieds.local",
            password="StrongPass123!",
        )
        self.buyer = User.objects.create_user(
            username="storefront_polish_buyer",
            email="storefront-polish-buyer@classifieds.local",
            password="StrongPass123!",
        )
        self.furniture = Category.objects.create(
            name="Storefront Furniture",
            slug="storefront-furniture-v106",
        )
        self.vehicles = Category.objects.create(
            name="Storefront Vehicles",
            slug="storefront-vehicles-v106",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Polished Seller Store",
            headline="Curated local listings from one seller.",
            description="A clearer storefront for browsing seller inventory.",
            location="Berlin",
        )

    def create_listing(self, title, category, status=Listing.Status.APPROVED):
        return Listing.objects.create(
            title=title,
            description=f"{title} description for store filtering.",
            price=Decimal("250.00"),
            category=category,
            owner=self.seller,
            location="Berlin",
            status=status,
        )

    def test_dashboard_shows_store_shortcut_and_public_link(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seller Store")
        self.assertContains(response, "Store Settings")
        self.assertContains(response, "View Public Store")
        self.assertContains(
            response,
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
        )

    def test_profile_shows_store_settings_shortcut(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage Seller Store")
        self.assertContains(response, reverse("accounts:seller_store_settings"))

    def test_public_store_search_filters_approved_listings(self):
        lamp = self.create_listing("Oak Lamp With Storage", self.furniture)
        sedan = self.create_listing("Blue Sedan", self.vehicles)

        response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
            {"q": "lamp"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search this store")
        self.assertContains(response, lamp.title)
        self.assertNotContains(response, sedan.title)
        self.assertContains(response, "Clear")

    def test_public_store_category_filter_limits_listings(self):
        lamp = self.create_listing("Category Filter Lamp", self.furniture)
        sedan = self.create_listing("Category Filter Sedan", self.vehicles)

        response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
            {"category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, lamp.title)
        self.assertNotContains(response, sedan.title)
        self.assertContains(response, "Storefront Furniture")

    def test_public_store_no_filter_match_has_clear_empty_state(self):
        self.create_listing("Walnut Console", self.furniture)

        response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
            {"q": "does-not-exist"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No listings match your store filters.")

    def test_listing_card_links_to_public_seller_store(self):
        listing = self.create_listing("Store Card Discoverability Listing", self.furniture)

        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, listing.title)
        self.assertContains(response, "Store: Polished Seller Store")
        self.assertContains(
            response,
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
        )

    def test_inactive_store_is_not_linked_from_listing_card(self):
        self.store.is_active = False
        self.store.save(update_fields=["is_active", "updated_at"])
        listing = self.create_listing("Inactive Store Listing", self.furniture)

        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, listing.title)
        self.assertNotContains(response, "Store: Polished Seller Store")
        self.assertNotContains(
            response,
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
        )
