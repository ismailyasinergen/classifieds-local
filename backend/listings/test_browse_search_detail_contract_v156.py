"""
BROWSE_SEARCH_DETAIL_CONTRACT_V156

Focused behavior contracts for the browse_search_detail lane before moving
its remaining view out of listings.views in a later checkpoint.

The target may be either a function-based view or a class-based view. v156
therefore discovers both top-level functions and classes in listings.views.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, is_dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.urls import URLPattern, URLResolver, get_resolver, resolve, reverse
from django.utils import timezone

from categories.models import Category
from listings import views as listing_views
from listings import listing_views_split_lane_followup_audit_v153 as followup
from listings.models import Listing


BROWSE_SEARCH_DETAIL_CONTRACT_V156 = True
BROWSE_SEARCH_DETAIL_LANE = "browse_search_detail"


def _followup_report():
    return followup.build_followup_report(Path("."))


def _browse_lane_from_report():
    report = _followup_report()

    if report.recommended_next_lane.name == BROWSE_SEARCH_DETAIL_LANE:
        return report.recommended_next_lane

    for candidate in report.remaining_candidates:
        if candidate.name == BROWSE_SEARCH_DETAIL_LANE:
            return candidate

    raise AssertionError("browse_search_detail lane was not found in the v153 follow-up report")


def _source_definition_ranges():
    views_source = Path("listings/views.py").read_text(encoding="utf-8")
    tree = ast.parse(views_source)
    ranges = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        start_lineno = node.lineno
        decorator_list = getattr(node, "decorator_list", [])
        if decorator_list:
            start_lineno = min(decorator.lineno for decorator in decorator_list)

        end_lineno = node.end_lineno or node.lineno
        name = node.name

        ranges[name] = {
            "kind": "class" if isinstance(node, ast.ClassDef) else "function",
            "start": start_lineno,
            "end": end_lineno,
            "span_lines": end_lineno - start_lineno + 1,
            "body_lines": end_lineno - node.lineno + 1,
            "public_object": getattr(listing_views, name, None),
        }

    return ranges


def _extract_definition_names_from_value(value):
    names = []

    if value is None:
        return names

    if isinstance(value, str):
        if value.isidentifier() and value != BROWSE_SEARCH_DETAIL_LANE:
            names.append(value)
        return names

    if is_dataclass(value):
        value = asdict(value)

    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"name", "function_name", "definition_name", "view_name", "class_name"} and isinstance(nested, str):
                if nested.isidentifier() and nested != BROWSE_SEARCH_DETAIL_LANE:
                    names.append(nested)
            elif isinstance(nested, (list, tuple, dict)):
                names.extend(_extract_definition_names_from_value(nested))
        return names

    if isinstance(value, (list, tuple, set)):
        for item in value:
            names.extend(_extract_definition_names_from_value(item))
        return names

    for attr in ("name", "function_name", "definition_name", "view_name", "class_name"):
        nested = getattr(value, attr, None)
        if isinstance(nested, str) and nested.isidentifier() and nested != BROWSE_SEARCH_DETAIL_LANE:
            names.append(nested)

    return names


def _callback_target_name(callback):
    view_class = getattr(callback, "view_class", None)
    if view_class is not None:
        return getattr(view_class, "__name__", "")

    view_func = getattr(callback, "view_func", None)
    if view_func is not None:
        return getattr(view_func, "__name__", "")

    return getattr(callback, "__name__", "")


def _walk_urlpatterns(patterns=None):
    if patterns is None:
        patterns = get_resolver().url_patterns

    for pattern in patterns:
        if isinstance(pattern, URLPattern):
            yield pattern
        elif isinstance(pattern, URLResolver):
            yield from _walk_urlpatterns(pattern.url_patterns)


def _url_patterns_for_definition(target_name):
    matches = []

    for pattern in _walk_urlpatterns():
        callback = pattern.callback
        callback_target_name = _callback_target_name(callback)
        if callback_target_name == target_name:
            matches.append(pattern)

    return matches


def _reverse_pattern(pattern, listing):
    kwargs_options = [
        {},
        {"pk": listing.pk},
        {"id": listing.pk},
        {"listing_id": listing.pk},
        {"slug": getattr(listing, "slug", "")},
        {"pk": listing.pk, "slug": getattr(listing, "slug", "")},
    ]

    route_name = getattr(pattern, "name", None)
    if not route_name:
        return None

    viewname_options = [f"listings:{route_name}", route_name]

    for viewname in viewname_options:
        for kwargs in kwargs_options:
            kwargs = {key: value for key, value in kwargs.items() if value not in {None, ""}}
            try:
                url = reverse(viewname, kwargs=kwargs)
            except Exception:
                continue
            return url

    return None


def _target_definition_name():
    lane = _browse_lane_from_report()
    definitions = _source_definition_ranges()

    names = []
    for attr in (
        "definitions",
        "definition_reports",
        "function_reports",
        "definition_names",
        "function_names",
        "view_names",
        "class_names",
        "sample_definitions",
    ):
        names.extend(_extract_definition_names_from_value(getattr(lane, attr, None)))

    names = [
        name
        for name in dict.fromkeys(names)
        if name in definitions and definitions[name]["public_object"] is not None
    ]

    if len(names) == 1:
        return names[0]

    excluded_names = {
        "listing_favorite_toggle",
        "listing_feature_priority_update",
    }

    lane_line_count = getattr(lane, "total_lines", None)

    exact_line_count_candidates = [
        name
        for name, meta in definitions.items()
        if meta["public_object"] is not None
        and name not in excluded_names
        and lane_line_count in {meta["span_lines"], meta["body_lines"]}
    ]

    if len(exact_line_count_candidates) == 1:
        return exact_line_count_candidates[0]

    # If the line-count match collides with another extracted-roadmap view,
    # prefer the listing detail target because browse_search_detail is the
    # public browse/detail lane, while saved_search_rename belongs to the
    # saved-search management lane.
    detail_exact_candidates = [
        name
        for name in exact_line_count_candidates
        if "detail" in name.lower() and "listing" in name.lower()
    ]

    if len(detail_exact_candidates) == 1:
        return detail_exact_candidates[0]

    if "ListingDetailView" in exact_line_count_candidates:
        return "ListingDetailView"

    routed_candidates = []
    for name in exact_line_count_candidates:
        if _url_patterns_for_definition(name):
            routed_candidates.append(name)

    detail_routed_candidates = [
        name
        for name in routed_candidates
        if "detail" in name.lower() and "listing" in name.lower()
    ]

    if len(detail_routed_candidates) == 1:
        return detail_routed_candidates[0]

    if len(routed_candidates) == 1:
        return routed_candidates[0]

    # Final fallback: search all routed top-level view-like definitions. This
    # intentionally includes class-based views, where URL callbacks expose
    # callback.view_class rather than callback.__name__.
    routed_view_like = []
    for name, meta in definitions.items():
        if meta["public_object"] is None or name in excluded_names:
            continue

        patterns = _url_patterns_for_definition(name)
        if not patterns:
            continue

        lower_name = name.lower()
        route_names = " ".join(str(getattr(pattern, "name", "") or "") for pattern in patterns).lower()
        combined = lower_name + " " + route_names

        if any(token in combined for token in ("browse", "search", "detail", "listing", "list")):
            routed_view_like.append(name)

    if len(routed_view_like) == 1:
        return routed_view_like[0]

    raise AssertionError(
        "Could not uniquely identify browse_search_detail target definition. "
        f"names={names}, exact_line_count_candidates={exact_line_count_candidates}, "
        f"routed_candidates={routed_candidates}, routed_view_like={routed_view_like}, "
        f"lane_line_count={lane_line_count}"
    )


class BrowseSearchDetailSourceContractV156Tests(SimpleTestCase):
    def test_v156_browse_search_detail_is_current_next_lane(self):
        report = _followup_report()

        self.assertEqual(report.recommended_next_lane.name, BROWSE_SEARCH_DETAIL_LANE)
        self.assertEqual(report.recommended_next_lane.definition_count, 1)
        self.assertGreater(report.recommended_next_lane.total_lines, 0)

    def test_v156_browse_search_detail_target_is_still_defined_in_views_before_extraction(self):
        target_name = _target_definition_name()
        definitions = _source_definition_ranges()

        self.assertIn(target_name, definitions)
        self.assertIsNotNone(definitions[target_name]["public_object"])
        self.assertGreater(definitions[target_name]["span_lines"], 0)

    def test_v156_browse_search_detail_target_is_one_remaining_definition(self):
        lane = _browse_lane_from_report()
        target_name = _target_definition_name()
        definitions = _source_definition_ranges()

        self.assertEqual(lane.definition_count, 1)
        self.assertIn(
            lane.total_lines,
            {definitions[target_name]["span_lines"], definitions[target_name]["body_lines"]},
        )

    def test_v156_browse_search_detail_target_has_public_url_pattern(self):
        target_name = _target_definition_name()
        patterns = _url_patterns_for_definition(target_name)

        self.assertEqual(len(patterns), 1)
        self.assertTrue(getattr(patterns[0], "name", None))


class BrowseSearchDetailRuntimeContractV156Tests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.seller = self.User.objects.create_user(
            username=f"seller-v156-{uuid4().hex[:8]}",
            email=f"seller-v156-{uuid4().hex[:8]}@example.com",
            password="pass12345",
        )
        self.category = self._create_category()
        self.listing = self._create_listing(seller=self.seller, category=self.category)

    def _create_category(self):
        values = {}
        for field in Category._meta.fields:
            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.name == "name":
                values[field.name] = f"V156 Browse {uuid4().hex[:8]}"
            elif field.name == "slug":
                values[field.name] = f"v156-browse-{uuid4().hex[:8]}"
            elif not field.blank and not field.null and not field.has_default():
                values[field.name] = self._value_for_field(field, field.name)

        return Category.objects.create(**values)

    def _create_listing(self, seller, category):
        values = {}
        for field in Listing._meta.fields:
            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.name in {"seller", "owner", "user", "created_by"}:
                values[field.name] = seller
                continue

            if field.name == "category":
                values[field.name] = category
                continue

            if field.name == "status":
                values[field.name] = self._approved_status_value(field)
                continue

            if field.name in {"expires_at", "featured_until", "top_listing_until"}:
                values[field.name] = timezone.now() + timedelta(days=30)
                continue

            if not field.blank and not field.null and not field.has_default():
                values[field.name] = self._value_for_field(field, field.name)

        return Listing.objects.create(**values)

    def _approved_status_value(self, field):
        choices = list(getattr(field, "choices", []) or [])
        values = [choice[0] for choice in choices]

        for preferred in ("approved", "active", "published", "live"):
            if preferred in values:
                return preferred

        if values:
            return values[0]

        return "approved"

    def _value_for_field(self, field, name):
        if isinstance(field, models.ForeignKey):
            if field.remote_field and field.remote_field.model == self.User:
                return self.seller
            if field.remote_field and field.remote_field.model == Category:
                return self.category
            raise AssertionError(f"Unhandled required foreign key field: {name}")

        if isinstance(field, models.SlugField):
            return f"v156-{name}-{uuid4().hex[:8]}"

        if isinstance(field, models.CharField):
            if getattr(field, "choices", None):
                return list(field.choices)[0][0]
            value = f"V156 {name} {uuid4().hex[:8]}"
            max_length = field.max_length or 100
            return value[:max_length]

        if isinstance(field, models.TextField):
            return f"V156 contract test value for {name}."

        if isinstance(field, models.DecimalField):
            return Decimal("99.99")

        if isinstance(field, (models.IntegerField, models.PositiveIntegerField, models.PositiveSmallIntegerField)):
            return 1

        if isinstance(field, models.BooleanField):
            return False

        if isinstance(field, models.DateTimeField):
            return timezone.now()

        if isinstance(field, models.DateField):
            return timezone.now().date()

        raise AssertionError(f"Unhandled required field: {name} ({field.__class__.__name__})")

    def _reverse_target_url(self):
        target_name = _target_definition_name()
        patterns = _url_patterns_for_definition(target_name)

        errors = []
        for pattern in patterns:
            url = _reverse_pattern(pattern, self.listing)
            if not url:
                errors.append(f"could not reverse pattern name={getattr(pattern, 'name', None)!r}")
                continue

            match = resolve(url)
            if _callback_target_name(match.func) == target_name:
                return target_name, url, match

            errors.append(f"resolved callback {_callback_target_name(match.func)!r} did not match {target_name!r}")

        raise AssertionError(
            "Could not reverse a URL for browse_search_detail target definition. "
            + " | ".join(errors[:8])
        )

    def test_v156_public_route_resolves_to_browse_search_detail_callback(self):
        target_name, url, match = self._reverse_target_url()

        self.assertEqual(_callback_target_name(match.func), target_name)
        self.assertGreater(len(url), 1)

    def test_v156_public_get_for_browse_search_detail_route_is_available(self):
        _target_name, url, _match = self._reverse_target_url()

        response = self.client.get(url)

        self.assertIn(response.status_code, {200, 301, 302})
        if response.status_code in {301, 302}:
            self.assertNotIn("/accounts/login", response.url)

    def test_v156_public_get_with_search_query_is_safe_for_route(self):
        _target_name, url, _match = self._reverse_target_url()

        response = self.client.get(url, {"q": "V156"})

        self.assertIn(response.status_code, {200, 301, 302})
        if response.status_code in {301, 302}:
            self.assertNotIn("/accounts/login", response.url)
