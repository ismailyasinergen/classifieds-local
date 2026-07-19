"""
PUBLIC_DEALS_SEO_METADATA_V298

Focused SEO, canonicalization, structured-data, safety, and compatibility
tests for the public Deals landing page.
"""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import connection
from django.test import (
    RequestFactory,
    TestCase,
    override_settings,
)
from django.shortcuts import render
from django.test.utils import CaptureQueriesContext
from django.urls import path, reverse
from django.utils import timezone

from config.urls import urlpatterns as project_urlpatterns

from accounts.models import UserProfile
from categories.models import Category

from .models import Listing
from .public_deals_seo_metadata_v298 import (
    PUBLIC_DEALS_META_DESCRIPTION_V298,
    PUBLIC_DEALS_SEO_METADATA_V298,
    PUBLIC_DEALS_SITE_NAME_V298,
    build_public_deals_seo_context_v298,
)


def v298_base_without_page_title(request):
    return render(
        request,
        "base.html",
        {},
    )


urlpatterns = [
    path(
        "__v298/base-without-page-title/",
        v298_base_without_page_title,
        name="v298_base_without_page_title",
    ),
    *project_urlpatterns,
]


@override_settings(
    ALLOWED_HOSTS=[
        "example.test",
        "testserver",
    ]
)
class PublicDealsSeoMetadataV298Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.seller = User.objects.create_user(
            username="v298-seo-seller",
            email="v298-seo-seller@example.test",
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=cls.seller
        )

        cls.category = Category.objects.create(
            name="V298 SEO Deals",
            slug="v298-seo-deals",
        )

        cls.now = timezone.now()

    def create_listing(
        self,
        title,
        *,
        price="1000.00",
    ):
        return Listing.objects.create(
            owner=self.seller,
            category=self.category,
            title=title,
            description=(
                f"{title} structured Deals fixture."
            ),
            price=Decimal(str(price)),
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=(
                self.now
                + timedelta(days=30)
            ),
        )

    @staticmethod
    def change_price(
        listing,
        price,
    ):
        listing.price = Decimal(str(price))
        listing.save(
            update_fields=["price"],
        )
        listing.refresh_from_db()

    def deals(
        self,
        params=None,
    ):
        return self.client.get(
            reverse(
                "listings:public_deals_v296"
            ),
            params or {},
            secure=True,
            HTTP_HOST="example.test",
        )

    @staticmethod
    def json_ld(response):
        return json.loads(
            response.context["seo_json_ld"]
        )

    def test_first_page_renders_complete_indexable_metadata(self):
        listing = self.create_listing(
            "V298 First Page Deal",
        )
        self.change_price(
            listing,
            "800.00",
        )

        response = self.deals()

        canonical_url = (
            "https://example.test/deals/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.context["page_title"],
            "Deals",
        )
        self.assertEqual(
            response.context["seo_title"],
            "Deals | Classifieds Local",
        )
        self.assertEqual(
            response.context["seo_description"],
            PUBLIC_DEALS_META_DESCRIPTION_V298,
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
                "public_deals_seo_metadata_v298"
            ]
        )

        self.assertContains(
            response,
            (
                "<title>"
                "Deals | Classifieds Local"
                "</title>"
            ),
            html=True,
        )
        self.assertContains(
            response,
            (
                '<meta name="description" '
                f'content="{PUBLIC_DEALS_META_DESCRIPTION_V298}">'
            ),
            html=True,
        )
        self.assertContains(
            response,
            (
                '<link rel="canonical" '
                f'href="{canonical_url}">'
            ),
            html=True,
        )
        self.assertContains(
            response,
            (
                '<meta name="robots" '
                'content="index,follow">'
            ),
            html=True,
        )
        self.assertContains(
            response,
            (
                '<script type="application/ld+json">'
            ),
        )

    def test_open_graph_and_twitter_metadata_match_canonical_page(self):
        response = self.deals()

        canonical_url = (
            "https://example.test/deals/"
        )

        expected_tags = (
            (
                '<meta property="og:type" '
                'content="website">'
            ),
            (
                '<meta property="og:site_name" '
                'content="Classifieds Local">'
            ),
            (
                '<meta property="og:title" '
                'content="Deals | Classifieds Local">'
            ),
            (
                '<meta property="og:description" '
                f'content="{PUBLIC_DEALS_META_DESCRIPTION_V298}">'
            ),
            (
                '<meta property="og:url" '
                f'content="{canonical_url}">'
            ),
            (
                '<meta name="twitter:card" '
                'content="summary">'
            ),
            (
                '<meta name="twitter:title" '
                'content="Deals | Classifieds Local">'
            ),
            (
                '<meta name="twitter:description" '
                f'content="{PUBLIC_DEALS_META_DESCRIPTION_V298}">'
            ),
        )

        for expected in expected_tags:
            with self.subTest(
                expected=expected
            ):
                self.assertContains(
                    response,
                    expected,
                    html=True,
                )

    def test_collection_page_json_ld_uses_public_listing_urls(self):
        first = self.create_listing(
            "V298 Structured First",
            price="1200.00",
        )
        second = self.create_listing(
            "V298 Structured Second",
            price="1000.00",
        )

        self.change_price(
            first,
            "600.00",
        )
        self.change_price(
            second,
            "800.00",
        )

        response = self.deals()
        payload = self.json_ld(response)

        self.assertEqual(
            payload["@context"],
            "https://schema.org",
        )
        self.assertEqual(
            payload["@type"],
            "CollectionPage",
        )
        self.assertEqual(
            payload["name"],
            "Deals",
        )
        self.assertEqual(
            payload["url"],
            "https://example.test/deals/",
        )
        self.assertEqual(
            payload["isPartOf"],
            {
                "@type": "WebSite",
                "name": (
                    PUBLIC_DEALS_SITE_NAME_V298
                ),
                "url": (
                    "https://example.test/"
                ),
            },
        )

        item_list = payload["mainEntity"]

        self.assertEqual(
            item_list["@type"],
            "ItemList",
        )
        self.assertEqual(
            item_list["numberOfItems"],
            2,
        )
        self.assertEqual(
            [
                element["position"]
                for element
                in item_list[
                    "itemListElement"
                ]
            ],
            [
                1,
                2,
            ],
        )
        self.assertEqual(
            item_list[
                "itemListElement"
            ][0]["name"],
            first.title,
        )
        self.assertEqual(
            item_list[
                "itemListElement"
            ][0]["url"],
            (
                "https://example.test"
                f"{first.get_absolute_url()}"
            ),
        )

    def test_second_page_has_normalized_canonical_and_global_positions(self):
        for index in range(13):
            listing = self.create_listing(
                f"V298 Paginated Deal {index:02d}",
            )
            self.change_price(
                listing,
                "500.00",
            )

        response = self.deals(
            {
                "page": "2",
            }
        )

        canonical_url = (
            "https://example.test/deals/?page=2"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.context["seo_title"],
            (
                "Deals – Page 2 "
                "| Classifieds Local"
            ),
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
        self.assertContains(
            response,
            (
                '<link rel="canonical" '
                f'href="{canonical_url}">'
            ),
            html=True,
        )

        payload = self.json_ld(response)

        self.assertEqual(
            payload["name"],
            "Deals – Page 2",
        )
        self.assertEqual(
            payload["url"],
            canonical_url,
        )
        self.assertEqual(
            payload["mainEntity"][
                "numberOfItems"
            ],
            13,
        )
        self.assertEqual(
            payload["mainEntity"][
                "itemListElement"
            ][0]["position"],
            13,
        )

    def test_noncanonical_parameters_are_noindex_but_keep_clean_canonical(self):
        listing = self.create_listing(
            "V298 Tracking Parameter Deal",
        )
        self.change_price(
            listing,
            "800.00",
        )

        response = self.deals(
            {
                "utm_source": "newsletter",
                "sort": "ignored",
            }
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.context[
                "seo_canonical_url"
            ],
            "https://example.test/deals/",
        )
        self.assertEqual(
            response.context["seo_robots"],
            "noindex,follow",
        )
        self.assertContains(
            response,
            (
                '<meta name="robots" '
                'content="noindex,follow">'
            ),
            html=True,
        )
        self.assertNotContains(
            response,
            "utm_source",
        )
        self.assertNotContains(
            response,
            "sort=ignored",
        )

    def test_redundant_page_one_is_noindex_and_canonicalizes_to_root(self):
        response = self.deals(
            {
                "page": "1",
            }
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.context[
                "seo_canonical_url"
            ],
            "https://example.test/deals/",
        )
        self.assertEqual(
            response.context["seo_robots"],
            "noindex,follow",
        )
        self.assertEqual(
            response.context["seo_title"],
            "Deals | Classifieds Local",
        )

    def test_json_ld_serialization_prevents_script_breakout(self):
        dangerous_title = (
            "V298 </script>"
            "<script>alert(1)</script>"
        )

        listing = self.create_listing(
            dangerous_title,
        )
        self.change_price(
            listing,
            "800.00",
        )

        response = self.deals()
        serialized = response.context[
            "seo_json_ld"
        ]
        payload = json.loads(
            serialized
        )

        self.assertNotIn(
            "</script>",
            serialized.lower(),
        )
        self.assertIn(
            "\\u003C/script\\u003E",
            serialized,
        )
        self.assertEqual(
            payload["mainEntity"][
                "itemListElement"
            ][0]["name"],
            dangerous_title,
        )

        html = response.content.decode(
            response.charset or "utf-8"
        )

        self.assertEqual(
            html.count(
                '<script type="application/ld+json">'
            ),
            1,
        )

    def test_empty_deals_page_has_valid_empty_collection(self):
        response = self.deals()
        payload = self.json_ld(response)

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            payload["mainEntity"][
                "numberOfItems"
            ],
            0,
        )
        self.assertEqual(
            payload["mainEntity"][
                "itemListElement"
            ],
            [],
        )
        self.assertEqual(
            response.context["seo_robots"],
            "index,follow",
        )

    def test_metadata_builder_performs_no_database_query(self):
        listing = self.create_listing(
            "V298 Query-free Metadata",
        )
        self.change_price(
            listing,
            "800.00",
        )

        loaded_listing = (
            Listing.objects
            .get(pk=listing.pk)
        )

        page_obj = Paginator(
            [
                loaded_listing,
            ],
            12,
        ).page(1)

        request = RequestFactory().get(
            "/deals/",
            secure=True,
            HTTP_HOST="example.test",
        )

        with CaptureQueriesContext(
            connection
        ) as captured:
            context = (
                build_public_deals_seo_context_v298(
                    request=request,
                    page_obj=page_obj,
                    listings=page_obj.object_list,
                )
            )

        self.assertEqual(
            len(captured),
            0,
        )
        self.assertEqual(
            context["seo_robots"],
            "index,follow",
        )

    @override_settings(
        ROOT_URLCONF=__name__,
    )
    def test_base_template_falls_back_when_page_title_is_missing(self):
        response = self.client.get(
            "/__v298/base-without-page-title/",
            secure=True,
            HTTP_HOST="example.test",
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "<title>Classifieds Local</title>",
            html=True,
        )
        self.assertNotContains(
            response,
            '<meta name="description"',
        )
        self.assertNotContains(
            response,
            '<link rel="canonical"',
        )
        self.assertNotContains(
            response,
            'type="application/ld+json"',
        )

    def test_base_template_remains_opt_in_for_non_seo_pages(self):
        response = self.client.get(
            reverse(
                "listings:listing_list"
            ),
            secure=True,
            HTTP_HOST="example.test",
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertNotContains(
            response,
            '<meta name="description"',
        )
        self.assertNotContains(
            response,
            '<link rel="canonical"',
        )
        self.assertNotContains(
            response,
            '<meta name="robots"',
        )
        self.assertNotContains(
            response,
            'property="og:',
        )
        self.assertNotContains(
            response,
            'name="twitter:',
        )
        self.assertNotContains(
            response,
            'type="application/ld+json"',
        )

    def test_v298_contract_adds_no_route_model_or_migration(self):
        backend_root = Path(
            settings.BASE_DIR
        )

        helper_source = (
            backend_root
            / "listings"
            / "public_deals_seo_metadata_v298.py"
        ).read_text(
            encoding="utf-8",
        )

        base_source = (
            backend_root
            / "templates"
            / "base.html"
        ).read_text(
            encoding="utf-8",
        )

        root_urls_source = (
            backend_root
            / "config"
            / "urls.py"
        ).read_text(
            encoding="utf-8",
        )

        listings_urls_source = (
            backend_root
            / "listings"
            / "urls.py"
        ).read_text(
            encoding="utf-8",
        )

        migration_directory = (
            backend_root
            / "listings"
            / "migrations"
        )

        self.assertTrue(
            PUBLIC_DEALS_SEO_METADATA_V298
        )
        self.assertIn(
            "CollectionPage",
            helper_source,
        )
        self.assertIn(
            "ItemList",
            helper_source,
        )
        self.assertIn(
            "request.build_absolute_uri",
            helper_source,
        )
        self.assertIn(
            "OPTIONAL_SEO_METADATA_V298",
            base_source,
        )
        self.assertNotIn(
            "sitemap",
            root_urls_source.lower(),
        )
        self.assertNotIn(
            "robots",
            root_urls_source.lower(),
        )
        self.assertNotIn(
            "sitemap",
            listings_urls_source.lower(),
        )
        self.assertNotIn(
            "robots",
            listings_urls_source.lower(),
        )
        self.assertEqual(
            list(
                migration_directory.glob(
                    "*v298*"
                )
            ),
            [],
        )
