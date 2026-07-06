from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import SellerStore
from categories.models import Category
from listings.models import Listing


class SellerStorePinnedListingsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="store_pinned_seller_v112",
            email="store-pinned-seller-v112@classifieds.local",
            password="StrongPass123!",
        )
        self.furniture = Category.objects.create(
            name="Store Pinned Furniture",
            slug="store-pinned-furniture-v112",
        )
        self.vehicles = Category.objects.create(
            name="Store Pinned Vehicles",
            slug="store-pinned-vehicles-v112",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Pinned Seller Store",
            headline="Featured and pinned inventory.",
            description="A v112 store page for pinned listing tests.",
            location="Berlin",
        )

    def public_store_url(self):
        return reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})

    def create_listing(
        self,
        title,
        price="100.00",
        category=None,
        created_at=None,
        top_listing_priority=0,
        top_listing_until=None,
        featured_priority=0,
        featured_until=None,
        is_featured=False,
    ):
        listing = Listing.objects.create(
            title=title,
            description=f"{title} pinned listing test description.",
            price=Decimal(str(price)),
            category=category or self.furniture,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
            top_listing_priority=top_listing_priority,
            top_listing_until=top_listing_until,
            featured_priority=featured_priority,
            featured_until=featured_until,
            is_featured=is_featured,
        )
        if created_at is not None:
            Listing.objects.filter(pk=listing.pk).update(created_at=created_at)
            listing.refresh_from_db()
        return listing

    def assert_context_titles(self, response, key, expected_titles):
        self.assertEqual(
            [listing.title for listing in response.context[key]],
            expected_titles,
        )

    def test_active_priority_listing_appears_in_pinned_section_above_normal_grid(self):
        now = timezone.now()
        pinned = self.create_listing(
            "Pinned Premium Console",
            top_listing_priority=10,
            top_listing_until=now + timedelta(days=5),
            created_at=now - timedelta(days=3),
        )
        regular = self.create_listing(
            "Regular Store Shelf",
            created_at=now,
        )

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-pinned-listings-v112")
        self.assertContains(response, "Pinned by this seller")
        self.assert_context_titles(response, "pinned_store_listings", [pinned.title])
        self.assert_context_titles(response, "listings", [regular.title])

    def test_expired_priority_listing_is_not_pinned(self):
        now = timezone.now()
        expired = self.create_listing(
            "Expired Priority Console",
            top_listing_priority=99,
            top_listing_until=now - timedelta(days=1),
        )
        regular = self.create_listing("Regular Non Priority Console")

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "seller-store-pinned-listings-v112")
        self.assert_context_titles(response, "pinned_store_listings", [])
        listing_ids = [listing.pk for listing in response.context["listings"]]
        self.assertIn(expired.pk, listing_ids)
        self.assertIn(regular.pk, listing_ids)

    def test_pinned_section_only_appears_when_relevant(self):
        self.create_listing("Plain Store Listing")

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pinned by this seller")
        self.assert_context_titles(response, "pinned_store_listings", [])

    def test_featured_listing_can_be_pinned_and_is_removed_from_regular_grid(self):
        now = timezone.now()
        featured = self.create_listing(
            "Featured Store Cabinet",
            featured_priority=4,
            featured_until=now + timedelta(days=7),
            is_featured=True,
        )
        regular = self.create_listing("Regular Companion Cabinet")

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assert_context_titles(response, "pinned_store_listings", [featured.title])
        self.assert_context_titles(response, "listings", [regular.title])
        regular_grid_ids = [listing.pk for listing in response.context["listings"]]
        self.assertNotIn(featured.pk, regular_grid_ids)

    def test_filters_do_not_leak_irrelevant_pinned_listings(self):
        now = timezone.now()
        furniture_pinned = self.create_listing(
            "Filtered Pinned Furniture",
            category=self.furniture,
            top_listing_priority=5,
            top_listing_until=now + timedelta(days=5),
        )
        vehicle_pinned = self.create_listing(
            "Filtered Pinned Vehicle",
            category=self.vehicles,
            top_listing_priority=9,
            top_listing_until=now + timedelta(days=5),
        )

        response = self.client.get(
            self.public_store_url(),
            {
                "q": "Filtered Pinned",
                "category": self.furniture.slug,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assert_context_titles(response, "pinned_store_listings", [furniture_pinned.title])
        self.assertContains(response, furniture_pinned.title)
        self.assertNotContains(response, vehicle_pinned.title)

    def test_sorting_still_applies_to_regular_grid_after_pinned_section(self):
        now = timezone.now()
        pinned = self.create_listing(
            "Pinned Sort Header Item",
            price="999.00",
            top_listing_priority=10,
            top_listing_until=now + timedelta(days=5),
        )
        low = self.create_listing("Low Regular Price Item", price="10.00")
        high = self.create_listing("High Regular Price Item", price="500.00")

        response = self.client.get(
            self.public_store_url(),
            {"sort": "price_asc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assert_context_titles(response, "pinned_store_listings", [pinned.title])
        self.assert_context_titles(response, "listings", [low.title, high.title])

    def test_pagination_uses_regular_grid_and_preserves_filters_with_pinned_section(self):
        now = timezone.now()
        self.create_listing(
            "Paged Pinned Store Item",
            category=self.furniture,
            top_listing_priority=8,
            top_listing_until=now + timedelta(days=3),
        )
        for index in range(13):
            self.create_listing(
                f"Paged Regular Store Item {index:02d}",
                category=self.furniture,
                price=str(100 + index),
            )

        response = self.client.get(
            self.public_store_url(),
            {
                "q": "Paged",
                "category": self.furniture.slug,
                "sort": "price_desc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-pinned-listings-v112")
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, "q=Paged")
        self.assertContains(response, f"category={self.furniture.slug}")
        self.assertContains(response, "sort=price_desc")
