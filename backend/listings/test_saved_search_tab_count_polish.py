from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchTabCountPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_tab_count_polish_v128",
            email="saved-search-tab-count-polish-v128@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.seller_store_directory_url = reverse("accounts:seller_store_directory")

        SavedSearch.objects.create(
            user=self.user,
            name="Oak listing search",
            path="/listings/",
            querystring="q=oak",
            query_params={"q": "oak"},
        )
        SavedSearch.objects.create(
            user=self.user,
            name="Walnut listing search",
            path="/listings/",
            querystring="q=walnut",
            query_params={"q": "walnut"},
        )
        SavedSearch.objects.create(
            user=self.user,
            name="Oak seller stores",
            path=self.seller_store_directory_url,
            querystring="q=oak",
            query_params={"q": "oak"},
        )
        SavedSearch.objects.create(
            user=self.user,
            name="Berlin seller stores",
            path=self.seller_store_directory_url,
            querystring="q=Berlin",
            query_params={"q": "Berlin"},
        )

    def test_tab_counts_follow_active_search_query(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"q": "Oak"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_TAB_COUNT_POLISH_V128")
        self.assertContains(response, "saved-search-active-filter-summary-v128")
        self.assertContains(response, "Tab counts are narrowed by")
        self.assertContains(response, "Clear the search to see all saved-search totals")
        self.assertContains(response, "<span>All</span>", html=True)
        self.assertContains(response, '<span class="saved-search-type-tab-count-v127">2</span>', html=True)
        self.assertContains(response, "<span>Listing searches</span>", html=True)
        self.assertContains(response, "<span>Seller store searches</span>", html=True)
        self.assertContains(response, "2 shown")
        self.assertContains(response, "4 total")
        self.assertNotContains(response, "Walnut listing search")
        self.assertNotContains(response, "Berlin seller stores")

    def test_type_tab_counts_are_query_aware_and_preserve_urls(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {
                "q": "Berlin",
                "type": "seller-stores",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Berlin seller stores")
        self.assertNotContains(response, "Oak seller stores")
        self.assertContains(response, "Search:")
        self.assertContains(response, "Berlin")
        self.assertContains(response, "Type:")
        self.assertContains(response, "Seller store searches")
        self.assertContains(response, "q=Berlin")
        self.assertContains(response, "type=listings")
        self.assertContains(response, "type=seller-stores")
        self.assertContains(response, "<span>1 shown</span>", html=True)
        self.assertContains(response, "<span>4 total</span>", html=True)

    def test_query_aware_counts_support_zero_match_type_empty_state(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {
                "q": "Walnut",
                "type": "seller-stores",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No seller store searches saved yet")
        self.assertContains(response, "No seller store saved searches match this keyword")
        self.assertContains(response, "Tab counts are narrowed by")
        self.assertContains(response, "type=listings")
        self.assertContains(response, "Walnut")
        self.assertNotContains(response, "Walnut listing search")
        self.assertNotContains(response, "Oak seller stores")

    def test_default_tab_counts_remain_global_without_search_query(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4 shown")
        self.assertContains(response, "4 total")
        self.assertNotContains(response, "Tab counts are narrowed by")
        self.assertContains(response, "Oak listing search")
        self.assertContains(response, "Walnut listing search")
        self.assertContains(response, "Oak seller stores")
        self.assertContains(response, "Berlin seller stores")
