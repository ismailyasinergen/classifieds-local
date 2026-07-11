from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import NoReverseMatch, reverse

from categories.models import Category
from categories.public_browse_mount_v187 import (
    V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT_MARKER,
    V187_MOUNTED_TEMPLATE_NAMES,
    get_v187_mounted_template_paths,
)


class CategoryPublicBrowseMountV187Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def test_v187_mounted_template_manifest_is_declared(self):
        self.assertEqual(V187_MOUNTED_TEMPLATE_NAMES, ("listings/listing_list.html",))

    def test_v187_mounted_templates_contain_load_tag_and_mount_marker(self):
        for path in get_v187_mounted_template_paths():
            text = path.read_text(encoding="utf-8")

            self.assertIn("category_navigation_v186", text)
            self.assertIn(V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT_MARKER, text)
            self.assertIn("render_category_navigation_v186", text)

    def test_v187_mounted_template_renders_category_navigation_partial(self):
        request = RequestFactory().get(
            "/listings/",
            {
                "category": "vehicles-cars-sedans",
                "q": "hybrid",
                "page": "4",
            },
        )
        request.user = AnonymousUser()

        for template_name in V187_MOUNTED_TEMPLATE_NAMES:
            html = render_to_string(
                template_name,
                {
                    "listings": [],
                    "object_list": [],
                    "page_obj": [],
                    "paginator": None,
                    "query": "hybrid",
                    "selected_category": Category.objects.get(slug="vehicles-cars-sedans"),
                },
                request=request,
            )

            self.assertIn("V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION", html)
            self.assertIn("Selected category: Sedans", html)
            self.assertIn("vehicles-cars-sedans", html)
            self.assertIn("q=hybrid", html)
            self.assertNotIn("page=4", html)

    def _public_browse_url_candidates(self) -> tuple[str, ...]:
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

        urls.extend(("/listings/", "/", "/browse/"))

        unique_urls: list[str] = []
        for url in urls:
            if url not in unique_urls:
                unique_urls.append(url)

        return tuple(unique_urls)

    def test_v187_public_browse_response_renders_category_navigation_when_route_available(self):
        matched_responses = []

        for url in self._public_browse_url_candidates():
            response = self.client.get(
                url,
                {
                    "category": "home-garden-furniture",
                    "q": "chair",
                },
            )

            if response.status_code != 200:
                continue

            content = response.content.decode("utf-8", errors="ignore")
            if "V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION" in content:
                matched_responses.append((url, content))

        self.assertTrue(
            matched_responses,
            "No public browse route rendered the v187 category navigation mount.",
        )

        _url, content = matched_responses[0]
        self.assertIn("Selected category: Furniture", content)
        self.assertIn("home-garden-furniture", content)
        self.assertIn("q=chair", content)

    def test_v187_seeded_category_data_is_available_for_public_navigation(self):
        self.assertEqual(Category.objects.filter(parent__isnull=True).count(), 10)
        self.assertTrue(Category.objects.filter(slug="home-garden-furniture").exists())
        self.assertTrue(Category.objects.filter(slug="vehicles-cars-sedans").exists())
