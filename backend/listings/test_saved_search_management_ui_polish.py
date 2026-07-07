from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchManagementUiPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_management_ui_polish_v129",
            email="saved-search-management-ui-polish-v129@classifieds.local",
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
            name="Oak seller stores",
            path=self.seller_store_directory_url,
            querystring="q=oak",
            query_params={"q": "oak"},
        )

    def test_saved_search_page_renders_v129_polish_markers(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_MANAGEMENT_UI_POLISH_V129")
        self.assertContains(response, "SAVED_SEARCH_MANAGEMENT_UI_POLISH_V129_MOBILE")
        self.assertContains(response, "saved-search-page-v129")
        self.assertContains(response, "saved-search-header-v129")
        self.assertContains(response, "saved-search-type-tabs-v129")
        self.assertContains(response, "saved-search-management-bar-v129")
        self.assertContains(response, "saved-search-search-form-v129")
        self.assertContains(response, "saved-search-counts-v129")
        self.assertContains(response, "saved-search-grid-v129")
        self.assertContains(response, "saved-search-card-v129")
        self.assertContains(response, "saved-search-actions-v129")

    def test_v129_polish_keeps_v127_and_v128_saved_search_behavior(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"q": "Oak", "type": "seller-stores"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_TYPE_FILTER_TABS_V127")
        self.assertContains(response, "SAVED_SEARCH_TAB_COUNT_POLISH_V128")
        self.assertContains(response, "saved-search-active-filter-summary-v128")
        self.assertContains(response, "saved-search-active-filter-summary-v129")
        self.assertContains(response, "saved-search-tab-count-note-v128")
        self.assertContains(response, "saved-search-tab-count-note-v129")
        self.assertContains(response, "Search:")
        self.assertContains(response, "Oak")
        self.assertContains(response, "Type:")
        self.assertContains(response, "Seller store searches")
        self.assertContains(response, "Tab counts are narrowed by")
        self.assertContains(response, "Oak seller stores")
        self.assertNotContains(response, "Oak listing search")

    def test_empty_saved_search_page_keeps_polished_empty_state(self):
        User = get_user_model()
        empty_user = User.objects.create_user(
            username="saved_search_management_ui_polish_empty_v129",
            email="saved-search-management-ui-polish-empty-v129@classifieds.local",
            password="StrongPass123!",
        )
        self.client.force_login(empty_user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "saved-search-empty-v129")
        self.assertContains(response, "Saved Searches")
        self.assertContains(response, "Browse listings")
        self.assertContains(response, "Browse seller stores")
        self.assertNotContains(response, "Tab counts are narrowed by")
