from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SellerStoreDirectorySavedSearchResultCountPreviewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="seller_store_count_preview_v126",
            email="seller-store-count-preview-v126@classifieds.local",
            password="StrongPass123!",
        )
        self.directory_url = reverse("accounts:seller_store_directory")
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.query_data = {
            "q": "no-such-store-v126",
            "location": "Nowhere",
        }

    def test_active_filter_state_shows_result_count_preview(self):
        self.client.force_login(self.user)

        response = self.client.get(self.directory_url, self.query_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SELLER_STORE_SAVED_SEARCH_RESULT_COUNT_PREVIEW_V126")
        self.assertContains(response, "seller-store-saved-search-count-v126")
        self.assertContains(response, "This search currently matches 0 seller stores.")
        self.assertContains(response, "Save this seller store search")

    def test_zero_match_state_keeps_saved_search_count_preview(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.directory_url,
            {
                "q": "zero-match-v126",
                "location": "NoCity",
                "sort": "newest",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-saved-search-count-v126")
        self.assertContains(response, "This search currently matches 0 seller stores.")
        self.assertContains(response, "Save seller store search")

    def test_already_saved_state_shows_same_result_count_preview(self):
        for querystring in (
            "q=no-such-store-v126&location=Nowhere",
            "location=Nowhere&q=no-such-store-v126",
        ):
            SavedSearch.objects.get_or_create(
                user=self.user,
                path=self.directory_url,
                querystring=querystring,
                defaults={
                    "name": "Saved no-match stores",
                    "query_params": {
                        "q": "no-such-store-v126",
                        "location": "Nowhere",
                    },
                },
            )

        self.client.force_login(self.user)
        response = self.client.get(self.directory_url, self.query_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-saved-search-saved-state-v125")
        self.assertContains(response, "Already saved")
        self.assertContains(response, "View saved searches")
        self.assertContains(response, self.saved_search_list_url)
        self.assertContains(response, "This search currently matches 0 seller stores.")
        self.assertNotContains(response, "Save seller store search</button>")
