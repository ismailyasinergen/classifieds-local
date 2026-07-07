from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreDirectorySavedSearchCtaTests(TestCase):
    def setUp(self):
        self.directory_url = reverse("accounts:seller_store_directory")
        self.saved_searches_url = reverse("listings:saved_search_list")
        self.login_url = reverse("accounts:login")
        self.category = Category.objects.create(
            name="Directory Saved CTA Furniture V121",
            slug="directory-saved-cta-furniture-v121",
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
            headline=f"{store_name} saved-search CTA headline.",
            description=f"{store_name} saved-search CTA description.",
            location=location,
        )

        for index in range(listing_count):
            Listing.objects.create(
                title=f"{store_name} Listing {index + 1}",
                description=f"{store_name} saved-search CTA listing.",
                price=Decimal("125.00"),
                category=self.category,
                owner=user,
                location=location,
                status=Listing.Status.APPROVED,
            )

        return user, store

    def test_saved_search_cta_is_hidden_on_default_directory(self):
        self.create_store_with_listings(
            "directory_saved_default_v121",
            "Directory Saved Default Store",
        )

        response = self.client.get(self.directory_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["directory_saved_search_active"])
        self.assertEqual(response.context["directory_saved_search_filter_count"], 0)
        self.assertEqual(response.context["directory_saved_search_url"], self.directory_url)
        self.assertNotContains(response, 'aria-label="Save seller store search"')
        self.assertNotContains(response, "Save this seller store search")

    def test_saved_search_cta_renders_for_active_search_and_location(self):
        self.create_store_with_listings(
            "directory_saved_search_berlin_v121",
            "Directory Saved Search Berlin Store",
            location="Berlin",
            listing_count=2,
            verified=True,
        )
        self.create_store_with_listings(
            "directory_saved_search_munich_v121",
            "Directory Saved Search Munich Store",
            location="Munich",
            listing_count=1,
            verified=True,
        )

        response = self.client.get(
            self.directory_url,
            {
                "q": "Saved Search Berlin",
                "location": "Berlin",
                "verified_only": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["directory_saved_search_active"])
        self.assertEqual(response.context["directory_saved_search_filter_count"], 3)
        self.assertContains(response, "seller-store-saved-search-cta-v121")
        self.assertContains(response, 'aria-label="Save seller store search"')
        self.assertContains(response, "Save this seller store search")
        self.assertContains(response, "3 active selections")
        self.assertContains(response, "1 matching store")
        self.assertContains(response, "Reopen this search")
        self.assertIn("q=Saved+Search+Berlin", response.context["directory_saved_search_url"])
        self.assertIn("location=Berlin", response.context["directory_saved_search_url"])
        self.assertIn("verified_only=1", response.context["directory_saved_search_url"])

    def test_saved_search_cta_renders_for_sort_only_state(self):
        self.create_store_with_listings(
            "directory_saved_sort_v121",
            "Directory Saved Sort Store",
            location="Berlin",
        )

        response = self.client.get(self.directory_url, {"sort": "newest"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["directory_saved_search_active"])
        self.assertEqual(response.context["directory_saved_search_filter_count"], 1)
        self.assertContains(response, "Save this seller store search")
        self.assertContains(response, "1 active selection")
        self.assertIn("sort=newest", response.context["directory_saved_search_url"])

    def test_anonymous_saved_search_cta_prompts_login_with_current_url(self):
        self.create_store_with_listings(
            "directory_saved_login_v121",
            "Directory Saved Login Store",
            location="Hamburg",
        )

        response = self.client.get(
            self.directory_url,
            {
                "location": "Hamburg",
                "sort": "name_az",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in to revisit searches")
        self.assertContains(response, self.login_url)
        self.assertNotContains(response, "View saved searches")
        saved_url = response.context["directory_saved_search_url"]
        self.assertIn("location=Hamburg", saved_url)
        self.assertIn("sort=name_az", saved_url)

    def test_authenticated_saved_search_cta_links_to_saved_searches_page(self):
        user, store = self.create_store_with_listings(
            "directory_saved_user_v121",
            "Directory Saved User Store",
            location="Berlin",
        )
        self.client.force_login(user)

        response = self.client.get(self.directory_url, {"q": "Saved User"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save this seller store search")
        self.assertContains(response, "View saved searches")
        self.assertContains(response, self.saved_searches_url)
        self.assertNotContains(response, "Log in to revisit searches")
