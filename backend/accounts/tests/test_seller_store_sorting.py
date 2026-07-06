from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import SellerStore
from categories.models import Category
from listings.models import Listing


class SellerStoreSortingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="store_sort_seller_v111",
            email="store-sort-seller-v111@classifieds.local",
            password="StrongPass123!",
        )
        self.furniture = Category.objects.create(
            name="Store Sort Furniture",
            slug="store-sort-furniture-v111",
        )
        self.vehicles = Category.objects.create(
            name="Store Sort Vehicles",
            slug="store-sort-vehicles-v111",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Sortable Seller Store",
            headline="Sort this seller inventory.",
            description="A v111 store page for sorting tests.",
            location="Berlin",
        )

    def public_store_url(self):
        return reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})

    def create_listing(
        self,
        title,
        price,
        category=None,
        created_at=None,
        top_listing_priority=0,
    ):
        listing = Listing.objects.create(
            title=title,
            description=f"{title} sort test description.",
            price=Decimal(str(price)),
            category=category or self.furniture,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
            top_listing_priority=top_listing_priority,
        )
        if created_at is not None:
            Listing.objects.filter(pk=listing.pk).update(created_at=created_at)
            listing.refresh_from_db()
        return listing

    def assert_titles_in_order(self, response, *titles):
        content = response.content.decode()
        positions = [content.index(title) for title in titles]
        self.assertEqual(positions, sorted(positions), titles)

    def test_default_sort_uses_newest_first(self):
        now = timezone.now()
        older = self.create_listing(
            "Default Older Listing",
            "300.00",
            created_at=now - timedelta(days=2),
        )
        newer = self.create_listing(
            "Default Newer Listing",
            "100.00",
            created_at=now,
        )

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-sort-v111")
        self.assertContains(response, "Newest first")
        self.assertContains(response, 'value="newest" selected')
        self.assert_titles_in_order(response, newer.title, older.title)

    def test_oldest_sort_orders_oldest_first(self):
        now = timezone.now()
        older = self.create_listing(
            "Oldest Sort First",
            "300.00",
            created_at=now - timedelta(days=3),
        )
        newer = self.create_listing(
            "Oldest Sort Second",
            "100.00",
            created_at=now,
        )

        response = self.client.get(self.public_store_url(), {"sort": "oldest"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="oldest" selected')
        self.assert_titles_in_order(response, older.title, newer.title)

    def test_price_ascending_sort_orders_low_to_high(self):
        high = self.create_listing("Expensive Store Item", "900.00")
        low = self.create_listing("Affordable Store Item", "50.00")
        middle = self.create_listing("Middle Store Item", "250.00")

        response = self.client.get(self.public_store_url(), {"sort": "price_asc"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="price_asc" selected')
        self.assert_titles_in_order(response, low.title, middle.title, high.title)

    def test_price_descending_sort_orders_high_to_low(self):
        high = self.create_listing("High Price Store Item", "900.00")
        low = self.create_listing("Low Price Store Item", "50.00")
        middle = self.create_listing("Medium Price Store Item", "250.00")

        response = self.client.get(self.public_store_url(), {"sort": "price_desc"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="price_desc" selected')
        self.assert_titles_in_order(response, high.title, middle.title, low.title)

    def test_invalid_sort_falls_back_to_newest_without_preserving_invalid_value(self):
        now = timezone.now()
        older = self.create_listing(
            "Invalid Sort Older",
            "20.00",
            created_at=now - timedelta(days=5),
        )
        newer = self.create_listing(
            "Invalid Sort Newer",
            "10.00",
            created_at=now,
        )

        response = self.client.get(self.public_store_url(), {"sort": "unsafe-sort"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="newest" selected')
        self.assertNotContains(response, "unsafe-sort")
        self.assert_titles_in_order(response, newer.title, older.title)

    def test_pagination_preserves_query_category_and_sort(self):
        for index in range(13):
            self.create_listing(
                f"Paged Sort Lamp {index:02d}",
                str(100 + index),
                category=self.furniture,
            )
        self.create_listing(
            "Paged Sort Vehicle Outside Filter",
            "1.00",
            category=self.vehicles,
        )

        response = self.client.get(
            self.public_store_url(),
            {
                "q": "Paged Sort",
                "category": self.furniture.slug,
                "sort": "price_desc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, "q=Paged+Sort")
        self.assertContains(response, f"category={self.furniture.slug}")
        self.assertContains(response, "sort=price_desc")
        self.assertNotContains(response, "Paged Sort Vehicle Outside Filter")

    def test_category_tab_urls_preserve_search_and_sort_but_drop_page(self):
        self.create_listing("Tab Preserve Furniture Item", "100.00", self.furniture)
        self.create_listing("Tab Preserve Vehicle Item", "200.00", self.vehicles)

        response = self.client.get(
            self.public_store_url(),
            {
                "q": "Tab Preserve",
                "sort": "price_asc",
                "category": self.furniture.slug,
                "page": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-category-tabs-v110")
        self.assertContains(response, "q=Tab+Preserve")
        self.assertContains(response, "sort=price_asc")
        self.assertContains(response, f"category={self.vehicles.slug}#store-listings-v109")
        self.assertNotContains(response, "page=2&amp;category")
