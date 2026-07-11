from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase


V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_MARKER = (
    "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH"
)


class SellerStorePublicPageResponsivePolishV198Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _public_store_template_candidates(self) -> list[Path]:
        roots = (
            self._backend_root() / "accounts" / "templates" / "accounts",
            self._backend_root() / "templates" / "accounts",
            self._backend_root() / "accounts" / "templates",
        )

        candidates: list[tuple[int, Path]] = []

        for root in roots:
            if not root.exists():
                continue

            for path in root.rglob("*.html"):
                text = path.read_text(encoding="utf-8", errors="ignore")
                lowered = text.lower()
                posix = path.as_posix().lower()

                score = 0

                if V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_MARKER in text:
                    score += 100
                if "seller_store_detail" in posix:
                    score += 40
                if "seller_store" in posix and "directory" not in posix:
                    score += 25
                if "seller store" in lowered:
                    score += 10
                if "store listings" in lowered or "seller listings" in lowered:
                    score += 8
                if "directory" in posix or "directory" in lowered:
                    score -= 80
                if "form" in posix or "edit" in posix or "create" in posix or "settings" in posix:
                    score -= 40

                if score > 0:
                    candidates.append((score, path))

        candidates.sort(key=lambda item: (-item[0], item[1].as_posix()))

        return [path for _score, path in candidates]

    def _public_store_template_path(self) -> Path:
        candidates = self._public_store_template_candidates()
        self.assertTrue(candidates, "No public seller-store template candidates were discovered.")
        return candidates[0]

    def _seller_store_directory_template_path(self) -> Path:
        return (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )

    def _saved_search_management_template_path(self) -> Path:
        return (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / "saved_search_list.html"
        )

    def _category_admin_path(self) -> Path:
        return self._backend_root() / "categories" / "admin.py"

    def _category_navigation_partial_path(self) -> Path:
        return self._backend_root() / "templates" / "categories" / "_category_navigation_v186.html"

    def test_v198_marker_is_declared_for_public_seller_store_responsive_polish(self):
        self.assertEqual(
            V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_MARKER,
            "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH",
        )

    def test_v198_public_seller_store_template_contains_responsive_guidance(self):
        text = self._public_store_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", text)
        self.assertIn("seller-store-public-responsive-v198", text)
        self.assertIn('data-v198-seller-store-public-responsive="true"', text)
        self.assertIn('aria-label="Seller store public page browsing guidance"', text)
        self.assertIn('aria-label="Seller store page responsive browsing tips"', text)
        self.assertIn("Browse this seller store comfortably on any screen", text)
        self.assertIn(
            "Store details, active listings, filters, and pagination stay easier to scan as the page adapts to smaller screens.",
            text,
        )
        self.assertIn("Scan the store first", text)
        self.assertIn("Use the seller details and listing summary to understand what this store offers.", text)
        self.assertIn("Refine the listings", text)
        self.assertIn("Search, category, sorting, and pagination controls remain connected while browsing.", text)
        self.assertIn("Read clearly on mobile", text)
        self.assertIn("Helpful sections collapse into a single-column flow for smaller screens.", text)

    def test_v198_public_seller_store_template_contains_mobile_css_contract(self):
        text = self._public_store_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("@media (max-width: 820px)", text)
        self.assertIn("@media (max-width: 520px)", text)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", text)
        self.assertIn("grid-template-columns: 1fr;", text)
        self.assertIn("seller-store-public-responsive-v198__grid", text)
        self.assertIn("seller-store-public-responsive-v198__item", text)

    def test_v198_does_not_touch_directory_saved_search_category_admin_or_category_nav(self):
        directory = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        saved_search = self._saved_search_management_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        category_admin = self._category_admin_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        category_nav = self._category_navigation_partial_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", directory)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search)
        self.assertIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", category_admin)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav)

        for text in (directory, saved_search, category_admin, category_nav):
            self.assertNotIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", text)
            self.assertNotIn("seller-store-public-responsive-v198", text)
            self.assertNotIn("Browse this seller store comfortably on any screen", text)

    def test_v198_public_store_template_does_not_receive_saved_search_admin_or_directory_hooks(self):
        text = self._public_store_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", text)
        self.assertNotIn("saved-search-notification-settings-v197", text)
        self.assertNotIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)
        self.assertNotIn("v196_parent_path", text)
        self.assertNotIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", text)
        self.assertNotIn("seller-store-directory-responsive-v195", text)
        self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)
        self.assertNotIn("category-navigation-v193-keyboard-ready", text)

    def test_v198_existing_checkpoint_guards_remain_present(self):
        v195_test = (
            self._backend_root()
            / "accounts"
            / "tests"
            / "test_seller_store_directory_responsive_polish_v195.py"
        )
        v196_test = self._backend_root() / "categories" / "test_category_taxonomy_admin_ux_polish_v196.py"
        v197_test = self._backend_root() / "listings" / "test_saved_search_notification_settings_polish_v197.py"

        self.assertTrue(v195_test.exists())
        self.assertTrue(v196_test.exists())
        self.assertTrue(v197_test.exists())

        self.assertIn(
            "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
            v195_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH",
            v196_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH",
            v197_test.read_text(encoding="utf-8", errors="ignore"),
        )
