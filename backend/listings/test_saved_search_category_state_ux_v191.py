from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, reverse


V191_SAVED_SEARCH_CATEGORY_STATE_UX_MARKER = "V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH"


class SavedSearchCategoryStateUxV191Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(
            username="v191-saved-search-user",
            email="v191-saved-search-user@example.com",
            password="test-password",
        )

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _listing_browse_template_path(self) -> Path:
        return self._backend_root() / "listings" / "templates" / "listings" / "listing_list.html"

    def _candidate_browse_urls(self) -> tuple[str, ...]:
        names = (
            "listings:browse",
            "listings:listing_browse",
            "listings:listing_list",
            "listings:list",
            "listing_browse",
            "listing_list",
            "browse_search_detail",
            "listings:browse_search_detail",
            "home",
        )

        urls: list[str] = []
        for name in names:
            try:
                urls.append(reverse(name))
            except NoReverseMatch:
                continue

        urls.extend(("/", "/listings/", "/browse/"))

        unique_urls: list[str] = []
        for url in urls:
            if url not in unique_urls:
                unique_urls.append(url)

        return tuple(unique_urls)

    def _get_public_browse_content(self, params: dict[str, str], *, authenticated: bool = True):
        if authenticated:
            self.client.force_login(self.user)
        else:
            self.client.logout()

        candidates: list[tuple[str, int, str]] = []

        for url in self._candidate_browse_urls():
            response = self.client.get(url, params)
            content = response.content.decode("utf-8", errors="ignore")
            candidates.append((url, response.status_code, content[:260]))

            if response.status_code == 200 and "Classifieds Local" in content:
                return url, response, content

        debug = "\n".join(
            f"{url} -> {status} :: {snippet}"
            for url, status, snippet in candidates
        )
        raise AssertionError("No usable public browse response was found.\n" + debug)

    def test_v191_marker_is_declared_for_saved_search_category_state_ux(self):
        self.assertEqual(
            V191_SAVED_SEARCH_CATEGORY_STATE_UX_MARKER,
            "V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH",
        )

    def test_v191_listing_browse_template_contains_category_aware_saved_search_copy(self):
        text = self._listing_browse_template_path().read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT", text)
        self.assertIn("render_category_navigation_v186", text)
        self.assertIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", text)
        self.assertIn("{% if request.GET.category %}", text)
        self.assertIn("saved-search-category-state-v191", text)
        self.assertIn('data-v191-saved-search-category-state="true"', text)
        self.assertIn('aria-label="Category-aware saved search note"', text)
        self.assertIn("Category-aware saved search", text)
        self.assertIn(
            "Save this search to keep this category together with your current keywords and sort order.",
            text,
        )

    def test_v191_category_browse_shows_category_aware_saved_search_wording(self):
        _url, response, content = self._get_public_browse_content(
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
            },
            authenticated=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", content)
        self.assertIn('data-v191-saved-search-category-state="true"', content)
        self.assertIn('aria-label="Category-aware saved search note"', content)
        self.assertIn("Category-aware saved search", content)
        self.assertIn(
            "Save this search to keep this category together with your current keywords and sort order.",
            content,
        )
        self.assertIn("home-garden-furniture", content)
        self.assertIn("q=chair", content)
        self.assertIn("sort=newest", content)

    def test_v191_default_browse_does_not_show_category_specific_saved_search_note(self):
        _url, response, content = self._get_public_browse_content(
            {
                "q": "chair",
                "sort": "newest",
            },
            authenticated=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", content)
        self.assertNotIn('data-v191-saved-search-category-state="true"', content)
        self.assertNotIn("Category-aware saved search", content)

    def test_v191_v188_saved_search_category_behavior_guard_remains_present(self):
        v188_test = self._backend_root() / "listings" / "test_saved_search_category_compat_v188.py"
        self.assertTrue(v188_test.exists())

        text = v188_test.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V188_SAVED_SEARCH_CATEGORY_COMPATIBILITY_POLISH", text)
        self.assertIn("test_v188_saved_search_create_preserves_category_query", text)
        self.assertIn("test_v188_saved_search_browse_state_keeps_category_query_and_sort", text)
        self.assertIn("test_v188_saved_search_result_preview_flow_handles_category_query_safely", text)

    def test_v191_saved_search_category_copy_does_not_leak_into_seller_store_templates(self):
        candidate_roots = (
            self._backend_root() / "accounts" / "templates",
            self._backend_root() / "templates" / "accounts",
        )

        seller_store_templates: list[Path] = []
        for root in candidate_roots:
            if root.exists():
                seller_store_templates.extend(
                    path
                    for path in root.rglob("*.html")
                    if "seller" in path.as_posix().lower() or "store" in path.as_posix().lower()
                )

        self.assertTrue(
            seller_store_templates,
            "No seller/store templates were found for v191 leak-scope verification.",
        )

        for path in seller_store_templates:
            text = path.read_text(encoding="utf-8", errors="ignore")

            self.assertNotIn(
                "V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH",
                text,
                f"v191 saved-search category-state copy leaked into seller/store template: {path}",
            )
            self.assertNotIn(
                "saved-search-category-state-v191",
                text,
                f"v191 saved-search category-state CSS hook leaked into seller/store template: {path}",
            )
            self.assertNotIn(
                "Category-aware saved search",
                text,
                f"v191 category-aware saved-search wording leaked into seller/store template: {path}",
            )
