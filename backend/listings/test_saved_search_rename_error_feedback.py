from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchRenameErrorFeedbackTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_error_v137",
            email="saved-search-rename-error-v137@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_rename_error_other_v137",
            email="saved-search-rename-error-other-v137@classifieds.local",
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

    def test_v137_blank_rename_sets_error_session_and_preserves_existing_name_and_redirect(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "     ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Oak listing search")
        self.assertEqual(
            self.client.session.get("saved_search_rename_error_id_v137"),
            self.saved_search.pk,
        )
        self.assertEqual(
            self.client.session.get("saved_search_rename_error_message_v137"),
            "Type a new name before saving this saved search.",
        )
        self.assertIsNone(self.client.session.get("saved_search_renamed_id_v136"))

    def test_v137_saved_search_list_reopens_failed_rename_form_and_clears_error_session(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["saved_search_rename_error_id_v137"] = self.saved_search.pk
        session["saved_search_rename_error_message_v137"] = "Type a new name before saving this saved search."
        session.save()

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            getattr(response.wsgi_request, "saved_search_rename_error_id_v137", None),
            self.saved_search.pk,
        )
        self.assertEqual(
            getattr(response.wsgi_request, "saved_search_rename_error_message_v137", None),
            "Type a new name before saving this saved search.",
        )

        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_TOGGLE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_REOPEN")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_CARD")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_INPUT")
        self.assertContains(response, "saved-search-rename-error-v137")
        self.assertContains(response, "saved-search-rename-form-error-v137")
        self.assertContains(response, "Rename was not saved")
        self.assertContains(response, "Type a new name before saving this saved search.")
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'aria-live="assertive"')
        self.assertContains(response, 'aria-expanded="true"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(
            response,
            f'aria-describedby="saved-search-rename-helper-{self.saved_search.pk}-v135 saved-search-rename-error-{self.saved_search.pk}-v137"',
        )

        self.assertNotIn("saved_search_rename_error_id_v137", self.client.session)
        self.assertNotIn("saved_search_rename_error_message_v137", self.client.session)

    def test_v137_normal_saved_search_list_keeps_rename_form_hidden_by_default(self):
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        form_id = f"saved-search-rename-form-{self.saved_search.pk}-v134"

        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137")
        self.assertNotContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_CARD")
        self.assertNotContains(response, "Rename was not saved")
        self.assertContains(response, f'aria-controls="{form_id}"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, 'aria-invalid="false"')
        self.assertContains(response, "hidden")

    def test_v137_successful_rename_still_uses_v136_success_feedback_session_only(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "  Valid   Rename  ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Valid Rename")
        self.assertEqual(
            self.client.session.get("saved_search_renamed_id_v136"),
            self.saved_search.pk,
        )
        self.assertIsNone(self.client.session.get("saved_search_rename_error_id_v137"))
        self.assertIsNone(self.client.session.get("saved_search_rename_error_message_v137"))

    def test_v137_preserves_v132_to_v136_contracts_and_duplicate_name_guard(self):
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
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ACCESSIBILITY_POLISH_V135_SCRIPT")
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136")
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_FORM")
        self.assertContains(response, "aria-label=\"Rename this saved search\"")
        self.assertContains(response, "Press Escape to cancel renaming")
        self.assertContains(response, f'action="{self.rename_url}"')
        self.assertNotContains(response, 'value="Oak listing search"')
        self.assertEqual(html.count("Oak listing search"), 1)

    def test_v137_owner_scope_still_blocks_foreign_rename_without_error_feedback_session(self):
        self.client.force_login(self.user)

        other_rename_url = reverse(
            "listings:saved_search_rename",
            kwargs={"pk": self.other_user_search.pk},
        )
        response = self.client.post(
            other_rename_url,
            {
                "name": "     ",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.other_user_search.refresh_from_db()
        self.assertEqual(self.other_user_search.name, "Other user private search")
        self.assertIsNone(self.client.session.get("saved_search_rename_error_id_v137"))
        self.assertIsNone(self.client.session.get("saved_search_rename_error_message_v137"))
