"""
PUBLIC_DEALS_SPRINT_CLOSEOUT_AUDIT_V300

Final read-only closeout contracts for the public Deals sprint completed
through v296-v299.
"""

import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
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
from .test_public_deals_discovery_integration_release_audit_v299 import (
    PUBLIC_DEALS_DISCOVERY_INTEGRATION_RELEASE_AUDIT_V299,
)


PUBLIC_DEALS_SPRINT_CLOSEOUT_AUDIT_V300 = True


class PublicDealsSprintCloseoutAuditV300Tests(
    SimpleTestCase
):
    @property
    def backend_root(self):
        return Path(settings.BASE_DIR)

    @property
    def listings_root(self):
        return self.backend_root / "listings"

    def read_backend(self, relative_path):
        return (
            self.backend_root
            / relative_path
        ).read_text(
            encoding="utf-8",
        )

    def test_v296_v300_markers_and_single_route_remain_connected(self):
        deals_url = reverse(
            "listings:public_deals_v296"
        )
        match = resolve(
            deals_url
        )

        self.assertEqual(
            deals_url,
            "/deals/",
        )
        self.assertEqual(
            match.func.view_class,
            PublicDealsListViewV296,
        )

        for marker in (
            PUBLIC_DEALS_LANDING_PAGE_V296,
            DEAL_AWARE_LISTING_COMPARISON_V297,
            PUBLIC_DEALS_SEO_METADATA_V298,
            PUBLIC_DEALS_DISCOVERY_INTEGRATION_RELEASE_AUDIT_V299,
            PUBLIC_DEALS_SPRINT_CLOSEOUT_AUDIT_V300,
        ):
            with self.subTest(marker=marker):
                self.assertTrue(marker)

        urls_source = self.read_backend(
            "listings/urls.py"
        )

        self.assertEqual(
            urls_source.count(
                'name="public_deals_v296"'
            ),
            1,
        )
        self.assertEqual(
            urls_source.count(
                "PublicDealsListViewV296.as_view()"
            ),
            1,
        )

    def test_sprint_test_package_contains_exactly_43_prior_contracts(self):
        expected_counts = {
            "test_public_deals_landing_page_v296.py": 12,
            "test_deal_aware_listing_comparison_v297.py": 10,
            "test_public_deals_seo_metadata_v298.py": 12,
            (
                "test_public_deals_discovery_"
                "integration_release_audit_v299.py"
            ): 9,
        }

        total = 0

        for filename, expected_count in expected_counts.items():
            source = (
                self.listings_root
                / filename
            ).read_text(
                encoding="utf-8",
            )
            actual_count = source.count(
                "    def test_"
            )

            with self.subTest(filename=filename):
                self.assertEqual(
                    actual_count,
                    expected_count,
                )

            total += actual_count

        self.assertEqual(
            total,
            43,
        )

    def test_sprint_tests_preserve_key_release_contracts(self):
        sources = {
            filename: (
                self.listings_root
                / filename
            ).read_text(
                encoding="utf-8",
            )
            for filename in (
                "test_public_deals_landing_page_v296.py",
                "test_deal_aware_listing_comparison_v297.py",
                "test_public_deals_seo_metadata_v298.py",
                (
                    "test_public_deals_discovery_"
                    "integration_release_audit_v299.py"
                ),
            )
        }

        required_contracts = (
            (
                "test_public_deals_landing_page_v296.py",
                "test_pagination_uses_twelve_deals_and_semantic_navigation",
            ),
            (
                "test_public_deals_landing_page_v296.py",
                "test_page_query_count_does_not_grow_per_card",
            ),
            (
                "test_deal_aware_listing_comparison_v297.py",
                "test_v297_comparison_query_count_does_not_grow_per_listing",
            ),
            (
                "test_public_deals_seo_metadata_v298.py",
                "test_json_ld_serialization_prevents_script_breakout",
            ),
            (
                "test_public_deals_seo_metadata_v298.py",
                "test_metadata_builder_performs_no_database_query",
            ),
            (
                (
                    "test_public_deals_discovery_"
                    "integration_release_audit_v299.py"
                ),
                "test_non_deals_pages_do_not_mark_deals_current",
            ),
            (
                (
                    "test_public_deals_discovery_"
                    "integration_release_audit_v299.py"
                ),
                "test_v299_adds_no_route_model_or_migration",
            ),
        )

        for filename, contract in required_contracts:
            with self.subTest(
                filename=filename,
                contract=contract,
            ):
                self.assertIn(
                    contract,
                    sources[filename],
                )

    def test_sprint_milestone_sources_remain_versioned(self):
        required_markers = {
            "public_deals_landing_page_v296.py": (
                "PUBLIC_DEALS_LANDING_PAGE_V296",
                "PublicDealsListViewV296",
            ),
            "listing_comparison_discount_v297.py": (
                "DEAL_AWARE_LISTING_COMPARISON_V297",
            ),
            "public_deals_seo_metadata_v298.py": (
                "PUBLIC_DEALS_SEO_METADATA_V298",
            ),
            (
                "test_public_deals_discovery_"
                "integration_release_audit_v299.py"
            ): (
                (
                    "PUBLIC_DEALS_DISCOVERY_INTEGRATION_"
                    "RELEASE_AUDIT_V299"
                ),
                "release-readiness",
            ),
        }

        for filename, required_terms in required_markers.items():
            source = (
                self.listings_root
                / filename
            ).read_text(
                encoding="utf-8",
            )

            for term in required_terms:
                with self.subTest(
                    filename=filename,
                    term=term,
                ):
                    self.assertIn(
                        term,
                        source,
                    )

    def test_shared_deals_identity_remains_consistent(self):
        base_source = self.read_backend(
            "templates/base.html"
        )
        comparison_source = self.read_backend(
            (
                "listings/templates/listings/"
                "listing_comparison_v274.html"
            )
        )
        seo_source = self.read_backend(
            "listings/public_deals_seo_metadata_v298.py"
        )

        self.assertIn(
            (
                "{% safe_url "
                "'listings:public_deals_v296' "
                "as nav_deals_url %}"
            ),
            base_source,
        )
        self.assertIn(
            'aria-current="page"',
            base_source,
        )
        self.assertGreaterEqual(
            comparison_source.count(
                "{% url 'listings:public_deals_v296' %}"
            ),
            2,
        )
        self.assertIn(
            '"listings:public_deals_v296"',
            seo_source,
        )

    def test_sprint_implementation_package_remains_present(self):
        required_paths = (
            "listings/public_deals_landing_page_v296.py",
            "listings/listing_comparison_discount_v297.py",
            "listings/public_deals_seo_metadata_v298.py",
            (
                "listings/templates/listings/"
                "public_deals_landing_page_v296.html"
            ),
            (
                "listings/templates/listings/"
                "listing_comparison_v274.html"
            ),
            "templates/base.html",
        )

        for relative_path in required_paths:
            with self.subTest(
                relative_path=relative_path
            ):
                self.assertTrue(
                    (
                        self.backend_root
                        / relative_path
                    ).is_file()
                )

    def test_v300_adds_no_route_model_or_migration(self):
        urls_source = self.read_backend(
            "listings/urls.py"
        )
        root_urls_source = self.read_backend(
            "config/urls.py"
        )
        models_source = self.read_backend(
            "listings/models.py"
        )
        migration_directory = (
            self.listings_root
            / "migrations"
        )

        self.assertNotIn(
            "v300",
            urls_source.lower(),
        )
        self.assertNotIn(
            "v300",
            root_urls_source.lower(),
        )
        self.assertNotIn(
            "v300",
            models_source.lower(),
        )
        self.assertEqual(
            list(
                migration_directory.glob(
                    "*v300*"
                )
            ),
            [],
        )
        self.assertTrue(
            (
                migration_directory
                / (
                    "0023_listingpricehistory_"
                    "discount_guardrail_v293.py"
                )
            ).is_file()
        )

    def test_closeout_audit_remains_read_only_and_self_describing(self):
        source = (
            self.listings_root
            / "test_public_deals_sprint_closeout_audit_v300.py"
        ).read_text(
            encoding="utf-8",
        )

        required_terms = (
            "PUBLIC_DEALS_SPRINT_CLOSEOUT_AUDIT_V300",
            "from django.test import SimpleTestCase",
            (
                "test_sprint_test_package_contains_"
                "exactly_43_prior_contracts"
            ),
            "test_v300_adds_no_route_model_or_migration",
            "test_shared_deals_identity_remains_consistent",
        )

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

        tree = ast.parse(source)

        model_imports = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 1
                and node.module == "models"
            )
        ]
        orm_manager_accesses = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "objects"
            )
        ]
        client_accesses = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "client"
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            )
        ]

        self.assertEqual(
            model_imports,
            [],
        )
        self.assertEqual(
            orm_manager_accesses,
            [],
        )
        self.assertEqual(
            client_accesses,
            [],
        )
