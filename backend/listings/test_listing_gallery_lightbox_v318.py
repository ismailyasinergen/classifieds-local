from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    SellerStore,
    UserProfile,
)
from categories.models import Category
from listings.models import (
    Listing,
    ListingImage,
)


V318_MARKER = "LISTING_GALLERY_LIGHTBOX_V318"


class ListingGalleryLightboxV318Tests(
    TestCase
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(settings.BASE_DIR)
        cls.template_path = (
            cls.base_dir
            / "listings"
            / "templates"
            / "listings"
            / "listing_detail.html"
        )
        cls.source = cls.template_path.read_text(
            encoding="utf-8"
        )

    def setUp(self):
        user_model = get_user_model()

        self.seller = user_model.objects.create_user(
            username="v318-seller",
            email="v318-seller@classifieds.local",
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=self.seller,
        )

        SellerStore.objects.get_or_create(
            owner=self.seller,
        )

        self.category = Category.objects.create(
            name="V318 Furniture",
            slug="v318-furniture",
        )

        self.listing = Listing.objects.create(
            title="V318 Gallery Listing",
            description=(
                "A public listing used to verify "
                "the full-screen gallery."
            ),
            price=Decimal("318.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.APPROVED,
        )

    def test_v318_marker_and_dialog_are_packaged(
        self,
    ):
        self.assertIn(
            V318_MARKER,
            self.source,
        )
        self.assertIn(
            "<dialog",
            self.source,
        )
        self.assertIn(
            'id="listing-gallery-lightbox-v318"',
            self.source,
        )
        self.assertIn(
            'aria-labelledby="listing-gallery-lightbox-title-v318"',
            self.source,
        )

    def test_v318_main_image_is_keyboard_accessible(
        self,
    ):
        fragments = (
            'role="button"',
            'tabindex="0"',
            'aria-haspopup="dialog"',
            'aria-controls="listing-gallery-lightbox-v318"',
            'event.key === "Enter"',
            'event.key === " "',
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v318_navigation_supports_buttons_and_arrows(
        self,
    ):
        fragments = (
            "data-gallery-lightbox-prev-v318",
            "data-gallery-lightbox-next-v318",
            'event.key === "ArrowLeft"',
            'event.key === "ArrowRight"',
            "showLightboxImage(activeIndex - 1)",
            "showLightboxImage(activeIndex + 1)",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v318_selection_stays_synchronized(
        self,
    ):
        fragments = (
            "selected.click();",
            "selected.dataset.gallerySrc",
            "selected.dataset.galleryAlt",
            "selectedIndex()",
            "lightboxCounter.textContent",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v318_close_paths_and_focus_restore_exist(
        self,
    ):
        fragments = (
            "data-gallery-lightbox-close-v318",
            (
                'lightbox.addEventListener(\n'
                '                "cancel"'
            ),
            "event.target === lightbox",
            "restoreFocusNode.focus()",
            "listing-gallery-lightbox-open-v318",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v318_mobile_and_backdrop_styles_exist(
        self,
    ):
        fragments = (
            ".listing-gallery-lightbox-v318::backdrop",
            "@media (max-width: 760px)",
            "width: 100vw;",
            "height: 100vh;",
            "object-fit: contain;",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_v318_photo_listing_renders_lightbox(
        self,
    ):
        image_bytes = (
            b"GIF89a"
            b"\x01\x00\x01\x00"
            b"\x80\x00\x00"
            b"\x00\x00\x00"
            b"\xff\xff\xff"
            b"!\xf9\x04\x01"
            b"\x00\x00\x00\x00"
            b",\x00\x00\x00\x00"
            b"\x01\x00\x01\x00"
            b"\x00\x02\x02D\x01\x00;"
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                listing_image = ListingImage.objects.create(
                    listing=self.listing,
                    image=SimpleUploadedFile(
                        "v318-photo.gif",
                        image_bytes,
                        content_type="image/gif",
                    ),
                )

                response = self.client.get(
                    reverse(
                        "listings:listing_detail",
                        kwargs={
                            "pk": self.listing.pk,
                        },
                    )
                )

                image_url = listing_image.image.url

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'id="listing-gallery-lightbox-v318"',
        )

        self.assertContains(
            response,
            'data-marker="LISTING_GALLERY_LIGHTBOX_V318"',
        )

        self.assertContains(
            response,
            image_url,
            count=4,
        )

        self.assertContains(
            response,
            "Open full-screen photo viewer",
        )

    def test_v318_image_free_listing_hides_lightbox_dialog(
        self,
    ):
        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            'id="listing-gallery-lightbox-v318"',
        )

        self.assertNotContains(
            response,
            'data-marker="LISTING_GALLERY_LIGHTBOX_V318"',
        )

        self.assertNotContains(
            response,
            "Open full-screen photo viewer",
        )

    def test_v318_adds_no_database_migration(
        self,
    ):
        matches = []

        for app_name in (
            "accounts",
            "listings",
        ):
            matches.extend(
                (
                    self.base_dir
                    / app_name
                    / "migrations"
                ).glob("*v318*.py")
            )

        self.assertEqual(
            matches,
            [],
        )
