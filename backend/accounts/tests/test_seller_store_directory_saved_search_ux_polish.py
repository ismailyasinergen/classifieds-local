from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SellerStoreDirectorySavedSearchUxPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="seller_store_saved_search_ux_v125",
            email="seller-store-saved-search-ux-v125@classifieds.local",
            password="StrongPass123!",
        )
        self.directory_url = reverse("accounts:seller_store_directory")
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.saved_search_create_url = reverse("listings:saved_search_create")
        self.query_data = {
            "q": "oak",
            "location": "Berlin",
        }
        self.querystring = "q=oak&location=Berlin"

    def test_authenticated_directory_save_cta_uses_polished_copy_and_mobile_hooks(self):
        self.client.force_login(self.user)

        response = self.client.get(self.directory_url, self.query_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SELLER_STORE_DIRECTORY_SAVED_SEARCH_UX_POLISH_V125")
        self.assertContains(response, "seller-store-saved-search-cta-v125")
        self.assertContains(response, "seller-store-saved-search-form-v125")
        self.assertContains(response, "Save this seller store search")
        self.assertContains(response, "return to this exact directory view")
        self.assertContains(response, "Save seller store search")
        self.assertContains(response, f'name="path" value="{self.directory_url}"')

    def test_already_saved_directory_search_has_clear_saved_state_and_management_link(self):
        # Cover both likely canonical orders so this test remains focused on
        # the rendered UX, not querystring ordering internals.
        for querystring in ("q=oak&location=Berlin", "location=Berlin&q=oak"):
            SavedSearch.objects.get_or_create(
                user=self.user,
                path=self.directory_url,
                querystring=querystring,
                defaults={
                    "name": "Berlin oak sellers",
                    "query_params": {
                        "q": "oak",
                        "location": "Berlin",
                    },
                },
            )

        self.client.force_login(self.user)
        response = self.client.get(self.directory_url, self.query_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-saved-search-saved-state-v125")
        self.assertContains(response, "Already saved")
        self.assertContains(response, "already in your Saved Searches")
        self.assertContains(response, self.saved_search_list_url)
        self.assertContains(response, "View saved searches")
        self.assertNotContains(response, "seller-store-saved-search-form-v122")
        self.assertNotContains(response, "Save seller store search</button>")

    def test_saving_seller_store_directory_search_adds_success_message(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.saved_search_create_url,
            {
                "name": "",
                "path": self.directory_url,
                "querystring": self.querystring,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        saved_search = SavedSearch.objects.filter(
            user=self.user,
            path=self.directory_url,
        ).first()
        self.assertIsNotNone(saved_search)
        self.assertTrue(saved_search.is_seller_store_directory_search)
        self.assertEqual(saved_search.query_params.get("q"), "oak")
        self.assertEqual(saved_search.query_params.get("location"), "Berlin")

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn(
            "Seller store search saved. You can reopen it from Saved Searches.",
            messages,
        )
        self.assertContains(response, "seller-store-saved-search-saved-state-v125")
        self.assertContains(response, "Already saved")
