from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, SavedSearch


class SavedSearchUxPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="saved-search-ux-buyer-v78@classifieds.local",
            username="saved_search_ux_buyer_v78",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="saved-search-ux-seller-v78@classifieds.local",
            username="saved_search_ux_seller_v78",
            password="Testpass12345",
        )

        self.vehicles, _ = Category.objects.get_or_create(
            slug="vehicles",
            defaults={"name": "Vehicles"},
        )
        self.cars, _ = Category.objects.get_or_create(
            slug="cars",
            defaults={"name": "Cars", "parent": self.vehicles},
        )

    def _listing(self, title="V78 Toyota"):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal("975000.00"),
            category=self.cars,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes={
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
            },
        )

    def test_saved_search_list_shows_readable_filter_chips(self):
        self.client.force_login(self.buyer)
        saved_search = SavedSearch.objects.create(
            user=self.buyer,
            name="Toyota under 1M",
            path=reverse("listings:listing_list"),
            query_params={
                "category": "cars",
                "q": "Toyota",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
            querystring=(
                "category=cars&q=Toyota&min_price=900000&max_price=1000000"
                "&attr_marka=Toyota&attr_yil_min=2019&attr_km_max=50000"
            ),
        )

        response = self.client.get(reverse("listings:saved_search_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_UX_POLISH_V78")
        self.assertContains(response, "Toyota under 1M")
        self.assertContains(response, "Category:")
        self.assertContains(response, "Cars")
        self.assertContains(response, "Search:")
        self.assertContains(response, "Toyota")
        self.assertContains(response, "Price:")
        self.assertContains(response, "900000")
        self.assertContains(response, "1000000")
        self.assertContains(response, "Brand:")
        self.assertContains(response, "Year:")
        self.assertContains(response, "KM:")
        self.assertContains(response, f"{saved_search.filter_count} saved filters")
        self.assertContains(response, "Run search")
        self.assertContains(response, "Remove saved search")
        self.assertContains(response, "/listings/?")
        self.assertContains(response, "category=cars")
        self.assertContains(response, "q=Toyota")
        self.assertContains(response, "min_price=900000")
        self.assertContains(response, "max_price=1000000")
        self.assertContains(response, "attr_marka=Toyota")
        self.assertContains(response, "attr_yil_min=2019")
        self.assertContains(response, "attr_km_max=50000")

    def test_already_saved_browse_state_is_clearer(self):
        self.client.force_login(self.buyer)
        self._listing("V78 Saved Browse Toyota")
        SavedSearch.objects.create(
            user=self.buyer,
            name="Saved Toyota browse",
            path=reverse("listings:listing_list"),
            query_params={"category": "cars", "attr_marka": "Toyota"},
            querystring="category=cars&attr_marka=Toyota",
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars", "attr_marka": "Toyota"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_UX_POLISH_V78")
        self.assertContains(response, "Already saved")
        self.assertContains(response, "Saved Toyota browse")
        self.assertContains(response, "View saved searches")
        self.assertContains(response, "V78 Saved Browse Toyota")
        self.assertNotContains(response, "Optional search name")

    def test_empty_saved_search_page_uses_polished_empty_state(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("listings:saved_search_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_UX_POLISH_V78")
        self.assertContains(response, "No saved searches yet")
        self.assertContains(response, "Start browsing")
        self.assertContains(response, "saved-search-empty-v78")

    def test_unnamed_saved_search_has_readable_summary_sentence(self):
        self.client.force_login(self.buyer)
        SavedSearch.objects.create(
            user=self.buyer,
            path=reverse("listings:listing_list"),
            query_params={
                "category": "cars",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
            },
            querystring="category=cars&attr_marka=Toyota&attr_yil_min=2019",
        )

        response = self.client.get(reverse("listings:saved_search_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cars")
        self.assertContains(response, "Brand: Toyota")
        self.assertContains(response, "Year: Min 2019")
        self.assertContains(response, "3 saved filters")
