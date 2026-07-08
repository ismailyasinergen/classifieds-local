"""
LISTING_PROMOTIONS_CONTRACT_V151

Contract tests for the listing_promotions split lane before moving the current
promotion view out of listings/views.py.

These tests intentionally lock routing, authentication, ownership boundaries,
and the v150 split-lane recommendation before the behavior-bearing move happens.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import NoReverseMatch, resolve, reverse
from django.utils import timezone

from categories.models import Category
from listings import listing_views_split_lane_audit_v150 as split_audit
from listings import views as listing_views
from listings.models import Listing


LISTING_PROMOTIONS_CONTRACT_V151 = True
PROMOTION_VIEW_NAME = 'listing_feature_priority_update'
PROMOTION_URL_NAME = 'listing_feature_priority_update'
PROMOTION_ROUTE = 'listings/<int:pk>/feature-priority/'
PROMOTION_ROUTE_PARAMS = ['pk']


def _model_field_names(model):
    return {field.name for field in model._meta.fields}


def _create_category():
    fields = _model_field_names(Category)
    kwargs = {}

    if "name" in fields:
        kwargs["name"] = "V151 Contract Category"
    if "slug" in fields:
        kwargs["slug"] = "v151-contract-category"

    return Category.objects.create(**kwargs)


def _listing_status_value():
    fields = _model_field_names(Listing)
    if "status" not in fields:
        return None

    status_class = getattr(Listing, "Status", None)
    for attr in ("APPROVED", "ACTIVE", "PUBLISHED"):
        if status_class is not None and hasattr(status_class, attr):
            return getattr(status_class, attr)

    field = Listing._meta.get_field("status")
    values = [choice[0] for choice in getattr(field, "choices", [])]
    for candidate in ("approved", "active", "published", "APPROVED", "ACTIVE", "PUBLISHED"):
        if candidate in values:
            return candidate

    return values[0] if values else "approved"


def _fill_required_listing_fields(kwargs):
    for field in Listing._meta.fields:
        if field.name in kwargs:
            continue
        if field.primary_key or getattr(field, "auto_created", False):
            continue
        if getattr(field, "default", NOT_PROVIDED) is not NOT_PROVIDED:
            continue
        if getattr(field, "null", False) or getattr(field, "blank", False):
            continue

        if isinstance(field, (models.CharField, models.SlugField)):
            kwargs[field.name] = f"v151-{field.name}"
        elif isinstance(field, models.TextField):
            kwargs[field.name] = f"V151 contract {field.name}"
        elif isinstance(field, models.DecimalField):
            kwargs[field.name] = Decimal("100.00")
        elif isinstance(field, (models.IntegerField, models.PositiveIntegerField)):
            kwargs[field.name] = 1
        elif isinstance(field, models.FloatField):
            kwargs[field.name] = 1.0
        elif isinstance(field, models.BooleanField):
            kwargs[field.name] = True
        elif isinstance(field, models.DateTimeField):
            kwargs[field.name] = timezone.now()
        elif isinstance(field, models.DateField):
            kwargs[field.name] = timezone.now().date()

    return kwargs


def _create_listing(owner, category):
    fields = _model_field_names(Listing)
    kwargs = {}

    if "seller" in fields:
        kwargs["seller"] = owner
    if "user" in fields:
        kwargs["user"] = owner
    if "owner" in fields:
        kwargs["owner"] = owner
    if "category" in fields:
        kwargs["category"] = category
    if "title" in fields:
        kwargs["title"] = "V151 Contract Listing"
    if "description" in fields:
        kwargs["description"] = "A listing used to lock the promotion contract before split."
    if "price" in fields:
        kwargs["price"] = Decimal("125.00")
    if "location" in fields:
        kwargs["location"] = "V151 Test City"

    status_value = _listing_status_value()
    if status_value is not None:
        kwargs["status"] = status_value

    kwargs = _fill_required_listing_fields(kwargs)
    return Listing.objects.create(**kwargs)


def _param_value(listing, param_name):
    if hasattr(listing, param_name):
        value = getattr(listing, param_name)
        if value:
            return value

    lowered = param_name.lower()
    if lowered in {"pk", "id", "listing_id", "listing_pk"}:
        return listing.pk

    if "slug" in lowered and hasattr(listing, "slug"):
        slug = getattr(listing, "slug")
        if slug:
            return slug

    return listing.pk


def _promotion_url(listing):
    kwargs = {name: _param_value(listing, name) for name in PROMOTION_ROUTE_PARAMS}
    args = [_param_value(listing, name) for name in PROMOTION_ROUTE_PARAMS]

    candidate_names = [PROMOTION_URL_NAME, f"listings:{PROMOTION_URL_NAME}"]
    for candidate_name in candidate_names:
        try:
            if kwargs:
                return reverse(candidate_name, kwargs=kwargs)
            return reverse(candidate_name)
        except NoReverseMatch:
            pass

        try:
            return reverse(candidate_name, args=args)
        except NoReverseMatch:
            pass

    path = PROMOTION_ROUTE
    for param_name, value in kwargs.items():
        path = re.sub(rf"<(?:[^:>]+:)?{re.escape(param_name)}>", str(value), path)

    return "/" + path.lstrip("/")


class ListingPromotionsContractV151Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="v151-promotion-owner",
            email="v151-promotion-owner@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="v151-promotion-other",
            email="v151-promotion-other@example.com",
            password="testpass123",
        )
        self.category = _create_category()
        self.listing = _create_listing(owner=self.owner, category=self.category)
        self.url = _promotion_url(self.listing)

    def test_v151_listing_promotions_lane_contract_matches_v150_audit(self):
        report = split_audit.build_report(Path("."))
        lane = next(lane for lane in report.lane_reports if lane.name == "listing_promotions")

        self.assertEqual(lane.definition_count, 1)
        self.assertEqual(lane.definitions[0].name, PROMOTION_VIEW_NAME)
        self.assertEqual(lane.definitions[0].line_count, 20)
        self.assertEqual(lane.split_readiness, "candidate_for_first_split")

    def test_v151_promotion_url_name_route_and_callback_are_stable(self):
        match = resolve(self.url)

        self.assertEqual(match.url_name, PROMOTION_URL_NAME)
        self.assertIs(match.func, getattr(listing_views, PROMOTION_VIEW_NAME))

    def test_v151_anonymous_promotion_request_redirects_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        login_url = resolve_url(settings.LOGIN_URL)
        self.assertIn(login_url.rstrip("/"), response["Location"])

    def test_v151_authenticated_get_promotion_request_is_method_not_allowed(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_v151_owner_post_promotion_request_reaches_flow_without_permission_or_method_error(self):
        self.client.force_login(self.owner)

        response = self.client.post(self.url, data={})

        self.assertIn(response.status_code, {200, 302, 400})
        self.assertNotEqual(response.status_code, 403)
        self.assertNotEqual(response.status_code, 404)
        self.assertNotEqual(response.status_code, 405)

    def test_v151_non_owner_get_promotion_request_is_method_not_allowed(self):
        self.client.force_login(self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_v151_non_owner_post_promotion_request_cannot_render_success_flow(self):
        self.client.force_login(self.other_user)

        response = self.client.post(self.url, data={})

        self.assertIn(response.status_code, {302, 403, 404})
        self.assertNotEqual(response.status_code, 200)
        self.assertNotEqual(response.status_code, 405)
