from __future__ import annotations

import importlib
import inspect
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from categories.public_browse_mount_v187 import (
    V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT_MARKER,
    V187_MOUNTED_TEMPLATE_PROJECT_PATHS,
)


V189_SELLER_STORE_CATEGORY_COMPAT_MARKER = "V189_SELLER_STORE_CATEGORY_COMPATIBILITY_POLISH"


class SellerStoreCategoryCompatibilityV189Tests(SimpleTestCase):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _test_method_names(self, module_name: str) -> set[str]:
        module = importlib.import_module(module_name)
        method_names: set[str] = set()

        for _class_name, test_class in inspect.getmembers(module, inspect.isclass):
            if not test_class.__name__.endswith("Tests"):
                continue

            for method_name in dir(test_class):
                if method_name.startswith("test_"):
                    method_names.add(method_name)

        self.assertTrue(
            method_names,
            f"{module_name} did not expose any unittest-style test methods.",
        )

        return method_names

    def _assert_module_has_test_fragments(
        self,
        module_name: str,
        expected_fragments: tuple[str, ...],
    ) -> None:
        method_names = self._test_method_names(module_name)

        for fragment in expected_fragments:
            self.assertTrue(
                any(fragment in method_name for method_name in method_names),
                f"{module_name} is missing expected seller-store compatibility coverage fragment `{fragment}`. "
                f"Available tests: {sorted(method_names)}",
            )

    def test_v189_marker_is_declared_for_seller_store_category_compatibility(self):
        self.assertEqual(
            V189_SELLER_STORE_CATEGORY_COMPAT_MARKER,
            "V189_SELLER_STORE_CATEGORY_COMPATIBILITY_POLISH",
        )

    def test_v189_existing_seller_store_category_tabs_coverage_remains_present(self):
        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_category_tabs",
            (
                "category_tabs_render_counts",
                "selected_category_tab_is_marked_active",
                "pagination_preserves_selected_category",
                "search_and_category_tabs_work_together",
                "all_listings_tab_clears_category",
            ),
        )

    def test_v189_existing_seller_store_directory_category_discovery_coverage_remains_present(self):
        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_directory_category_discovery",
            (
                "category_discovery_chips_render",
                "category_filter_includes_child_category_listings",
                "category_filter_is_preserved_in_pagination_and_sort_urls",
                "category_filter_limits_directory",
                "invalid_category_slug_is_ignored",
            ),
        )

    def test_v189_existing_seller_store_saved_search_cta_coverage_remains_present(self):
        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_directory_saved_search_cta",
            (
                "anonymous_saved_search_cta_prompts_login",
                "authenticated_saved_search_cta_links",
                "saved_search_cta_renders_for_active_search",
                "saved_search_cta_renders_for_sort_only_state",
            ),
        )

        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_directory_saved_search_create_integration",
            (
                "authenticated_directory_cta_renders_direct_save_form",
                "post_creates_seller_store_directory_saved_search_with_path",
                "seller_store_saved_search_dedupes_by_path",
                "already_saved_directory_search_shows_saved_state",
            ),
        )

        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_directory_saved_search_result_count_preview",
            (
                "active_filter_state_shows_result_count_preview",
                "already_saved_state_shows_same_result_count_preview",
                "zero_match_state_keeps_saved_search_count_preview",
            ),
        )

    def test_v189_existing_seller_store_sorting_and_pagination_coverage_remains_present(self):
        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_directory_sorting",
            (
                "directory_sort_ui_renders_options",
                "pagination_preserves_sort_and_directory_filters",
                "invalid_sort_falls_back",
                "verified_first_sort_orders",
            ),
        )

        self._assert_module_has_test_fragments(
            "accounts.tests.test_seller_store_sorting",
            (
                "category_tab_urls_preserve_search_and_sort_but_drop_page",
                "pagination_preserves_query_category_and_sort",
                "invalid_sort_falls_back",
                "price_ascending_sort",
                "price_descending_sort",
            ),
        )

    def test_v189_v187_public_browse_mount_scope_does_not_expand_to_seller_store(self):
        self.assertEqual(
            V187_MOUNTED_TEMPLATE_PROJECT_PATHS,
            ("listings/templates/listings/listing_list.html",),
        )

        mounted_template = self._backend_root() / V187_MOUNTED_TEMPLATE_PROJECT_PATHS[0]
        self.assertTrue(mounted_template.exists())

        mounted_text = mounted_template.read_text(encoding="utf-8", errors="ignore")

        self.assertIn(V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT_MARKER, mounted_text)
        self.assertIn("render_category_navigation_v186", mounted_text)

    def test_v189_public_browse_navigation_tag_does_not_leak_into_seller_store_templates(self):
        candidate_roots = (
            self._backend_root() / "accounts" / "templates",
            self._backend_root() / "templates" / "accounts",
        )

        template_paths: list[Path] = []
        for root in candidate_roots:
            if root.exists():
                template_paths.extend(root.rglob("*.html"))

        seller_store_templates = [
            path
            for path in template_paths
            if "store" in path.as_posix().lower() or "seller" in path.as_posix().lower()
        ]

        self.assertTrue(
            seller_store_templates,
            "No seller/store templates were found for v189 leak-scope verification.",
        )

        for path in seller_store_templates:
            text = path.read_text(encoding="utf-8", errors="ignore")

            self.assertNotIn(
                "V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT",
                text,
                f"Public browse category mount leaked into seller/store template: {path}",
            )
            self.assertNotIn(
                "render_category_navigation_v186",
                text,
                f"Public browse navigation tag leaked into seller/store template: {path}",
            )

    def test_v189_v188_saved_search_category_guard_remains_present(self):
        v188_test = self._backend_root() / "listings" / "test_saved_search_category_compat_v188.py"
        self.assertTrue(v188_test.exists())

        text = v188_test.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V188_SAVED_SEARCH_CATEGORY_COMPATIBILITY_POLISH", text)
        self.assertIn("test_v188_saved_search_create_preserves_category_query", text)
        self.assertIn("test_v188_category_filter_url_preserves_saved_search_safe_state", text)
        self.assertIn("test_v188_category_browse_pagination_keeps_safe_query_params", text)
