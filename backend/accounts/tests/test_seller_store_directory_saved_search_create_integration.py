from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing, SavedSearch


class SellerStoreDirectorySavedSearchCreateIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            username="directory_saved_create_buyer_v122",
            email="directory-saved-create-buyer-v122@classifieds.local",
            password="StrongPass123!",
        )
        self.directory_url = reverse("accounts:seller_store_directory")
        self.saved_search_create_url = reverse("listings:saved_search_create")
        self.saved_searches_url = reverse("listings:saved_search_list")
        self.listing_browse_url = reverse("listings:listing_list")
        self.category = Category.objects.create(
            name="Directory Saved Create Furniture V122",
            slug="directory-saved-create-furniture-v122",
        )

    def create_store_with_listings(
        self,
        username,
        store_name,
        location="Berlin",
        listing_count=1,
        verified=False,
    ):
        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            email=f"{username}@classifieds.local",
            password="StrongPass123!",
        )
        user.profile.location = location
        user.profile.verification_status = (
            UserProfile.VerificationStatus.APPROVED
            if verified
            else UserProfile.VerificationStatus.NOT_REQUESTED
        )
        user.profile.save(update_fields=["location", "verification_status"])

        store = SellerStore.objects.create(
            owner=user,
            name=store_name,
            headline=f"{store_name} saved-search create headline.",
            description=f"{store_name} saved-search create description.",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} saved-search create listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=location,
                status=Listing.Status.APPROVED,
            )

        return user, store

    def test_authenticated_directory_cta_renders_direct_save_form(self):
        self.create_store_with_listings(
            "directory_saved_create_seller_v122",
            "Directory Saved Create Berlin Store",
            location="Berlin",
            listing_count=2,
            verified=True,
        )
        self.client.force_login(self.buyer)

        response = self.client.get(
            self.directory_url,
            {
                "location": "Berlin",
                "verified_only": "1",
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seller-store-saved-search-form-v122")
        self.assertContains(response, self.saved_search_create_url)
        self.assertContains(response, "Save seller store search")
        self.assertContains(response, "View saved searches")
        self.assertEqual(
            response.context["directory_saved_search_path"],
            self.directory_url,
        )
        self.assertEqual(
            response.context["directory_saved_search_querystring"],
            "location=Berlin&sort=name_az&verified_only=1",
        )
        self.assertIsNone(response.context["directory_current_saved_search"])

    def test_post_creates_seller_store_directory_saved_search_with_path(self):
        self.client.force_login(self.buyer)
        querystring = (
            f"q=Desk&page=9&location=Berlin&verified_only=1"
            f"&min_listings=2&sort=name_az&category={self.category.slug}"
        )

        response = self.client.post(
            self.saved_search_create_url,
            {
                "name": "Berlin seller stores",
                "path": self.directory_url,
                "querystring": querystring,
            },
        )

        expected_querystring = (
            f"category={self.category.slug}&location=Berlin"
            "&min_listings=2&q=Desk&sort=name_az&verified_only=1"
        )
        self.assertEqual(
            response["Location"],
            f"{self.directory_url}?{expected_querystring}",
        )

        saved_search = SavedSearch.objects.get(user=self.buyer)
        self.assertEqual(saved_search.name, "Berlin seller stores")
        self.assertEqual(saved_search.path, self.directory_url)
        self.assertEqual(saved_search.querystring, expected_querystring)
        self.assertEqual(saved_search.query_params["category"], self.category.slug)
        self.assertEqual(saved_search.query_params["location"], "Berlin")
        self.assertEqual(saved_search.query_params["min_listings"], "2")
        self.assertEqual(saved_search.query_params["q"], "Desk")
        self.assertEqual(saved_search.query_params["sort"], "name_az")
        self.assertEqual(saved_search.query_params["verified_only"], "1")
        self.assertNotIn("page", saved_search.query_params)

    def test_seller_store_saved_search_dedupes_by_path_not_listing_browse(self):
        self.client.force_login(self.buyer)
        SavedSearch.objects.create(
            user=self.buyer,
            name="Listing browse Berlin",
            path=self.listing_browse_url,
            query_params={"location": "Berlin"},
            querystring="location=Berlin",
        )

        first_response = self.client.post(
            self.saved_search_create_url,
            {
                "name": "Store Berlin",
                "path": self.directory_url,
                "querystring": "location=Berlin",
            },
        )

        self.assertEqual(first_response["Location"], f"{self.directory_url}?location=Berlin")
        self.assertEqual(SavedSearch.objects.filter(user=self.buyer).count(), 2)

        second_response = self.client.post(
            self.saved_search_create_url,
            {
                "name": "Store Berlin Updated",
                "path": self.directory_url,
                "querystring": "location=Berlin",
            },
        )

        self.assertEqual(second_response["Location"], f"{self.directory_url}?location=Berlin")
        self.assertEqual(SavedSearch.objects.filter(user=self.buyer).count(), 2)
        store_search = SavedSearch.objects.get(
            user=self.buyer,
            path=self.directory_url,
        )
        self.assertEqual(store_search.name, "Store Berlin Updated")

    def test_already_saved_directory_search_shows_saved_state(self):
        self.create_store_with_listings(
            "directory_saved_already_v122",
            "Directory Saved Already Store",
            location="Berlin",
        )
        saved_search = SavedSearch.objects.create(
            user=self.buyer,
            name="Already saved store search",
            path=self.directory_url,
            query_params={"q": "Already"},
            querystring="q=Already",
        )
        self.client.force_login(self.buyer)

        response = self.client.get(self.directory_url, {"q": "Already"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["directory_current_saved_search"], saved_search)
        self.assertContains(response, "Already saved")
        self.assertContains(response, "View saved searches")
        self.assertNotContains(response, "Save seller store search</button>")

    def test_anonymous_directory_cta_keeps_login_path_not_save_form(self):
        self.create_store_with_listings(
            "directory_saved_anon_v122",
            "Directory Saved Anonymous Store",
            location="Hamburg",
        )

        response = self.client.get(self.directory_url, {"location": "Hamburg"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in to revisit searches")
        self.assertNotContains(response, "seller-store-saved-search-form-v122")
        self.assertEqual(SavedSearch.objects.count(), 0)
