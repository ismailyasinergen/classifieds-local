from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, SavedSearch


class SavedSearchFoundationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="saved-search-buyer-v77@classifieds.local",
            username="saved_search_buyer_v77",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="saved-search-seller-v77@classifieds.local",
            username="saved_search_seller_v77",
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
        self.real_estate, _ = Category.objects.get_or_create(
            slug="real-estate",
            defaults={"name": "Real Estate"},
        )
        self.homes, _ = Category.objects.get_or_create(
            slug="homes-for-sale",
            defaults={"name": "Homes for Sale", "parent": self.real_estate},
        )

    def _listing(self, title, category, price, attributes):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal(price),
            category=category,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes,
        )

    def test_filtered_browse_shows_login_to_save_search_for_anonymous_user(self):
        self._listing(
            "V77 Anonymous Save Search Toyota",
            self.cars,
            "975000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "cars",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_FOUNDATION_V77")
        self.assertContains(response, "Log in to save this search")
        self.assertContains(response, "FILTER_UX_POLISH_V76")

    def test_logged_in_filtered_browse_shows_save_search_form(self):
        self.client.force_login(self.buyer)
        self._listing(
            "V77 Logged In Save Search Toyota",
            self.cars,
            "975000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "cars",
                "q": "Toyota",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save this search")
        self.assertContains(response, reverse("listings:saved_search_create"))
        self.assertContains(response, 'name="querystring"')
        self.assertContains(response, "V77 Logged In Save Search Toyota")

    def test_create_saved_search_sanitizes_querystring_and_deduplicates(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "Toyota under 1M",
                "querystring": (
                    "category=cars&q=Toyota&page=3&unsafe=1&min_price=900000"
                    "&attr_marka=Toyota&attr_yil_min=2019&attr_km_max=50000"
                ),
            },
        )

        self.assertEqual(SavedSearch.objects.filter(user=self.buyer).count(), 1)
        saved_search = SavedSearch.objects.get(user=self.buyer)

        self.assertEqual(saved_search.name, "Toyota under 1M")
        self.assertEqual(saved_search.query_params["category"], "cars")
        self.assertEqual(saved_search.query_params["q"], "Toyota")
        self.assertEqual(saved_search.query_params["min_price"], "900000")
        self.assertEqual(saved_search.query_params["attr_marka"], "Toyota")
        self.assertNotIn("unsafe", saved_search.query_params)
        self.assertNotIn("page", saved_search.query_params)

        redirect_query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(redirect_query["category"], ["cars"])
        self.assertEqual(redirect_query["q"], ["Toyota"])
        self.assertNotIn("unsafe", redirect_query)
        self.assertNotIn("page", redirect_query)

        self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "Toyota under 1M updated",
                "querystring": (
                    "category=cars&q=Toyota&min_price=900000"
                    "&attr_marka=Toyota&attr_yil_min=2019&attr_km_max=50000"
                ),
            },
        )

        self.assertEqual(SavedSearch.objects.filter(user=self.buyer).count(), 1)
        saved_search.refresh_from_db()
        self.assertEqual(saved_search.name, "Toyota under 1M updated")

    def test_saved_search_list_runs_and_deletes_saved_search(self):
        self.client.force_login(self.buyer)
        saved_search = SavedSearch.objects.create(
            user=self.buyer,
            name="Homes 100m2",
            path=reverse("listings:listing_list"),
            query_params={
                "category": "homes-for-sale",
                "attr_m2_brut_min": "100",
                "attr_m2_brut_max": "150",
            },
            querystring="category=homes-for-sale&attr_m2_brut_min=100&attr_m2_brut_max=150",
        )

        response = self.client.get(reverse("listings:saved_search_list"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_FOUNDATION_V77")
        self.assertContains(response, "Homes 100m2")
        self.assertIn("category=homes-for-sale", html)
        self.assertIn("attr_m2_brut_min=100", html)
        self.assertContains(response, "Run search")

        delete_response = self.client.post(
            reverse("listings:saved_search_delete", args=[saved_search.pk]),
        )

        self.assertRedirects(delete_response, reverse("listings:saved_search_list"))
        self.assertFalse(SavedSearch.objects.filter(pk=saved_search.pk).exists())

    def test_saved_search_delete_is_owner_scoped(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            email="saved-search-other-v77@classifieds.local",
            username="saved_search_other_v77",
            password="Testpass12345",
        )
        saved_search = SavedSearch.objects.create(
            user=other_user,
            name="Other search",
            path=reverse("listings:listing_list"),
            query_params={"category": "cars"},
            querystring="category=cars",
        )

        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:saved_search_delete", args=[saved_search.pk]),
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(SavedSearch.objects.filter(pk=saved_search.pk).exists())

    def test_existing_v75_numeric_filter_behavior_is_preserved(self):
        self.client.force_login(self.buyer)
        self._listing(
            "V77 Numeric Toyota Match",
            self.cars,
            "975000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )
        self._listing(
            "V77 Numeric Toyota Old",
            self.cars,
            "850000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2018", "km": "90000"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "cars",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V77 Numeric Toyota Match")
        self.assertNotContains(response, "V77 Numeric Toyota Old")
        self.assertContains(response, "Save this search")
