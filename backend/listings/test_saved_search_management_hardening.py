from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import SavedSearch


class SavedSearchManagementHardeningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="saved-search-management-buyer-v79@classifieds.local",
            username="saved_search_management_buyer_v79",
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

    def _saved_search(self, name, querystring):
        params = {}
        for pair in querystring.split("&"):
            key, value = pair.split("=", 1)
            params[key] = value

        return SavedSearch.objects.create(
            user=self.buyer,
            name=name,
            path=reverse("listings:listing_list"),
            query_params=params,
            querystring=querystring,
        )

    def test_saved_search_list_is_searchable_and_paginated(self):
        self.client.force_login(self.buyer)

        for index in range(1, 9):
            self._saved_search(
                f"V79 Paginated Toyota {index:02d}",
                f"category=cars&q=Toyota&attr_marka=Toyota&attr_yil_min={2010 + index}",
            )

        response = self.client.get(reverse("listings:saved_search_list"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_MANAGEMENT_HARDENING_V79")
        self.assertContains(response, "Search saved searches")
        self.assertContains(response, 'name="q"')
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "Next page")
        self.assertContains(response, "6 per page")
        self.assertEqual(html.count("V79 Paginated Toyota"), 6)

        second_page = self.client.get(reverse("listings:saved_search_list"), {"page": "2"})
        second_html = second_page.content.decode()
        self.assertEqual(second_page.status_code, 200)
        self.assertContains(second_page, "Previous page")
        self.assertEqual(second_html.count("V79 Paginated Toyota"), 2)

    def test_saved_search_list_filters_by_name_and_preserves_query(self):
        self.client.force_login(self.buyer)
        self._saved_search(
            "V79 Toyota target",
            "category=cars&q=Toyota&attr_marka=Toyota",
        )
        self._saved_search(
            "V79 Honda hidden",
            "category=cars&q=Honda&attr_marka=Honda",
        )

        response = self.client.get(reverse("listings:saved_search_list"), {"q": "Toyota target"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V79 Toyota target")
        self.assertNotContains(response, "V79 Honda hidden")
        self.assertContains(response, "1 shown")
        self.assertContains(response, "2 total")
        self.assertContains(response, "Clear search")

    def test_reordered_duplicate_querystring_updates_existing_saved_search(self):
        self.client.force_login(self.buyer)

        first = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "V79 canonical original",
                "querystring": "q=Toyota&category=cars&attr_marka=Toyota",
            },
        )
        second = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "V79 canonical updated",
                "querystring": "attr_marka=Toyota&category=cars&q=Toyota",
            },
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)

        saved_searches = SavedSearch.objects.filter(user=self.buyer)
        self.assertEqual(saved_searches.count(), 1)

        saved_search = saved_searches.get()
        self.assertEqual(saved_search.name, "V79 canonical updated")
        self.assertEqual(saved_search.querystring, "attr_marka=Toyota&category=cars&q=Toyota")

        browse = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars", "q": "Toyota", "attr_marka": "Toyota"},
        )

        self.assertEqual(browse.status_code, 200)
        self.assertContains(browse, "Already saved")
        self.assertContains(browse, "V79 canonical updated")

    def test_saved_search_list_empty_search_result_has_management_empty_state(self):
        self.client.force_login(self.buyer)
        self._saved_search(
            "V79 Toyota target",
            "category=cars&q=Toyota&attr_marka=Toyota",
        )

        response = self.client.get(reverse("listings:saved_search_list"), {"q": "No match"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No saved searches match")
        self.assertContains(response, "Clear search")
        self.assertContains(response, "0 shown")
        self.assertContains(response, "1 total")
