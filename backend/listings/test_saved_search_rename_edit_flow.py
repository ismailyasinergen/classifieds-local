from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchRenameEditFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_rename_v132",
            email="saved-search-rename-v132@classifieds.local",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="saved_search_rename_other_v132",
            email="saved-search-rename-other-v132@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.seller_store_directory_url = reverse("accounts:seller_store_directory")

        self.saved_search = SavedSearch.objects.create(
            user=self.user,
            name="Oak listing search",
            path="/listings/",
            querystring="q=oak",
            query_params={"q": "oak"},
        )
        self.second_saved_search = SavedSearch.objects.create(
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

    def test_saved_search_list_renders_v132_rename_edit_form_without_duplicate_name_html(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.saved_search_list_url,
            {"q": "Oak", "type": "all", "page": "1"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132")
        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132_MOBILE")
        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132_FORM")
        self.assertContains(response, "SAVED_SEARCH_RENAME_EDIT_FLOW_V132_NO_DUPLICATE_NAME")
        self.assertContains(response, "saved-search-rename-form-v132")
        self.assertContains(response, "saved-search-rename-input-v132")
        self.assertContains(response, "saved-search-rename-submit-v132")
        self.assertContains(response, "Rename saved search")
        self.assertContains(response, "Save name")
        self.assertContains(response, "Type a new name")
        self.assertContains(response, f'action="{self.rename_url}"')
        self.assertContains(response, f'id="saved-search-name-{self.saved_search.pk}-v132"')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="next"')
        self.assertContains(response, "q=Oak")
        self.assertContains(response, "type=all")
        self.assertContains(response, "page=1")

        self.assertNotContains(response, 'value="Oak listing search"')
        self.assertEqual(html.count("Oak listing search"), 1)

    def test_owner_can_rename_saved_search_and_preserve_next_url(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all&page=1"

        response = self.client.post(
            self.rename_url,
            {
                "name": "  New    Oak   Search  ",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)

        self.saved_search.refresh_from_db()
        self.second_saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "New Oak Search")
        self.assertEqual(self.second_saved_search.name, "Walnut listing search")

    def test_blank_name_is_rejected_and_existing_name_is_kept(self):
        self.client.force_login(self.user)
        next_url = f"{self.saved_search_list_url}?q=Oak&type=all"

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

    def test_rename_is_owner_scoped(self):
        self.client.force_login(self.user)
        other_rename_url = reverse(
            "listings:saved_search_rename",
            kwargs={"pk": self.other_user_search.pk},
        )

        response = self.client.post(
            other_rename_url,
            {
                "name": "Stolen rename attempt",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 404)

        self.other_user_search.refresh_from_db()
        self.assertEqual(self.other_user_search.name, "Other user private search")

    def test_rename_rejects_unsafe_next_url(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.rename_url,
            {
                "name": "Safe redirect rename",
                "next": "https://evil.example/phish",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.saved_search_list_url)

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Safe redirect rename")

    def test_rename_requires_login(self):
        response = self.client.post(
            self.rename_url,
            {
                "name": "Anonymous rename attempt",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.name, "Oak listing search")
