from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStorefrontFoundationTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.seller = self.User.objects.create_user(
            username="seller_store_v105",
            email="seller-store-v105@classifieds.local",
            password="StrongPass123!",
        )
        self.seller_profile, _ = UserProfile.objects.get_or_create(user=self.seller)
        self.seller_profile.phone = "+49 555 0101"
        self.seller_profile.location = "Berlin"
        self.seller_profile.business_name = "V105 Seller Store"
        self.seller_profile.save(
            update_fields=[
                "phone",
                "location",
                "business_name",
            ]
        )
        self.category = Category.objects.create(name="Furniture", slug="v105-furniture")
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="V105 Seller Store",
            headline="Trusted local seller with curated listings.",
            description="A small storefront for v105 foundation testing.",
            location="Berlin",
        )

    def create_listing(self, title, status=Listing.Status.APPROVED, owner=None):
        return Listing.objects.create(
            title=title,
            description="A storefront test listing.",
            price=Decimal("100.00"),
            category=self.category,
            owner=owner or self.seller,
            location="Berlin",
            status=status,
        )

    def test_registration_auto_creates_seller_store(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "new_store_user_v105",
                "email": "new-store-user-v105@classifieds.local",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        new_user = self.User.objects.get(username="new_store_user_v105")
        self.assertTrue(SellerStore.objects.filter(owner=new_user).exists())

    def test_store_settings_page_creates_and_updates_store(self):
        user = self.User.objects.create_user(
            username="settings_store_user_v105",
            email="settings-store-user-v105@classifieds.local",
            password="StrongPass123!",
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.location = "Hamburg"
        profile.save(update_fields=["location"])
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:seller_store_settings"))
        self.assertEqual(response.status_code, 200)

        store = SellerStore.objects.get(owner=user)
        self.assertEqual(store.location, "Hamburg")

        response = self.client.post(
            reverse("accounts:seller_store_settings"),
            {
                "name": "Updated V105 Store",
                "headline": "Updated seller headline",
                "description": "Updated store description.",
                "location": "Munich",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        store.refresh_from_db()
        self.assertEqual(store.name, "Updated V105 Store")
        self.assertEqual(store.headline, "Updated seller headline")
        self.assertEqual(store.location, "Munich")
        self.assertTrue(store.is_active)

    def test_backfill_command_creates_store_for_existing_seller(self):
        seller = self.User.objects.create_user(
            username="backfill_store_user_v105",
            email="backfill-store-user-v105@classifieds.local",
            password="StrongPass123!",
        )
        UserProfile.objects.get_or_create(user=seller)
        self.create_listing("Backfill seller listing", owner=seller)

        self.assertFalse(SellerStore.objects.filter(owner=seller).exists())

        output = StringIO()
        call_command("backfill_seller_stores", stdout=output)

        self.assertTrue(SellerStore.objects.filter(owner=seller).exists())
        self.assertIn("Created store for backfill_store_user_v105", output.getvalue())

    def test_public_store_page_shows_only_active_approved_listings(self):
        approved_listing = self.create_listing("Approved storefront listing")
        pending_listing = self.create_listing(
            "Pending storefront listing",
            status=Listing.Status.PENDING,
        )

        response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V105 Seller Store")
        self.assertContains(response, approved_listing.title)
        self.assertNotContains(response, pending_listing.title)

    def test_inactive_store_is_hidden_from_public_but_owner_can_preview(self):
        self.store.is_active = False
        self.store.save(update_fields=["is_active", "updated_at"])

        public_response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})
        )
        self.assertEqual(public_response.status_code, 404)

        self.client.force_login(self.seller)
        owner_response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})
        )
        self.assertEqual(owner_response.status_code, 200)
        self.assertContains(owner_response, "This store is hidden from buyers.")

    def test_listing_detail_links_to_seller_store(self):
        listing = self.create_listing("Listing detail store link")

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seller Store")
        self.assertContains(response, "View seller store")
        self.assertContains(
            response,
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug}),
        )
