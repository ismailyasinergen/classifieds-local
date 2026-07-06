from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore
from categories.models import Category
from listings.models import Listing


class SellerStoreCategoryTabsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="category_tabs_seller_v110",
            email="category-tabs-seller-v110@classifieds.local",
            password="StrongPass123!",
        )
        self.furniture = Category.objects.create(
            name="Store Tab Furniture",
            slug="store-tab-furniture-v110",
        )
        self.vehicles = Category.objects.create(
            name="Store Tab Vehicles",
            slug="store-tab-vehicles-v110",
        )
        self.hidden_category = Category.objects.create(
            name="Store Tab Hidden",
            slug="store-tab-hidden-v110",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Category Tab Store",
            headline="Browse this store by category.",
            description="A v110 store page for category tab testing.",
            location="Berlin",
        )

    def public_store_url(self):
        return reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})

    def create_listing(
        self,
        title,
        category,
        status=Listing.Status.APPROVED,
        price=Decimal("199.00"),
    ):
        return Listing.objects.create(
            title=title,
            description=f"{title} category tab test description.",
            price=price,
            category=category,
            owner=self.seller,
            location="Berlin",
            status=status,
        )

    def test_category_tabs_render_counts_for_active_approved_listing_categories(self):
        self.create_listing("Oak Storage Console", self.furniture)
        self.create_listing("Walnut Display Shelf", self.furniture)
        self.create_listing("Blue Compact Car", self.vehicles)
        self.create_listing(
            "Pending Hidden Category Listing",
            self.hidden_category,
            status=Listing.Status.PENDING,
        )

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-category-tabs-v110")
        self.assertContains(response, "All listings (3)")
        self.assertContains(response, "Store Tab Furniture (2)")
        self.assertContains(response, "Store Tab Vehicles (1)")
        self.assertNotContains(response, "Store Tab Hidden (")
        self.assertNotContains(
            response,
            f"?category={self.hidden_category.slug}#store-listings-v109",
        )

    def test_selected_category_tab_is_marked_active_and_filters_listings(self):
        furniture_listing = self.create_listing("Selected Furniture Item", self.furniture)
        vehicle_listing = self.create_listing("Selected Vehicle Item", self.vehicles)

        response = self.client.get(
            self.public_store_url(),
            {"category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "store-category-tab-active-v110")
        self.assertContains(response, 'aria-current="true"')
        self.assertContains(response, "Store Tab Furniture (1)")
        self.assertContains(response, furniture_listing.title)
        self.assertNotContains(response, vehicle_listing.title)

    def test_all_listings_tab_clears_category_but_preserves_search_query(self):
        self.create_listing("Searchable Oak Cabinet", self.furniture)
        self.create_listing("Searchable Oak Vehicle Rack", self.vehicles)

        response = self.client.get(
            self.public_store_url(),
            {"q": "Oak", "category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"?q=Oak#store-listings-v109")
        self.assertContains(response, f"?q=Oak&amp;category={self.furniture.slug}#store-listings-v109")

    def test_search_and_category_tabs_work_together(self):
        matching = self.create_listing("Minimal Lamp", self.furniture)
        self.create_listing("Vintage Chair", self.furniture)
        self.create_listing("Minimal Scooter", self.vehicles)

        response = self.client.get(
            self.public_store_url(),
            {"q": "Minimal", "category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.title)
        self.assertNotContains(response, "Vintage Chair")
        self.assertNotContains(response, "Minimal Scooter")
        self.assertContains(response, "Active Listings (1 of 3)")

    def test_empty_filtered_state_remains_clear_with_category_tabs(self):
        self.create_listing("Walnut Shelf", self.furniture)

        response = self.client.get(
            self.public_store_url(),
            {"q": "does-not-exist", "category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-category-tabs-v110")
        self.assertContains(response, "No listings match your store filters.")
        self.assertContains(response, "Clear")

    def test_pagination_preserves_selected_category_and_search_query(self):
        for index in range(13):
            self.create_listing(f"Paged Lamp {index:02d}", self.furniture)
        self.create_listing("Paged Vehicle Outside Filter", self.vehicles)

        response = self.client.get(
            self.public_store_url(),
            {"q": "Paged", "category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, f"category={self.furniture.slug}")
        self.assertContains(response, "q=Paged")
        self.assertNotContains(response, "Paged Vehicle Outside Filter")
