from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchRenameUxPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_ux_v133",
            email="saved-search-rename-ux-v133@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_rename_ux_other_v133",
            email="saved-search-rename-ux-other-v133@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")

        self.saved_search = SavedSearch.objects.create(
            user=self.user,
            name="Oak listing search",
            path="/listings/",
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
        self.rename_url = reverse(
            "listings:saved_search_rename",
            kwargs={"pk": self.saved_search.pk},
        )

    def test_v133_rename_form_renders_polished_helper_and_mobile_hooks(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {"q": "Oak", "type": "all", "page": "1"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertContains(response, "SAVED_SEARCH_RENAME_UX_POLISH_V133")
        self.assertContains(response, "SAVED_SEARCH_RENAME_UX_POLISH_V133_MOBILE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_UX_POLISH_V133_HELPER")
        self.assertContains(response, "saved-search-rename-form-v132 saved-search-rename-form-v133")
        self.assertContains(response, "saved-search-rename-row-v132 saved-search-rename-row-v133")
        self.assertContains(response, "saved-search-rename-input-v132 saved-search-rename-input-v133")
        self.assertContains(response, "saved-search-rename-submit-v132 saved-search-rename-submit-v133")
        self.assertContains(response, "Current name is shown above.")
        self.assertContains(response, "Type a new name only when you want to update this saved search.")
        self.assertContains(response, "Type a new name")
        self.assertContains(response, f'action="{self.rename_url}"')
        self.assertContains(response, f'id="saved-search-name-{self.saved_search.pk}-v132"')

        # Preserve v132 duplicate-name guard so old pagination/search count tests stay stable.
        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132_NO_DUPLICATE_NAME")
        self.assertNotContains(response, 'value="Oak listing search"')
        self.assertEqual(html.count("Oak listing search"), 1)

    def test_v133_success_message_is_recorded_for_valid_rename(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "  Polished   Oak   Rename  ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Polished Oak Rename")

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn("Saved search name updated.", messages)

    def test_v133_blank_name_error_message_is_recorded_and_name_is_kept(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all"

        response = self.client.post(
            self.rename_url,
            {
                "name": "       ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Oak listing search")

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn("Saved search name cannot be blank.", messages)

    def test_v133_owner_scope_and_safe_next_still_match_v132_backend_contract(self):
        self.client.force_login(self.user)

        other_rename_url = reverse(
            "listings:saved_search_rename",
            kwargs={"pk": self.other_user_search.pk},
        )
        owner_scope_response = self.client.post(
            other_rename_url,
            {
                "name": "Should not rename",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(owner_scope_response.status_code, 404)

        self.other_user_search.refresh_from_db()
        self.assertEqual(self.other_user_search.name, "Other user private search")

        safe_next_response = self.client.post(
            self.rename_url,
            {
                "name": "Safe Next Guard",
                "next": "https://evil.example/phish",
            },
        )

        self.assertEqual(safe_next_response.status_code, 302)
        self.assertEqual(safe_next_response["Location"], self.saved_search_list_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Safe Next Guard")
