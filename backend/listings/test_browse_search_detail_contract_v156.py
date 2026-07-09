"""
BROWSE_SEARCH_DETAIL_CONTRACT_V156

Focused behavior contracts for the browse_search_detail lane.

v156 locked ListingDetailView before extraction. After v157, these contracts
remain green by validating the dedicated source module and the public
listings.views.ListingDetailView compatibility re-export.
"""

from __future__ import annotations

import ast
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from categories.models import Category
from listings import listing_browse_detail_views
from listings import listing_views_split_lane_followup_audit_v153 as followup
from listings import views as listing_views
from listings.models import Listing


BROWSE_SEARCH_DETAIL_CONTRACT_V156 = True
BROWSE_SEARCH_DETAIL_LANE = "browse_search_detail"


def _followup_report():
    return followup.build_followup_report(Path("."))


def _browse_extracted_status():
    report = _followup_report()
    extracted = {status.name: status for status in report.extracted_lanes}
    if BROWSE_SEARCH_DETAIL_LANE not in extracted:
        raise AssertionError("browse_search_detail lane was not found in extracted lanes after v157")
    return extracted[BROWSE_SEARCH_DETAIL_LANE]


def _dedicated_definition_ranges():
    source = Path("listings/listing_browse_detail_views.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    ranges = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        start_lineno = node.lineno
        decorator_list = getattr(node, "decorator_list", [])
        if decorator_list:
            start_lineno = min(decorator.lineno for decorator in decorator_list)

        end_lineno = node.end_lineno or node.lineno

        ranges[node.name] = {
            "kind": "class" if isinstance(node, ast.ClassDef) else "function",
            "start": start_lineno,
            "end": end_lineno,
            "span_lines": end_lineno - start_lineno + 1,
            "body_lines": end_lineno - node.lineno + 1,
        }

    return ranges


def _callback_target_name(callback):
    view_class = getattr(callback, "view_class", None)
    if view_class is not None:
        return getattr(view_class, "__name__", "")

    view_func = getattr(callback, "view_func", None)
    if view_func is not None:
        return getattr(view_func, "__name__", "")

    return getattr(callback, "__name__", "")


class BrowseSearchDetailSourceContractV156Tests(SimpleTestCase):
    def test_v156_browse_search_detail_is_extracted_after_v157(self):
        report = followup.build_followup_report(Path("."))
        extracted = {status.name for status in report.extracted_lanes}

        self.assertIn("browse_search_detail", extracted)
        self.assertIn("listing_crud_uploads", extracted)
        self.assertEqual(report.remaining_candidates, [])
        self.assertIsNone(report.recommended_next_lane)

    def test_v156_listing_detail_target_is_reexported_after_v157_extraction(self):
        self.assertTrue(hasattr(listing_views, "ListingDetailView"))
        self.assertTrue(hasattr(listing_browse_detail_views, "ListingDetailView"))
        self.assertIs(
            listing_views.ListingDetailView,
            listing_browse_detail_views.ListingDetailView,
        )

    def test_v156_dedicated_source_preserves_listing_detail_contract_shape(self):
        ranges = _dedicated_definition_ranges()

        self.assertIn("ListingDetailView", ranges)
        self.assertEqual(ranges["ListingDetailView"]["kind"], "class")
        self.assertEqual(ranges["ListingDetailView"]["body_lines"], 48)

    def test_v156_browse_search_detail_target_has_public_url_pattern(self):
        url = reverse("listings:listing_detail", kwargs={"pk": 1})
        match = resolve(url)

        self.assertEqual(match.url_name, "listing_detail")
        self.assertIs(getattr(match.func, "view_class", None), listing_views.ListingDetailView)


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
        url = reverse("listings:listing_detail", kwargs={"pk": self.listing.pk})
        match = resolve(url)

        self.assertEqual(match.url_name, "listing_detail")
        self.assertEqual(_callback_target_name(match.func), "ListingDetailView")
        self.assertIs(getattr(match.func, "view_class", None), listing_views.ListingDetailView)

        return url, match

    def test_v156_public_route_resolves_to_browse_search_detail_callback(self):
        url, match = self._reverse_target_url()

        self.assertGreater(len(url), 1)
        self.assertEqual(match.url_name, "listing_detail")

    def test_v156_public_get_for_browse_search_detail_route_is_available(self):
        url, _match = self._reverse_target_url()

        response = self.client.get(url)

        self.assertIn(response.status_code, {200, 301, 302})
        if response.status_code in {301, 302}:
            self.assertNotIn("/accounts/login", response.url)

    def test_v156_public_get_with_search_query_is_safe_for_route(self):
        url, _match = self._reverse_target_url()

        response = self.client.get(url, {"q": "V156"})

        self.assertIn(response.status_code, {200, 301, 302})
        if response.status_code in {301, 302}:
            self.assertNotIn("/accounts/login", response.url)
