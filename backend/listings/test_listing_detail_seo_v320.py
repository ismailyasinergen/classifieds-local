from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path
import struct
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import (
    TestCase,
    override_settings,
)
from django.urls import reverse

from accounts.models import (
    SellerStore,
    UserProfile,
)
from categories.models import Category
from listings.listing_detail_seo_v320 import (
    LISTING_DETAIL_FALLBACK_IMAGE_V320,
    LISTING_DETAIL_SEO_METADATA_V320,
)
from listings.models import (
    Listing,
    ListingImage,
)


@override_settings(
    ALLOWED_HOSTS=[
        "testserver",
        "example.test",
    ]
)
class ListingDetailSeoMetadataV320Tests(
    TestCase
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(
            settings.BASE_DIR
        )

        cls.view_path = (
            cls.base_dir
            / "listings"
            / "listing_browse_detail_views.py"
        )

        cls.base_template_path = (
            cls.base_dir
            / "templates"
            / "base.html"
        )

        cls.fallback_path = (
            cls.base_dir
            / "listings"
            / "static"
            / LISTING_DETAIL_FALLBACK_IMAGE_V320
        )

    def setUp(self):
        user_model = get_user_model()

        self.seller = (
            user_model.objects.create_user(
                username="v320-seller",
                email=(
                    "v320-seller@"
                    "classifieds.local"
                ),
                password="StrongPass123!",
            )
        )

        UserProfile.objects.get_or_create(
            user=self.seller,
        )

        SellerStore.objects.get_or_create(
            owner=self.seller,
        )

        self.category = Category.objects.create(
            name="V320 Furniture",
            slug="v320-furniture",
        )

        self.listing = Listing.objects.create(
            title=(
                "V320 Social Preview "
                "Listing"
            ),
            description=(
                "A public listing used to "
                "verify social preview and "
                "structured metadata."
            ),
            price=Decimal("320.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=(
                Listing.Status.APPROVED
            ),
        )

    def detail(
        self,
        listing=None,
        params=None,
    ):
        active_listing = (
            listing
            or self.listing
        )

        return self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": (
                        active_listing.pk
                    ),
                },
            ),
            params or {},
            secure=True,
            HTTP_HOST="example.test",
        )

    def test_v320_marker_and_view_shape_are_stable(
        self,
    ):
        self.assertTrue(
            LISTING_DETAIL_SEO_METADATA_V320
        )

        source = self.view_path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        classes = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.ClassDef,
            )
        }

        target = classes[
            "ListingDetailView"
        ]

        line_count = (
            (
                target.end_lineno
                or target.lineno
            )
            - target.lineno
            + 1
        )

        base_names = [
            base.id
            for base in target.bases
            if isinstance(
                base,
                ast.Name,
            )
        ]

        self.assertEqual(
            line_count,
            48,
        )

        self.assertEqual(
            base_names[:3],
            [
                (
                    "RecentlyViewedListings"
                    "ContextMixinV272"
                ),
                (
                    "RelatedListings"
                    "ContextMixinV271"
                ),
                (
                    "ListingDetailSeo"
                    "ContextMixinV320"
                ),
            ],
        )

    def test_v320_public_context_uses_canonical_fallback_metadata(
        self,
    ):
        response = self.detail()

        canonical_url = (
            "https://example.test"
            f"/listings/{self.listing.pk}/"
        )

        fallback_url = (
            "https://example.test/static/"
            + LISTING_DETAIL_FALLBACK_IMAGE_V320
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "seo_canonical_url"
            ],
            canonical_url,
        )

        self.assertEqual(
            response.context["seo_robots"],
            "index,follow",
        )

        self.assertTrue(
            response.context[
                "seo_social_metadata"
            ]
        )

        self.assertEqual(
            response.context["seo_og_type"],
            "product",
        )

        self.assertEqual(
            response.context[
                "seo_twitter_card"
            ],
            "summary_large_image",
        )

        self.assertEqual(
            response.context[
                "seo_image_url"
            ],
            fallback_url,
        )

    def test_v320_rendered_head_contains_complete_social_image_tags(
        self,
    ):
        response = self.detail()

        canonical_url = (
            "https://example.test"
            f"/listings/{self.listing.pk}/"
        )

        fallback_url = (
            "https://example.test/static/"
            + LISTING_DETAIL_FALLBACK_IMAGE_V320
        )

        expected_fragments = (
            (
                '<link rel="canonical" '
                f'href="{canonical_url}">'
            ),
            (
                '<meta property="og:type" '
                'content="product">'
            ),
            (
                '<meta property="og:image" '
                f'content="{fallback_url}">'
            ),
            (
                '<meta name="twitter:card" '
                'content="summary_large_image">'
            ),
            (
                '<meta name="twitter:image" '
                f'content="{fallback_url}">'
            ),
        )

        for expected in expected_fragments:
            with self.subTest(
                expected=expected
            ):
                self.assertContains(
                    response,
                    expected,
                    html=True,
                )

    def test_v320_listing_photo_replaces_fallback_image(
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
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                listing_image = (
                    ListingImage.objects.create(
                        listing=self.listing,
                        image=SimpleUploadedFile(
                            "v320-photo.gif",
                            image_bytes,
                            content_type=(
                                "image/gif"
                            ),
                        ),
                    )
                )

                response = self.detail()

                expected_url = (
                    "https://example.test/"
                    + listing_image.image.url.lstrip(
                        "/"
                    )
                )

        self.assertEqual(
            response.context[
                "seo_image_url"
            ],
            expected_url,
        )

        self.assertContains(
            response,
            (
                '<meta property="og:image" '
                f'content="{expected_url}">'
            ),
            html=True,
        )

    def test_v320_canonical_url_ignores_tracking_query_parameters(
        self,
    ):
        response = self.detail(
            params={
                "utm_source": "share",
                "ref": "social",
            }
        )

        self.assertEqual(
            response.context[
                "seo_canonical_url"
            ],
            (
                "https://example.test"
                f"/listings/{self.listing.pk}/"
            ),
        )

    def test_v320_metadata_escapes_html_and_json_ld_breakout(
        self,
    ):
        unsafe_listing = (
            Listing.objects.create(
                title=(
                    "V320 <script>"
                    "alert(1)</script>"
                ),
                description=(
                    "</script><script>"
                    "alert(2)</script>"
                ),
                price=Decimal("99.00"),
                location="Berlin & Mitte",
                category=self.category,
                owner=self.seller,
                status=(
                    Listing.Status.APPROVED
                ),
            )
        )

        response = self.detail(
            unsafe_listing
        )

        serialized = response.context[
            "seo_json_ld"
        ]

        self.assertNotIn(
            "</script>",
            serialized.lower(),
        )

        payload = json.loads(
            serialized
        )

        self.assertEqual(
            payload["@type"],
            "Product",
        )

        self.assertNotContains(
            response,
            "<script>alert(1)</script>",
        )

        self.assertContains(
            response,
            "V320 &lt;script&gt;"
            "alert(1)&lt;/script&gt;",
        )

    def test_v320_nonpublic_owner_preview_is_noindex_without_social_tags(
        self,
    ):
        preview = Listing.objects.create(
            title="V320 Pending Preview",
            description=(
                "Owner-only preview metadata."
            ),
            price=Decimal("50.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.PENDING,
        )

        self.client.force_login(
            self.seller
        )

        response = self.detail(
            preview
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["seo_robots"],
            "noindex,nofollow",
        )

        self.assertFalse(
            response.context[
                "seo_social_metadata"
            ]
        )

        self.assertEqual(
            response.context["seo_json_ld"],
            "",
        )

        self.assertNotContains(
            response,
            'property="og:image"',
        )

        self.assertNotContains(
            response,
            'type="application/ld+json"',
        )

    def test_v320_json_ld_describes_product_offer(
        self,
    ):
        response = self.detail()

        payload = json.loads(
            response.context[
                "seo_json_ld"
            ]
        )

        self.assertEqual(
            payload["@context"],
            "https://schema.org",
        )

        self.assertEqual(
            payload["@type"],
            "Product",
        )

        self.assertEqual(
            payload["sku"],
            str(self.listing.pk),
        )

        self.assertEqual(
            payload["offers"][
                "priceCurrency"
            ],
            "TRY",
        )

        self.assertEqual(
            payload["offers"]["price"],
            "320.00",
        )

        self.assertEqual(
            payload["image"],
            [
                response.context[
                    "seo_image_url"
                ],
            ],
        )

    def test_v320_base_template_and_fallback_png_are_packaged(
        self,
    ):
        source = (
            self.base_template_path.read_text(
                encoding="utf-8"
            )
        )

        for fragment in (
            "LISTING_DETAIL_SEO_METADATA_V320",
            'property="og:image"',
            'property="og:image:alt"',
            'name="twitter:image"',
            'name="twitter:image:alt"',
        ):
            with self.subTest(
                fragment=fragment
            ):
                self.assertIn(
                    fragment,
                    source,
                )

        raw = self.fallback_path.read_bytes()

        self.assertEqual(
            raw[:8],
            b"\x89PNG\r\n\x1a\n",
        )

        width, height = struct.unpack(
            ">II",
            raw[16:24],
        )

        self.assertEqual(
            (
                width,
                height,
            ),
            (
                1200,
                630,
            ),
        )

    def test_v320_adds_no_database_migration(
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
                ).glob("*v320*.py")
            )

        self.assertEqual(
            matches,
            [],
        )
