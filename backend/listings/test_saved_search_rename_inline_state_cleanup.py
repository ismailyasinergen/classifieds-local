from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from listings.models import SavedSearch
from listings.templatetags.saved_search_state_v138 import (
    DEFAULT_RENAME_ERROR_MESSAGE_V138,
    saved_search_rename_state_v138,
)


class SavedSearchRenameInlineStateCleanupTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_state_v138",
            email="saved-search-rename-state-v138@classifieds.local",
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
        self.other_saved_search = SavedSearch.objects.create(
            user=self.user,
            name="Walnut listing search",
            path="/listings/",
            querystring="q=walnut",
            query_params={"q": "walnut"},
        )
        self.rename_url = reverse(
            "listings:saved_search_rename",
            kwargs={"pk": self.saved_search.pk},
        )

    def test_v138_template_helper_returns_normal_success_and_error_state(self):
        request = RequestFactory().get(self.saved_search_list_url)

        normal_state = saved_search_rename_state_v138(request, self.saved_search)
        self.assertFalse(normal_state["has_error"])
        self.assertFalse(normal_state["was_renamed"])
        self.assertEqual(normal_state["aria_expanded"], "false")
        self.assertEqual(normal_state["aria_invalid"], "false")
        self.assertEqual(
            normal_state["input_describedby"],
            f"saved-search-rename-helper-{self.saved_search.pk}-v135",
        )
        self.assertEqual(normal_state["error_message"], DEFAULT_RENAME_ERROR_MESSAGE_V138)

        request.renamed_saved_search_id_v136 = self.saved_search.pk
        success_state = saved_search_rename_state_v138(request, self.saved_search)
        self.assertTrue(success_state["was_renamed"])
        self.assertFalse(success_state["has_error"])

        request.saved_search_rename_error_id_v137 = self.saved_search.pk
        request.saved_search_rename_error_message_v137 = "Custom rename error"
        error_state = saved_search_rename_state_v138(request, self.saved_search)
        self.assertTrue(error_state["has_error"])
        self.assertEqual(error_state["aria_expanded"], "true")
        self.assertEqual(error_state["aria_invalid"], "true")
        self.assertEqual(
            error_state["input_describedby"],
            f"saved-search-rename-helper-{self.saved_search.pk}-v135 "
            f"saved-search-rename-error-{self.saved_search.pk}-v137",
        )
        self.assertEqual(error_state["error_message"], "Custom rename error")

        other_state = saved_search_rename_state_v138(request, self.other_saved_search)
        self.assertFalse(other_state["has_error"])
        self.assertFalse(other_state["was_renamed"])

    def test_v138_template_cleanup_removes_raw_request_state_conditionals(self):
        template = Path("listings/templates/listings/saved_search_list.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("SAVED_SEARCH_RENAME_INLINE_STATE_CLEANUP_V138_LOAD", template)
        self.assertIn("SAVED_SEARCH_RENAME_INLINE_STATE_CLEANUP_V138_STATE", template)
        self.assertIn("saved_search_rename_state_v138 request search as rename_state_v138", template)
        self.assertIn("rename_state_v138.was_renamed", template)
        self.assertIn("rename_state_v138.has_error", template)
        self.assertIn("rename_state_v138.aria_expanded", template)
        self.assertIn("rename_state_v138.aria_invalid", template)
        self.assertIn("rename_state_v138.input_describedby", template)
        self.assertIn("rename_state_v138.error_message", template)

        self.assertNotIn("request.renamed_saved_search_id_v136 == search.pk", template)
        self.assertNotIn("request.saved_search_rename_error_id_v137 == search.pk", template)
        self.assertNotIn("request.saved_search_rename_error_id_v137 != search.pk", template)
        self.assertNotIn("request.saved_search_rename_error_message_v137|default", template)
        self.assertNotIn('value="{{ search.name }}"', template)

    def test_v138_error_rendering_preserves_v137_accessibility_contract(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["saved_search_rename_error_id_v137"] = self.saved_search.pk
        session["saved_search_rename_error_message_v137"] = "Type a new name before saving this saved search."
        session.save()

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_STATE_CLEANUP_V138")
        self.assertContains(response, "SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_CARD")
        self.assertContains(response, "Rename was not saved")
        self.assertContains(response, "Type a new name before saving this saved search.")
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'aria-live="assertive"')
        self.assertContains(response, 'aria-expanded="true"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(
            response,
            f'aria-describedby="saved-search-rename-helper-{self.saved_search.pk}-v135 '
            f'saved-search-rename-error-{self.saved_search.pk}-v137"',
        )
        self.assertNotIn("saved_search_rename_error_id_v137", self.client.session)
        self.assertNotIn("saved_search_rename_error_message_v137", self.client.session)

    def test_v138_success_rendering_preserves_v136_visual_feedback_contract(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["saved_search_renamed_id_v136"] = self.saved_search.pk
        session.save()

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_RENAME_INLINE_STATE_CLEANUP_V138")
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_CARD")
        self.assertContains(response, "Saved search renamed")
        self.assertContains(response, "This saved search was updated successfully.")
        self.assertContains(response, 'role="status"')
        self.assertContains(response, 'aria-live="polite"')
        self.assertNotIn("saved_search_renamed_id_v136", self.client.session)

    def test_v138_preserves_backend_rename_contracts(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        blank_response = self.client.post(
            self.rename_url,
            {"name": "   ", "next": next_url},
        )
        self.assertEqual(blank_response.status_code, 302)
        self.assertEqual(blank_response["Location"], next_url)
        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Oak listing search")
        self.assertEqual(
            self.client.session.get("saved_search_rename_error_id_v137"),
            self.saved_search.pk,
        )

        session = self.client.session
        session.flush()
        self.client.force_login(self.user)

        success_response = self.client.post(
            self.rename_url,
            {"name": "  Cleaned   Rename  ", "next": next_url},
        )
        self.assertEqual(success_response.status_code, 302)
        self.assertEqual(success_response["Location"], next_url)
        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Cleaned Rename")
        self.assertEqual(
            self.client.session.get("saved_search_renamed_id_v136"),
            self.saved_search.pk,
        )
