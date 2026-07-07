from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchSellerStoreManagementPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_store_management_v123",
            email="saved-search-store-management-v123@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.listing_browse_url = reverse("listings:listing_list")
        self.store_directory_url = reverse("accounts:seller_store_directory")

    def test_saved_search_model_exposes_source_and_run_labels(self):
        listing_search = SavedSearch.objects.create(
            user=self.user,
            name="Desk listings",
            path=self.listing_browse_url,
            query_params={"q": "Desk"},
            querystring="q=Desk",
        )
        store_search = SavedSearch.objects.create(
            user=self.user,
            name="Berlin seller stores",
            path=self.store_directory_url,
            query_params={"location": "Berlin", "verified_only": "1"},
            querystring="location=Berlin&verified_only=1",
        )

        self.assertFalse(listing_search.is_seller_store_directory_search)
        self.assertEqual(listing_search.search_source_label, "Listings")
        self.assertEqual(listing_search.search_source_css_class, "is-listing")
        self.assertEqual(listing_search.run_action_label, "Run search")

        self.assertTrue(store_search.is_seller_store_directory_search)
        self.assertEqual(store_search.search_source_label, "Seller stores")
        self.assertEqual(store_search.search_source_css_class, "is-seller-store")
        self.assertEqual(store_search.run_action_label, "Run store search")

    def test_saved_search_list_labels_listing_and_seller_store_searches(self):
        SavedSearch.objects.create(
            user=self.user,
            name="Desk listings",
            path=self.listing_browse_url,
            query_params={"q": "Desk"},
            querystring="q=Desk",
        )
        SavedSearch.objects.create(
            user=self.user,
            name="Berlin seller stores",
            path=self.store_directory_url,
            query_params={"location": "Berlin", "verified_only": "1"},
            querystring="location=Berlin&verified_only=1",
        )
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SELLER_STORE_SAVED_SEARCH_MANAGEMENT_POLISH_V123")
        self.assertContains(response, "saved-search-source-badge-v123")
        self.assertContains(response, "Listings")
        self.assertContains(response, "Seller stores")
        self.assertContains(response, "Run search")
        self.assertContains(response, "Run store search")
        self.assertContains(response, f"{self.listing_browse_url}?q=Desk")
        self.assertContains(
            response,
            f"{self.store_directory_url}?location=Berlin&amp;verified_only=1",
        )

    def test_saved_search_empty_state_mentions_listing_and_store_searches(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "saved listing searches and seller store searches",
        )
        self.assertContains(
            response,
            "listings browse page or seller store directory",
        )
        self.assertContains(response, "Start browsing listings")
        self.assertContains(response, "Browse seller stores")
        self.assertContains(response, self.listing_browse_url)
        self.assertContains(response, self.store_directory_url)
