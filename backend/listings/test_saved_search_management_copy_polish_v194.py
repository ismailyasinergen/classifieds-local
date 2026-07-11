from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, reverse


V194_SAVED_SEARCH_MANAGEMENT_COPY_MARKER = "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH"


class SavedSearchManagementCopyPolishV194Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(
            username="v194-saved-search-management-user",
            email="v194-saved-search-management-user@example.com",
            password="test-password",
        )

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _saved_search_template_candidates(self) -> list[Path]:
        roots = (
            self._backend_root() / "listings" / "templates",
            self._backend_root() / "templates" / "listings",
            self._backend_root() / "templates",
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
                if V194_SAVED_SEARCH_MANAGEMENT_COPY_MARKER in text:
                    score += 100
                if "saved" in posix and "search" in posix:
                    score += 30
                if "saved searches" in lowered:
                    score += 12
                if "saved search" in lowered:
                    score += 8
                if "seller" in lowered and "store" in lowered:
                    score -= 50
                if "render_category_navigation_v186" in lowered:
                    score -= 50

                if score > 0:
                    candidates.append((score, path))

        candidates.sort(key=lambda item: (-item[0], item[1].as_posix()))

        return [path for _score, path in candidates]

    def _saved_search_management_template_path(self) -> Path:
        candidates = self._saved_search_template_candidates()
        self.assertTrue(candidates, "No saved-search management template candidates were discovered.")
        return candidates[0]

    def _saved_search_management_url(self) -> str:
        candidates = (
            "listings:saved_search_list",
            "listings:saved_searches",
            "listings:saved_search_management",
            "saved_search_list",
            "saved_searches",
            "saved_search_management",
        )

        for name in candidates:
            try:
                return reverse(name)
            except NoReverseMatch:
                continue

        return "/listings/saved-searches/"

    def _get_saved_search_management_content(self):
        self.client.force_login(self.user)
        response = self.client.get(self._saved_search_management_url())
        content = response.content.decode("utf-8", errors="ignore")
        return response, content

    def test_v194_marker_is_declared_for_saved_search_management_copy(self):
        self.assertEqual(
            V194_SAVED_SEARCH_MANAGEMENT_COPY_MARKER,
            "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH",
        )

    def test_v194_saved_search_management_template_contains_copy_and_empty_guidance(self):
        text = self._saved_search_management_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", text)
        self.assertIn("saved-search-management-copy-v194", text)
        self.assertIn("saved-search-empty-guidance-v194", text)
        self.assertIn('data-v194-saved-search-management-copy="true"', text)
        self.assertIn('data-v194-saved-search-empty-guidance="true"', text)
        self.assertIn('aria-label="Saved search management guidance"', text)
        self.assertIn('aria-label="No saved searches guidance"', text)
        self.assertIn("Manage saved searches with confidence", text)
        self.assertIn(
            "Review the searches you follow, rename them when your intent changes, and remove searches you no longer need.",
            text,
        )
        self.assertIn("Use clear names so each saved search is easy to recognize later.", text)
        self.assertIn("Check the filter summary before reopening a search.", text)
        self.assertIn("Delete stale searches to keep this page focused.", text)
        self.assertIn("No saved searches yet", text)
        self.assertIn(
            "Start from a filtered browse page, then save the search to return to those listings faster next time.",
            text,
        )

    def test_v194_empty_saved_search_management_page_renders_new_guidance(self):
        response, content = self._get_saved_search_management_content()

        self.assertEqual(response.status_code, 200)
        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", content)
        self.assertIn('data-v194-saved-search-management-copy="true"', content)
        self.assertIn('aria-label="Saved search management guidance"', content)
        self.assertIn("Manage saved searches with confidence", content)
        self.assertIn("Delete stale searches to keep this page focused.", content)

        self.assertIn('data-v194-saved-search-empty-guidance="true"', content)
        self.assertIn('aria-label="No saved searches guidance"', content)
        self.assertIn("No saved searches yet", content)
        self.assertIn(
            "Start from a filtered browse page, then save the search to return to those listings faster next time.",
            content,
        )

    def test_v194_category_navigation_and_seller_store_templates_are_untouched(self):
        category_partial = (
            self._backend_root()
            / "templates"
            / "categories"
            / "_category_navigation_v186.html"
        )
        listing_browse = (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / "listing_list.html"
        )
        seller_store_directory = (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )

        category_text = category_partial.read_text(encoding="utf-8", errors="ignore")
        listing_text = listing_browse.read_text(encoding="utf-8", errors="ignore")
        seller_text = seller_store_directory.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_text)
        self.assertIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", listing_text)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", seller_text)

        for text in (category_text, listing_text, seller_text):
            self.assertNotIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", text)
            self.assertNotIn("saved-search-management-copy-v194", text)
            self.assertNotIn("saved-search-empty-guidance-v194", text)

    def test_v194_saved_search_template_does_not_receive_category_or_seller_store_hooks(self):
        text = self._saved_search_management_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertNotIn("render_category_navigation_v186", text)
        self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)
        self.assertNotIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", text)
        self.assertNotIn("seller-store-category-state-v192", text)

    def test_v194_existing_saved_search_management_guards_remain_present(self):
        files = (
            self._backend_root() / "listings" / "test_saved_search_management_hardening.py",
            self._backend_root() / "listings" / "test_saved_search_management_ui_polish.py",
            self._backend_root() / "listings" / "test_saved_search_ux_polish.py",
        )

        for path in files:
            self.assertTrue(path.exists(), f"Expected saved-search guard file missing: {path}")

        self.assertIn(
            "SavedSearchManagementHardeningTests",
            files[0].read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "SavedSearchManagementUiPolishTests",
            files[1].read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "SavedSearchUxPolishTests",
            files[2].read_text(encoding="utf-8", errors="ignore"),
        )
