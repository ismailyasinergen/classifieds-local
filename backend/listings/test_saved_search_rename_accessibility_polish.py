from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchRenameAccessibilityPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_a11y_v135",
            email="saved-search-rename-a11y-v135@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_rename_a11y_other_v135",
            email="saved-search-rename-a11y-other-v135@classifieds.local",
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

    def test_v135_renders_accessible_labels_descriptions_and_focus_classes(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {"q": "Oak", "type": "all", "page": "1"},
        )

        self.assertEqual(response.status_code, 200)
        form_id = f"saved-search-rename-form-{self.saved_search.pk}-v134"
        helper_id = f"saved-search-rename-helper-{self.saved_search.pk}-v135"

        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135_TOGGLE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135_HELPER")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135_INPUT")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135_CANCEL")
        self.assertContains(response, "saved-search-rename-sr-v135")
        self.assertContains(response, "saved-search-rename-toggle-v134 saved-search-rename-toggle-v135")
        self.assertContains(response, "saved-search-rename-cancel-v134 saved-search-rename-cancel-v135")
        self.assertContains(response, "saved-search-rename-input-v132 saved-search-rename-input-v133 saved-search-rename-input-v135")
        self.assertContains(response, 'aria-label="Rename this saved search"')
        self.assertContains(response, 'aria-label="Cancel renaming this saved search"')
        self.assertContains(response, 'aria-label="Rename saved search form"')
        self.assertContains(response, f'aria-controls="{form_id}"')
        self.assertContains(response, f'id="{helper_id}"')
        self.assertContains(response, f'aria-describedby="{helper_id}"')
        self.assertContains(response, "Press Escape to cancel renaming and return focus to the Rename button.")

    def test_v135_script_supports_escape_cancel_reset_and_focus_restore(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_SCRIPT")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135_SCRIPT")
        self.assertContains(response, 'event.key !== "Escape"')
        self.assertContains(response, "data-rename-form-v134")
        self.assertContains(response, "getToggleForForm")
        self.assertContains(response, "focusRenameInput")
        self.assertContains(response, "restoreToggleFocus")
        self.assertContains(response, "form.reset()")
        self.assertContains(response, "button.focus()")
        self.assertContains(response, "restoreFocus: true")
        self.assertContains(response, "resetForm: true")
        self.assertContains(response, 'form.removeAttribute("hidden")')
        self.assertContains(response, 'form.setAttribute("hidden", "hidden")')

    def test_v135_preserves_v132_v133_v134_contracts_and_duplicate_name_guard(self):
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
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_TOGGLE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_CANCEL")
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_TOGGLE_V134_SCRIPT")
        self.assertContains(response, "Current name is shown above.")
        self.assertContains(response, "Type a new name only when you want to update this saved search.")
        self.assertContains(response, "Type a new name")
        self.assertContains(response, f'action="{self.rename_url}"')
        self.assertNotContains(response, 'value="Oak listing search"')
        self.assertEqual(html.count("Oak listing search"), 1)

    def test_v135_backend_rename_contract_is_unchanged(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "  Accessible   Rename   Flow  ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Accessible Rename Flow")

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
