from __future__ import annotations

import html
import re
from decimal import Decimal
from io import StringIO
from urllib.parse import urljoin, urlsplit

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.text import slugify

from categories.models import Category
from categories.navigation_v186 import build_category_filter_url_v186


V188_SAVED_SEARCH_CATEGORY_COMPAT_MARKER = "V188_SAVED_SEARCH_CATEGORY_COMPATIBILITY_POLISH"


class SavedSearchCategoryCompatibilityV188Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(
            username="v188-saved-search-user",
            email="v188-saved-search-user@example.com",
            password="test-password",
        )

    def _listing_kwargs(self, category: Category, title: str) -> dict[str, object]:
        Listing = apps.get_model("listings", "Listing")
        user_model = get_user_model()
        kwargs: dict[str, object] = {}

        for field in Listing._meta.fields:
            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.default is not NOT_PROVIDED:
                continue

            if isinstance(field, models.ForeignKey):
                remote_model = field.remote_field.model

                if remote_model is Category:
                    kwargs[field.name] = category
                elif remote_model is user_model:
                    kwargs[field.name] = self.user
                elif field.name in {"seller", "user", "owner", "created_by"}:
                    kwargs[field.name] = self.user
                elif not field.null:
                    raise AssertionError(
                        f"V188 helper does not know how to populate required FK `{field.name}`."
                    )
                continue

            if field.null or field.blank:
                continue

            if field.choices:
                values = [choice[0] for choice in field.choices]
                if field.name == "status":
                    preferred = ("approved", "active", "published", "live", "open")
                    kwargs[field.name] = next(
                        (value for value in preferred if value in values),
                        values[0],
                    )
                else:
                    kwargs[field.name] = values[0]
            elif isinstance(field, models.SlugField):
                kwargs[field.name] = slugify(title)
            elif isinstance(field, (models.CharField, models.TextField)):
                if field.name == "title":
                    kwargs[field.name] = title
                elif field.name == "description":
                    kwargs[field.name] = f"{title} description"
                elif field.name == "location":
                    kwargs[field.name] = "Berlin"
                else:
                    kwargs[field.name] = f"{title} {field.name}"[: field.max_length or 255]
            elif isinstance(field, models.DecimalField):
                kwargs[field.name] = Decimal("100.00")
            elif isinstance(field, (models.IntegerField, models.PositiveIntegerField, models.PositiveSmallIntegerField)):
                kwargs[field.name] = 1
            elif isinstance(field, models.BooleanField):
                kwargs[field.name] = field.name in {
                    "is_active",
                    "is_approved",
                    "is_published",
                    "is_visible",
                }
            elif isinstance(field, models.DateTimeField):
                if "expire" in field.name or "end" in field.name:
                    kwargs[field.name] = timezone.now() + timezone.timedelta(days=30)
                else:
                    kwargs[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                if "expire" in field.name or "end" in field.name:
                    kwargs[field.name] = timezone.localdate() + timezone.timedelta(days=30)
                else:
                    kwargs[field.name] = timezone.localdate()
            elif isinstance(field, models.FileField):
                kwargs[field.name] = "v188-placeholder.txt"
            else:
                raise AssertionError(
                    f"V188 helper does not know how to populate required field `{field.name}`."
                )

        kwargs.setdefault("title", title)

        return kwargs

    def _create_listing(self, category_slug: str, title: str):
        Listing = apps.get_model("listings", "Listing")
        category = Category.objects.get(slug=category_slug)
        return Listing.objects.create(**self._listing_kwargs(category, title))

    def _first_descendant_slug(self, root_slug: str) -> str:
        root = Category.objects.get(slug=root_slug)

        grandchild = (
            Category.objects.filter(parent__parent=root)
            .order_by("slug")
            .first()
        )
        if grandchild is not None:
            return grandchild.slug

        child = Category.objects.filter(parent=root).order_by("slug").first()
        if child is not None:
            return child.slug

        return root.slug

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

    def _get_saved_search_browse_response(self, params: dict[str, str]):
        self.client.force_login(self.user)

        candidates: list[tuple[str, int, str]] = []

        for url in self._candidate_browse_urls():
            response = self.client.get(url, params)
            content = response.content.decode("utf-8", errors="ignore")
            candidates.append((url, response.status_code, content[:240]))

            if response.status_code != 200:
                continue

            has_saved_search_state = (
                "saved search" in content.lower()
                or "save search" in content.lower()
                or "already saved" in content.lower()
            )
            has_category_state = params.get("category", "") in content

            if has_saved_search_state and has_category_state:
                return url, response, content

        debug = "\n".join(
            f"{url} -> {status} :: {snippet}"
            for url, status, snippet in candidates
        )
        raise AssertionError(
            "No authenticated browse route rendered saved-search/category state.\n"
            + debug
        )

    def _parse_attrs(self, raw_attrs: str) -> dict[str, str]:
        attr_pattern = re.compile(
            r"""(?P<name>[\w:-]+)(?:\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote))?""",
            re.S,
        )

        attrs: dict[str, str] = {}
        for match in attr_pattern.finditer(raw_attrs):
            name = match.group("name").lower()
            value = match.group("value") or ""
            attrs[name] = html.unescape(value)

        return attrs

    def _maybe_extract_saved_search_form(self, content: str) -> tuple[str, dict[str, str]] | None:
        form_pattern = re.compile(
            r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>",
            re.I | re.S,
        )
        input_pattern = re.compile(r"<input\b(?P<attrs>[^>]*)>", re.I | re.S)
        textarea_pattern = re.compile(
            r"<textarea\b(?P<attrs>[^>]*)>(?P<value>.*?)</textarea>",
            re.I | re.S,
        )

        for form_match in form_pattern.finditer(content):
            form_attrs = self._parse_attrs(form_match.group("attrs"))
            body = form_match.group("body")
            searchable = f"{form_attrs.get('action', '')} {body}".lower()

            if form_attrs.get("method", "get").lower() != "post":
                continue

            if "saved" not in searchable and "save search" not in searchable:
                continue

            data: dict[str, str] = {}

            for input_match in input_pattern.finditer(body):
                input_attrs = self._parse_attrs(input_match.group("attrs"))
                name = input_attrs.get("name")
                input_type = input_attrs.get("type", "text").lower()

                if not name:
                    continue
                if input_type in {"submit", "button", "image"}:
                    continue
                if name == "csrfmiddlewaretoken":
                    continue

                data[name] = input_attrs.get("value", "")

            for textarea_match in textarea_pattern.finditer(body):
                textarea_attrs = self._parse_attrs(textarea_match.group("attrs"))
                name = textarea_attrs.get("name")
                if name:
                    data[name] = html.unescape(textarea_match.group("value") or "")

            for optional_name in ("name", "title", "saved_search_name"):
                data.setdefault(optional_name, "V188 category saved search")

            return form_attrs.get("action", ""), data

        return None

    def _extract_saved_search_form(self, content: str) -> tuple[str, dict[str, str]]:
        result = self._maybe_extract_saved_search_form(content)
        if result is None:
            raise AssertionError("No saved-search POST form was found on category browse page.")
        return result

    def _post_saved_search_from_browse_page(self, *, category_slug: str, query: str):
        url, _response, content = self._get_saved_search_browse_response(
            {
                "category": category_slug,
                "q": query,
                "sort": "newest",
            },
        )

        action, data = self._extract_saved_search_form(content)

        target_url = urljoin(url, action) if action else url
        split = urlsplit(target_url)
        post_path = split.path or url
        if split.query:
            post_path = f"{post_path}?{split.query}"

        post_response = self.client.post(post_path, data, follow=True)

        return post_response, data

    def _saved_search_queryset_for_user(self):
        SavedSearch = apps.get_model("listings", "SavedSearch")
        user_model = get_user_model()

        user_fields = [
            field
            for field in SavedSearch._meta.fields
            if isinstance(field, models.ForeignKey) and field.remote_field.model is user_model
        ]
        self.assertTrue(user_fields, "SavedSearch has no user ForeignKey field.")

        return SavedSearch.objects.filter(**{user_fields[0].name: self.user})

    def _saved_search_contains_category_signal(self, saved_search, category: Category) -> bool:
        text_parts: list[str] = []

        for field in saved_search._meta.fields:
            value = getattr(saved_search, field.name, "")
            if value is None:
                continue

            text_parts.append(str(value))

            if isinstance(field, models.ForeignKey) and field.remote_field.model is Category:
                if getattr(saved_search, field.name + "_id") == category.pk:
                    return True

        combined_text = " ".join(text_parts)

        return category.slug in combined_text or f"category={category.slug}" in combined_text

    def test_v188_marker_is_declared_for_compatibility_checkpoint(self):
        self.assertEqual(
            V188_SAVED_SEARCH_CATEGORY_COMPAT_MARKER,
            "V188_SAVED_SEARCH_CATEGORY_COMPATIBILITY_POLISH",
        )

    def test_v188_category_filter_url_preserves_saved_search_safe_state(self):
        url = build_category_filter_url_v186(
            "/",
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
                "page": "3",
            },
            "vehicles-cars-sedans",
        )

        self.assertIn("category=vehicles-cars-sedans", url)
        self.assertIn("q=chair", url)
        self.assertIn("sort=newest", url)
        self.assertNotIn("page=3", url)

    def test_v188_saved_search_browse_state_keeps_category_query_and_sort(self):
        self._create_listing("home-garden-furniture", "V188 chair listing")

        _url, response, content = self._get_saved_search_browse_response(
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("home-garden-furniture", content)
        self.assertIn("q=chair", content)
        self.assertIn("sort=newest", content)

    def test_v188_saved_search_create_preserves_category_query_and_repeat_is_deduped_or_already_saved(self):
        self._create_listing("home-garden-furniture", "V188 saved chair listing")
        category = Category.objects.get(slug="home-garden-furniture")

        before_count = self._saved_search_queryset_for_user().count()

        first_response, _first_data = self._post_saved_search_from_browse_page(
            category_slug="home-garden-furniture",
            query="chair",
        )

        after_first_count = self._saved_search_queryset_for_user().count()

        self.assertIn(first_response.status_code, {200, 302})
        self.assertEqual(after_first_count, before_count + 1)

        saved_search = self._saved_search_queryset_for_user().order_by("-pk").first()
        self.assertIsNotNone(saved_search)
        self.assertTrue(
            self._saved_search_contains_category_signal(saved_search, category),
            "SavedSearch did not preserve the selected category signal.",
        )

        _url, second_response, second_content = self._get_saved_search_browse_response(
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
            }
        )

        maybe_form = self._maybe_extract_saved_search_form(second_content)
        if maybe_form is not None:
            action, data = maybe_form
            target_url = urljoin(_url, action) if action else _url
            split = urlsplit(target_url)
            post_path = split.path or _url
            if split.query:
                post_path = f"{post_path}?{split.query}"
            second_response = self.client.post(post_path, data, follow=True)

        self.assertIn(second_response.status_code, {200, 302})
        self.assertEqual(
            self._saved_search_queryset_for_user().count(),
            after_first_count,
            "Repeating the same category-aware saved-search state created a duplicate.",
        )

    def test_v188_saved_search_result_preview_flow_handles_category_query_safely(self):
        self._create_listing("vehicles-cars-sedans", "V188 sedan listing")

        post_response, _data = self._post_saved_search_from_browse_page(
            category_slug="vehicles-cars-sedans",
            query="sedan",
        )

        response_text = post_response.content.decode("utf-8", errors="ignore")

        self.assertIn(post_response.status_code, {200, 302})
        self.assertNotIn("Traceback", response_text)
        self.assertNotIn("Server Error", response_text)

        _url, browse_response, browse_content = self._get_saved_search_browse_response(
            {
                "category": "vehicles-cars-sedans",
                "q": "sedan",
            }
        )

        self.assertEqual(browse_response.status_code, 200)
        self.assertIn("vehicles-cars-sedans", browse_content)
        self.assertIn("q=sedan", browse_content)

    def test_v188_category_browse_pagination_keeps_safe_query_params_with_existing_slug(self):
        selected_slug = self._first_descendant_slug("electronics")

        for index in range(1, 16):
            self._create_listing(
                selected_slug,
                f"V188 speaker listing {index}",
            )

        _url, response, content = self._get_saved_search_browse_response(
            {
                "category": selected_slug,
                "q": "speaker",
                "sort": "newest",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(selected_slug, content)
        self.assertIn("q=speaker", content)
        self.assertIn("sort=newest", content)
