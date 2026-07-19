"""
PUBLIC_DEALS_DISCOVERY_INTEGRATION_RELEASE_AUDIT_V299

Integration and release-readiness contracts for the public Deals discovery
surface introduced in v296 and extended through v297-v298.
"""

from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from .listing_comparison_discount_v297 import (
    DEAL_AWARE_LISTING_COMPARISON_V297,
)
from .public_deals_landing_page_v296 import (
    PUBLIC_DEALS_LANDING_PAGE_V296,
    PublicDealsListViewV296,
)
from .public_deals_seo_metadata_v298 import (
    PUBLIC_DEALS_SEO_METADATA_V298,
)


PUBLIC_DEALS_DISCOVERY_INTEGRATION_RELEASE_AUDIT_V299 = True


class _MainNavigationParserV299(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main_navigation = False
        self.current_link = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        if (
            tag == "nav"
            and attributes.get("aria-label")
            == "Main navigation"
        ):
            self.in_main_navigation = True
            return

        if (
            self.in_main_navigation
            and tag == "a"
        ):
            self.current_link = {
                "attrs": attributes,
                "text": [],
            }

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link["text"].append(data)

    def handle_endtag(self, tag):
        if (
            tag == "a"
            and self.current_link is not None
        ):
            self.current_link["text"] = (
                "".join(
                    self.current_link["text"]
                ).strip()
            )
            self.links.append(
                self.current_link
            )
            self.current_link = None
            return

        if (
            tag == "nav"
            and self.in_main_navigation
        ):
            self.in_main_navigation = False


class PublicDealsDiscoveryIntegrationReleaseAuditV299Tests(
    TestCase
):
    def main_navigation_link(
        self,
        response,
        label,
    ):
        parser = _MainNavigationParserV299()
        parser.feed(
            response.content.decode("utf-8")
        )

        matches = [
            link
            for link in parser.links
            if link["text"] == label
        ]

        self.assertEqual(
            len(matches),
            1,
        )

        return matches[0]

    def assert_current_deals_link(
        self,
        response,
    ):
        link = self.main_navigation_link(
            response,
            "Deals",
        )
        classes = (
            link["attrs"]
            .get("class", "")
            .split()
        )

        self.assertEqual(
            link["attrs"].get("href"),
            reverse(
                "listings:public_deals_v296"
            ),
        )
        self.assertEqual(
            link["attrs"].get("aria-current"),
            "page",
        )
        self.assertIn(
            "header-nav-deals-v299",
            classes,
        )
        self.assertIn(
            "is-current-v299",
            classes,
        )

    def test_anonymous_deals_navigation_is_current(self):
        response = self.client.get(
            reverse(
                "listings:public_deals_v296"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assert_current_deals_link(
            response
        )

    def test_authenticated_deals_navigation_is_current(self):
        user = get_user_model().objects.create_user(
            username="v299-navigation-user",
            password="test-pass-v299",
        )
        self.client.force_login(
            user
        )

        response = self.client.get(
            reverse(
                "listings:public_deals_v296"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assert_current_deals_link(
            response
        )

    def test_non_deals_pages_do_not_mark_deals_current(self):
        for route_name in (
            "listings:listing_list",
            "listings:listing_compare",
        ):
            with self.subTest(
                route_name=route_name
            ):
                response = self.client.get(
                    reverse(route_name)
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                link = self.main_navigation_link(
                    response,
                    "Deals",
                )
                classes = (
                    link["attrs"]
                    .get("class", "")
                    .split()
                )

                self.assertIn(
                    "header-nav-deals-v299",
                    classes,
                )
                self.assertNotIn(
                    "is-current-v299",
                    classes,
                )
                self.assertNotIn(
                    "aria-current",
                    link["attrs"],
                )

    def test_deals_and_comparison_keep_discovery_ctas(self):
        deals_url = reverse(
            "listings:public_deals_v296"
        )
        browse_url = reverse(
            "listings:listing_list"
        )

        deals_response = self.client.get(
            deals_url
        )
        comparison_response = self.client.get(
            reverse(
                "listings:listing_compare"
            )
        )

        self.assertEqual(
            deals_response.status_code,
            200,
        )
        self.assertEqual(
            comparison_response.status_code,
            200,
        )

        deals_html = (
            deals_response.content.decode(
                "utf-8"
            )
        )
        comparison_html = (
            comparison_response.content.decode(
                "utf-8"
            )
        )

        self.assertGreaterEqual(
            deals_html.count(
                f'href="{browse_url}"'
            ),
            3,
        )
        self.assertEqual(
            comparison_html.count(
                f'href="{deals_url}"'
            ),
            3,
        )
        self.assertIn(
            "Browse all listings",
            deals_html,
        )
        self.assertIn(
            "Browse deals",
            comparison_html,
        )

    @override_settings(
        ALLOWED_HOSTS=["testserver", "example.test"],
    )
    def test_navigation_and_seo_share_deals_identity(self):
        deals_url = reverse(
            "listings:public_deals_v296"
        )

        response = self.client.get(
            deals_url,
            secure=True,
            HTTP_HOST="example.test",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        link = self.main_navigation_link(
            response,
            "Deals",
        )

        self.assertEqual(
            link["attrs"].get("href"),
            deals_url,
        )
        self.assertEqual(
            response.context[
                "seo_canonical_url"
            ],
            "https://example.test/deals/",
        )
        self.assertEqual(
            response.context["seo_robots"],
            "index,follow",
        )

    def test_shared_header_packages_active_focus_and_responsive_contract(self):
        base_source = (
            Path(settings.BASE_DIR)
            / "templates"
            / "base.html"
        ).read_text(
            encoding="utf-8",
        )

        required_terms = (
            "PUBLIC_DEALS_DISCOVERY_INTEGRATION_V299",
            "header-nav-deals-v299",
            "is-current-v299",
            'aria-current="page"',
            "public_deals_v296",
            ".header-nav a:focus-visible",
            ".header-nav summary:focus-visible",
            "@media (max-width: 720px)",
            "flex: 1 1 auto",
        )

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    base_source,
                )

        self.assertNotIn(
            'href="/deals/"',
            base_source,
        )

    def test_v296_v297_v298_markers_and_route_remain_connected(self):
        deals_url = reverse(
            "listings:public_deals_v296"
        )
        match = resolve(
            deals_url
        )

        self.assertTrue(
            PUBLIC_DEALS_LANDING_PAGE_V296
        )
        self.assertTrue(
            DEAL_AWARE_LISTING_COMPARISON_V297
        )
        self.assertTrue(
            PUBLIC_DEALS_SEO_METADATA_V298
        )
        self.assertTrue(
            PUBLIC_DEALS_DISCOVERY_INTEGRATION_RELEASE_AUDIT_V299
        )
        self.assertEqual(
            match.func.view_class,
            PublicDealsListViewV296,
        )

    def test_prior_release_safety_contracts_remain_packaged(self):
        listings_root = (
            Path(settings.BASE_DIR)
            / "listings"
        )

        v296_source = (
            listings_root
            / "test_public_deals_landing_page_v296.py"
        ).read_text(
            encoding="utf-8",
        )
        v297_source = (
            listings_root
            / "test_deal_aware_listing_comparison_v297.py"
        ).read_text(
            encoding="utf-8",
        )
        v298_source = (
            listings_root
            / "test_public_deals_seo_metadata_v298.py"
        ).read_text(
            encoding="utf-8",
        )

        required_contracts = (
            (
                v296_source,
                "test_pagination_uses_twelve_deals_and_semantic_navigation",
            ),
            (
                v296_source,
                "test_page_query_count_does_not_grow_per_card",
            ),
            (
                v297_source,
                "test_v297_comparison_query_count_does_not_grow_per_listing",
            ),
            (
                v298_source,
                "test_base_template_falls_back_when_page_title_is_missing",
            ),
            (
                v298_source,
                "CaptureQueriesContext",
            ),
            (
                v298_source,
                "application/ld+json",
            ),
        )

        for source, contract in required_contracts:
            with self.subTest(
                contract=contract
            ):
                self.assertIn(
                    contract,
                    source,
                )

    def test_v299_adds_no_route_model_or_migration(self):
        backend_root = Path(
            settings.BASE_DIR
        )

        listings_urls_source = (
            backend_root
            / "listings"
            / "urls.py"
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
        models_source = (
            backend_root
            / "listings"
            / "models.py"
        ).read_text(
            encoding="utf-8",
        )
        migration_directory = (
            backend_root
            / "listings"
            / "migrations"
        )

        self.assertNotIn(
            "v299",
            listings_urls_source.lower(),
        )
        self.assertNotIn(
            "v299",
            root_urls_source.lower(),
        )
        self.assertNotIn(
            "v299",
            models_source.lower(),
        )
        self.assertEqual(
            list(
                migration_directory.glob(
                    "*v299*"
                )
            ),
            [],
        )
        self.assertEqual(
            len(
                list(
                    migration_directory.glob(
                        "0023_listingpricehistory_discount_guardrail_v293.py"
                    )
                )
            ),
            1,
        )
