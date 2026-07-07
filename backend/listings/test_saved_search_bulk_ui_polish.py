from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchBulkUiPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_bulk_ui_v131",
            email="saved-search-bulk-ui-v131@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_bulk_ui_other_v131",
            email="saved-search-bulk-ui-other-v131@classifieds.local",
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

    def test_saved_search_bulk_ui_renders_v131_polish_controls(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"q": "Oak", "type": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_BULK_UI_POLISH_V131")
        self.assertContains(response, "SAVED_SEARCH_BULK_UI_POLISH_V131_MOBILE")
        self.assertContains(response, "SAVED_SEARCH_BULK_UI_POLISH_V131_CONTROLS")
        self.assertContains(response, "SAVED_SEARCH_BULK_UI_POLISH_V131_SCRIPT")
        self.assertContains(response, "saved-search-bulk-action-v131")
        self.assertContains(response, 'class="saved-search-bulk-action-v130 saved-search-bulk-action-v131"')
        self.assertContains(response, 'id="saved-search-select-all-visible-v131"')
        self.assertContains(response, "Select all visible")
        self.assertContains(response, 'id="saved-search-selected-count-v131"')
        self.assertContains(response, 'aria-live="polite"')
        self.assertContains(response, "0 selected")
        self.assertContains(response, 'id="saved-search-bulk-delete-button-v131"')
        self.assertContains(response, "saved-search-bulk-delete-v131")
        self.assertContains(response, "disabled")
        self.assertContains(response, 'name="selected_saved_searches"')
        self.assertContains(response, 'form="saved-search-bulk-action-form-v130"')

    def test_v131_polish_preserves_v130_backend_bulk_delete_behavior(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all"

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

    def test_v131_script_targets_existing_v130_checkbox_contract(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'input[name="selected_saved_searches"][form="saved-search-bulk-action-form-v130"]',
        )
        self.assertContains(response, "updateBulkUi")
        self.assertContains(response, "is-active-v131")
        self.assertContains(response, "indeterminate")
        self.assertContains(response, 'selected + " selected"')

    def test_v131_keeps_previous_saved_search_ui_markers(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url, {"q": "Oak", "type": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_BULK_ACTIONS_V130")
        self.assertContains(response, "SAVED_SEARCH_BULK_ACTIONS_V130_CHECKBOX")
        self.assertContains(response, "SAVED_SEARCH_MANAGEMENT_UI_POLISH_V129")
        self.assertContains(response, "SAVED_SEARCH_TAB_COUNT_POLISH_V128")
        self.assertContains(response, "SAVED_SEARCH_TYPE_FILTER_TABS_V127")
        self.assertContains(response, f'action="{self.bulk_action_url}"')
        self.assertContains(response, 'value="/listings/saved-searches/?q=Oak&amp;type=all"')
