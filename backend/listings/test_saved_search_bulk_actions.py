from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchBulkActionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_bulk_actions_v130",
            email="saved-search-bulk-actions-v130@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_bulk_actions_other_v130",
            email="saved-search-bulk-actions-other-v130@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.bulk_action_url = reverse("listings:saved_search_bulk_action")
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
        self.seller_store_search = SavedSearch.objects.create(
            user=self.user,
            name="Oak seller stores",
            path=self.seller_store_directory_url,
            querystring="q=oak",
            query_params={"q": "oak"},
        )
        self.other_user_search = SavedSearch.objects.create(
            user=self.other_user,
            name="Other user private search",
            path="/listings/",
            querystring="q=private",
            query_params={"q": "private"},
        )

    def test_saved_search_list_renders_bulk_action_ui(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"q": "Oak", "type": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_BULK_ACTIONS_V130")
        self.assertContains(response, "SAVED_SEARCH_BULK_ACTIONS_V130_MOBILE")
        self.assertContains(response, 'id="saved-search-bulk-action-form-v130"')
        self.assertContains(response, f'action="{self.bulk_action_url}"')
        self.assertContains(response, 'name="bulk_action"')
        self.assertContains(response, 'name="next"')
        self.assertContains(response, 'name="selected_saved_searches"')
        self.assertContains(response, 'form="saved-search-bulk-action-form-v130"')
        self.assertContains(response, "Delete selected")
        self.assertContains(response, "saved-search-bulk-select-v130")
        self.assertContains(response, "SAVED_SEARCH_MANAGEMENT_UI_POLISH_V129")
        self.assertContains(response, "SAVED_SEARCH_TAB_COUNT_POLISH_V128")
        self.assertContains(response, "SAVED_SEARCH_TYPE_FILTER_TABS_V127")

    def test_bulk_delete_deletes_selected_owner_searches_only_and_preserves_next_url(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=seller-stores&page=2"

        response = self.client.post(
            self.bulk_action_url,
            {
                "bulk_action": "delete",
                "selected_saved_searches": [
                    str(self.listing_search.pk),
                    str(self.seller_store_search.pk),
                    str(self.other_user_search.pk),
                ],
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertFalse(SavedSearch.objects.filter(pk=self.listing_search.pk).exists())
        self.assertFalse(SavedSearch.objects.filter(pk=self.seller_store_search.pk).exists())
        self.assertTrue(SavedSearch.objects.filter(pk=self.second_listing_search.pk).exists())
        self.assertTrue(SavedSearch.objects.filter(pk=self.other_user_search.pk).exists())

    def test_bulk_delete_without_selection_keeps_searches_and_redirects(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.bulk_action_url,
            {
                "bulk_action": "delete",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.saved_search_list_url)
        self.assertTrue(SavedSearch.objects.filter(pk=self.listing_search.pk).exists())
        self.assertTrue(SavedSearch.objects.filter(pk=self.second_listing_search.pk).exists())
        self.assertTrue(SavedSearch.objects.filter(pk=self.seller_store_search.pk).exists())
        self.assertTrue(SavedSearch.objects.filter(pk=self.other_user_search.pk).exists())

    def test_bulk_action_rejects_unsafe_next_url(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.bulk_action_url,
            {
                "bulk_action": "delete",
                "selected_saved_searches": [str(self.listing_search.pk)],
                "next": "https://evil.example/phish",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.saved_search_list_url)
        self.assertFalse(SavedSearch.objects.filter(pk=self.listing_search.pk).exists())
        self.assertTrue(SavedSearch.objects.filter(pk=self.other_user_search.pk).exists())

    def test_bulk_action_requires_login(self):
        response = self.client.post(
            self.bulk_action_url,
            {
                "bulk_action": "delete",
                "selected_saved_searches": [str(self.listing_search.pk)],
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertTrue(SavedSearch.objects.filter(pk=self.listing_search.pk).exists())
