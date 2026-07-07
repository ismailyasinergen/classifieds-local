from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchTypeFilterTabsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_type_tabs_v127",
            email="saved-search-type-tabs-v127@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.seller_store_directory_url = reverse("accounts:seller_store_directory")

        self.listing_search = SavedSearch.objects.create(
            user=self.user,
            name="Oak listing search",
            path="/listings/",
            querystring="q=oak",
            query_params={"q": "oak"},
        )
        self.second_listing_search = SavedSearch.objects.create(
            user=self.user,
            name="Walnut listing search",
            path="/listings/",
            querystring="q=walnut",
            query_params={"q": "walnut"},
        )
        self.store_search = SavedSearch.objects.create(
            user=self.user,
            name="Berlin seller stores",
            path=self.seller_store_directory_url,
            querystring="q=Berlin",
            query_params={"q": "Berlin"},
        )

    def test_saved_search_list_renders_type_tabs_with_counts_and_labels(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_TYPE_FILTER_TABS_V127")
        self.assertContains(response, "saved-search-type-tabs-v127")
        self.assertContains(response, "All")
        self.assertContains(response, "Listing searches")
        self.assertContains(response, "Seller store searches")
        self.assertContains(response, "saved-search-type-tab-count-v127")
        self.assertContains(response, "Oak listing search")
        self.assertContains(response, "Walnut listing search")
        self.assertContains(response, "Berlin seller stores")

    def test_listing_type_tab_filters_out_seller_store_searches(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"type": "listings"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oak listing search")
        self.assertContains(response, "Walnut listing search")
        self.assertNotContains(response, "Berlin seller stores")
        self.assertContains(response, "Listing searches")
        self.assertContains(response, 'aria-current="page"')

    def test_seller_store_type_tab_filters_out_listing_searches(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"type": "seller-stores"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Berlin seller stores")
        self.assertNotContains(response, "Oak listing search")
        self.assertNotContains(response, "Walnut listing search")
        self.assertContains(response, "Seller store searches")
        # Seller-store saved searches should keep the v124 guardrail note,
        # but must not render listing email-alert toggle controls.
        self.assertContains(response, "Email alerts are available for listing searches only")
        self.assertNotContains(response, "Email me when new listings match")
        self.assertNotContains(response, "Disable email alerts")

    def test_type_tabs_preserve_search_query_when_switching_types(self):
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
        self.assertNotContains(response, "Oak listing search")
        self.assertContains(response, "q=Berlin")
        self.assertContains(response, "type=listings")
        self.assertContains(response, "type=seller-stores")

    def test_type_specific_empty_state_is_clear(self):
        User = get_user_model()
        listing_only_user = User.objects.create_user(
            username="saved_search_type_tabs_listing_only_v127",
            email="saved-search-type-tabs-listing-only-v127@classifieds.local",
            password="StrongPass123!",
        )
        SavedSearch.objects.create(
            user=listing_only_user,
            name="Only listing search",
            path="/listings/",
            querystring="q=chair",
            query_params={"q": "chair"},
        )

        self.client.force_login(listing_only_user)
        response = self.client.get(self.saved_search_list_url, {"type": "seller-stores"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No seller store searches saved yet")
        self.assertContains(response, "Save a seller store directory search")
        self.assertNotContains(response, "Only listing search")

    def test_v127_tabs_keep_legacy_management_counts_and_query_context(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"q": "Oak"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Oak"')
        self.assertContains(response, "1 shown")
        self.assertContains(response, "3 total")
        self.assertContains(response, "6 per page")
        self.assertContains(response, "0 email alerts on")
        self.assertContains(response, "saved-search-type-tabs-v127")

