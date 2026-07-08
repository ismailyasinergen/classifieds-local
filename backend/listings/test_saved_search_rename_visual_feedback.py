from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchRenameVisualFeedbackTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_feedback_v136",
            email="saved-search-rename-feedback-v136@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_rename_feedback_other_v136",
            email="saved-search-rename-feedback-other-v136@classifieds.local",
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
        self.second_search = SavedSearch.objects.create(
            user=self.user,
            name="Walnut listing search",
            path="/listings/",
            querystring="q=walnut",
            query_params={"q": "walnut"},
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

    def test_v136_successful_rename_sets_feedback_session_and_preserves_redirect_url(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "  Renamed   With   Feedback  ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Renamed With Feedback")

        self.assertEqual(
            self.client.session.get("saved_search_renamed_id_v136"),
            self.saved_search.pk,
        )

    def test_v136_saved_search_list_renders_and_clears_renamed_card_feedback(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["saved_search_renamed_id_v136"] = self.saved_search.pk
        session.save()

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            getattr(response.wsgi_request, "renamed_saved_search_id_v136", None),
            self.saved_search.pk,
        )
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136")
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_CARD")
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_FORM")
        self.assertContains(response, "saved-search-rename-feedback-v136")
        self.assertContains(response, "saved-search-rename-feedback-card-v136")
        self.assertContains(response, "saved-search-rename-feedback-title-v136")
        self.assertContains(response, "saved-search-rename-feedback-copy-v136")
        self.assertContains(response, 'role="status"')
        self.assertContains(response, 'aria-live="polite"')
        self.assertContains(response, "Saved search renamed")
        self.assertContains(response, "This saved search was updated successfully.")
        self.assertNotIn("saved_search_renamed_id_v136", self.client.session)

    def test_v136_unrelated_session_feedback_does_not_render_card_notice(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["saved_search_renamed_id_v136"] = 999999
        session.save()

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            getattr(response.wsgi_request, "renamed_saved_search_id_v136", None),
            999999,
        )
        self.assertContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136")
        self.assertNotContains(response, "SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_CARD")
        self.assertNotContains(response, "Saved search renamed")
        self.assertNotIn("saved_search_renamed_id_v136", self.client.session)

    def test_v136_preserves_v132_to_v135_rename_contracts(self):
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
        self.assertContains(response, "aria-label=\"Rename this saved search\"")
        self.assertContains(response, "Press Escape to cancel renaming")
        self.assertContains(response, f'action="{self.rename_url}"')
        self.assertNotContains(response, 'value="Oak listing search"')
        self.assertEqual(html.count("Oak listing search"), 1)

    def test_v136_owner_scope_still_blocks_foreign_rename_without_feedback_session(self):
        self.client.force_login(self.user)

        other_rename_url = reverse(
            "listings:saved_search_rename",
            kwargs={"pk": self.other_user_search.pk},
        )
        response = self.client.post(
            other_rename_url,
            {
                "name": "Should not rename",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.other_user_search.refresh_from_db()
        self.assertEqual(self.other_user_search.name, "Other user private search")
        self.assertIsNone(self.client.session.get("saved_search_renamed_id_v136"))
