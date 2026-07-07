from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchRenameInlineToggleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_toggle_v134",
            email="saved-search-rename-toggle-v134@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_rename_toggle_other_v134",
            email="saved-search-rename-toggle-other-v134@classifieds.local",
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

    def test_v134_rename_form_is_hidden_by_default_with_toggle_and_cancel_controls(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {"q": "Oak", "type": "all", "page": "1"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        form_id = f"saved-search-rename-form-{self.saved_search.pk}-v134"

        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134")
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_MOBILE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_TOGGLE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_CANCEL")
        self.assertContains(response, "saved-search-rename-toggle-bar-v134")
        self.assertContains(response, "saved-search-rename-toggle-v134")
        self.assertContains(response, "saved-search-rename-form-v132 saved-search-rename-form-v133 saved-search-rename-form-v134")
        self.assertContains(response, "saved-search-rename-row-v132 saved-search-rename-row-v133 saved-search-rename-row-v134")
        self.assertContains(response, "saved-search-rename-cancel-v134")
        self.assertContains(response, "Rename")
        self.assertContains(response, "Cancel")
        self.assertContains(response, f'aria-controls="{form_id}"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, f'data-rename-toggle-v134="{form_id}"')
        self.assertContains(response, f'data-rename-cancel-v134="{form_id}"')
        self.assertContains(response, f'id="{form_id}"')
        self.assertIn(f'id="{form_id}"\n                        hidden', html)

    def test_v134_progressive_enhancement_script_targets_toggle_and_cancel_contract(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_SCRIPT")
        self.assertContains(response, "data-rename-toggle-v134")
        self.assertContains(response, "data-rename-cancel-v134")
        self.assertContains(response, "aria-expanded")
        self.assertContains(response, 'form.removeAttribute("hidden")')
        self.assertContains(response, 'form.setAttribute("hidden", "hidden")')
        self.assertContains(response, ".saved-search-rename-input-v132")

    def test_v134_preserves_v132_v133_content_and_duplicate_name_guard(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {"q": "Oak", "type": "all", "page": "1"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132")
        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132_NO_DUPLICATE_NAME")
        self.assertContains(response, "SAVED_SEARCH_RENAME_UX_POLISH_V133_HELPER")
        self.assertContains(response, "Current name is shown above.")
        self.assertContains(response, "Type a new name only when you want to update this saved search.")
        self.assertContains(response, "Type a new name")
        self.assertContains(response, f'action="{self.rename_url}"')
        self.assertNotContains(response, 'value="Oak listing search"')
        self.assertEqual(html.count("Oak listing search"), 1)

    def test_v134_backend_rename_contract_is_unchanged(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "  Inline   Toggle   Rename  ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Inline Toggle Rename")

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
