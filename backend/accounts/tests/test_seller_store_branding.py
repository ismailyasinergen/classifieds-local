from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import SellerStore
from categories.models import Category
from listings.models import Listing


def tiny_gif_upload(name):
    return SimpleUploadedFile(
        name,
        (
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff,\x00\x00\x00"
            b"\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


class SellerStoreBrandingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media.name)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        cls._temp_media.cleanup()
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="branding_seller_v108",
            email="branding-seller-v108@classifieds.local",
            password="StrongPass123!",
        )
        self.category = Category.objects.create(
            name="Branding Furniture",
            slug="branding-furniture-v108",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Branded Seller Store",
            headline="A visual store identity for buyers.",
            description="Store branding test description.",
            location="Berlin",
        )

    def create_listing(self, title="Branded Store Listing"):
        return Listing.objects.create(
            title=title,
            description="A listing connected to a branded seller store.",
            price=Decimal("199.00"),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

    def add_branding_paths(self):
        self.store.logo = "seller_store_logos/branded-logo.png"
        self.store.banner = "seller_store_banners/branded-banner.png"
        self.store.save(update_fields=["logo", "banner", "updated_at"])

    def test_store_settings_form_uploads_logo_and_banner(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("accounts:seller_store_settings"),
            {
                "name": "Updated Branded Store",
                "headline": "Updated branded headline",
                "description": "Updated branded description.",
                "location": "Hamburg",
                "is_active": "on",
                "logo": tiny_gif_upload("store-logo.gif"),
                "banner": tiny_gif_upload("store-banner.gif"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, "Updated Branded Store")
        self.assertTrue(self.store.logo.name.startswith("seller_store_logos/"))
        self.assertTrue(self.store.banner.name.startswith("seller_store_banners/"))

    def test_store_settings_page_uses_multipart_form_and_preview(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("accounts:seller_store_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, "Store logo")
        self.assertContains(response, "Store banner")
        self.assertContains(response, "Store branding preview")

    def test_public_store_page_displays_logo_and_banner(self):
        self.add_branding_paths()
        self.create_listing()

        response = self.client.get(
            reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store.logo.url)
        self.assertContains(response, self.store.banner.url)
        self.assertContains(response, "storefront-logo-v108")
        self.assertContains(response, "storefront-banner-v108")

    def test_store_directory_card_displays_logo(self):
        self.add_branding_paths()
        self.create_listing()

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store.logo.url)
        self.assertContains(response, "seller-store-directory-logo-v108")

    def test_listing_card_displays_compact_store_logo(self):
        self.add_branding_paths()
        listing = self.create_listing("Listing Card Branding")

        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, listing.title)
        self.assertContains(response, self.store.logo.url)
        self.assertContains(response, "listing-card-store-logo-v108")

    def test_listing_detail_displays_store_logo_and_banner(self):
        self.add_branding_paths()
        listing = self.create_listing("Listing Detail Branding")

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store.logo.url)
        self.assertContains(response, self.store.banner.url)
        self.assertContains(response, "seller-store-logo-v108")
        self.assertContains(response, "seller-store-banner-v108")
