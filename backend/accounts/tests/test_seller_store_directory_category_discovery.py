from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectoryCategoryDiscoveryTests(TestCase):
    def setUp(self):
        self.directory_url = reverse("accounts:seller_store_directory")
        self.furniture = Category.objects.create(
            name="Directory Furniture V117",
            slug="directory-furniture-v117",
        )
        self.decor = Category.objects.create(
            name="Directory Decor V117",
            slug="directory-decor-v117",
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
            headline=f"{store_name} category discovery headline.",
            description=f"{store_name} category discovery description.",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} directory category discovery listing.",
                price=Decimal("125.00"),
                category=category,
                owner=user,
                location=location,
                status=listing_status,
            )

        return user, store

    def store_names(self, response):
        return [store.name for store in response.context["stores"]]

    def popular_category_names(self, response):
        return [
            category.name
            for category in response.context["popular_directory_categories"]
        ]

    def active_chip_labels(self, response):
        return [
            chip["label"]
            for chip in response.context["directory_active_chips"]
        ]

    def test_category_discovery_chips_render_with_active_store_counts(self):
        first_user, first_store = self.create_store_with_listings(
            "directory_category_first_v117",
            "Directory Category First Store",
            self.furniture,
            listing_count=2,
        )
        second_user, second_store = self.create_store_with_listings(
            "directory_category_second_v117",
            "Directory Category Second Store",
            self.furniture,
            listing_count=1,
        )
        decor_user, decor_store = self.create_store_with_listings(
            "directory_category_decor_v117",
            "Directory Category Decor Store",
            self.decor,
            listing_count=1,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-category-discovery-v117")
        self.assertContains(response, "Shop stores by category")
        self.assertContains(response, "Explore seller stores by the categories")
        self.assertContains(response, "seller-store-category-chip-v117")
        self.assertContains(response, "Directory Furniture V117")
        self.assertContains(response, "2 stores")
        self.assertContains(response, "Directory Decor V117")
        self.assertContains(response, "1 store")
        self.assertContains(response, f"category={self.furniture.slug}")
        self.assertEqual(response.context["directory_category_limit"], 8)
        self.assertEqual(
            self.popular_category_names(response)[:2],
            [self.furniture.name, self.decor.name],
        )

    def test_category_filter_limits_directory_to_matching_stores(self):
        furniture_user, furniture_store = self.create_store_with_listings(
            "directory_category_filter_furniture_v117",
            "Directory Category Filter Furniture Store",
            self.furniture,
            listing_count=2,
            verified=True,
        )
        decor_user, decor_store = self.create_store_with_listings(
            "directory_category_filter_decor_v117",
            "Directory Category Filter Decor Store",
            self.decor,
            listing_count=3,
            verified=True,
        )

        response = self.client.get(
            self.directory_url,
            {"category": self.furniture.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["selected_directory_category"],
            self.furniture,
        )
        self.assertEqual(self.store_names(response), [furniture_store.name])
        self.assertContains(response, furniture_store.name)
        self.assertNotContains(response, decor_store.name)
        self.assertContains(response, "Category:")
        self.assertContains(response, self.furniture.name)
        self.assertContains(response, "All categories")
        self.assertContains(response, "Clear all")
        self.assertNotContains(response, "Featured verified stores")
        self.assertIn("Category", self.active_chip_labels(response))

    def test_category_filter_includes_child_category_listings(self):
        vehicles = Category.objects.create(
            name="Directory Vehicles V117",
            slug="directory-vehicles-v117",
        )
        cars = Category.objects.create(
            name="Directory Cars V117",
            slug="directory-cars-v117",
            parent=vehicles,
        )
        car_user, car_store = self.create_store_with_listings(
            "directory_category_child_v117",
            "Directory Category Child Store",
            cars,
            listing_count=1,
        )
        decor_user, decor_store = self.create_store_with_listings(
            "directory_category_child_decor_v117",
            "Directory Category Child Decor Store",
            self.decor,
            listing_count=1,
        )

        response = self.client.get(
            self.directory_url,
            {"category": vehicles.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, car_store.name)
        self.assertNotContains(response, decor_store.name)
        self.assertEqual(self.store_names(response), [car_store.name])

    def test_category_filter_is_preserved_in_pagination_and_sort_urls(self):
        for index in range(13):
            self.create_store_with_listings(
                f"directory_category_paged_v117_{index}",
                f"Directory Category Paged Store {index:02d}",
                self.furniture,
                listing_count=2,
            )

        response = self.client.get(
            self.directory_url,
            {
                "category": self.furniture.slug,
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "page=2")
        self.assertContains(response, f"category={self.furniture.slug}")
        self.assertContains(response, "sort=name_az")
        self.assertEqual(
            response.context["selected_directory_category"],
            self.furniture,
        )

    def test_invalid_category_slug_is_ignored_and_not_preserved(self):
        for index in range(13):
            self.create_store_with_listings(
                f"directory_category_invalid_v117_{index}",
                f"Directory Category Invalid Store {index:02d}",
                self.furniture,
                listing_count=1,
            )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Directory Category Invalid",
                "category": "missing-category-v117",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["selected_directory_category"])
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "q=Directory+Category+Invalid")
        self.assertNotContains(response, "missing-category-v117")
        self.assertNotContains(response, "category=missing-category-v117")
        self.assertNotIn("Category", self.active_chip_labels(response))

    def test_category_discovery_is_hidden_when_no_active_store_categories_exist(self):
        self.create_store_with_listings(
            "directory_category_pending_v117",
            "Directory Category Pending Store",
            self.furniture,
            listing_status=Listing.Status.PENDING,
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["popular_directory_categories"], [])
        self.assertNotContains(response, "Shop stores by category")
        self.assertNotContains(response, 'aria-label="Popular store categories"')
