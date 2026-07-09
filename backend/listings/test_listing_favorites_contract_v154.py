"""
LISTING_FAVORITES_CONTRACT_V154

Focused behavior contracts for the favorites lane before extracting
listing_favorite_toggle from listings.views in a later checkpoint.

Updated in v155 to keep the public listings.views re-export contract green
after the dedicated favorite view module extraction.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from categories.models import Category
from listings import listing_favorite_views
from listings import views as listing_views
from listings.models import Listing, ListingFavorite


LISTING_FAVORITES_CONTRACT_V154 = True
FAVORITE_VIEW_NAME = "listing_favorite_toggle"
FAVORITE_URL_NAME = "listing_favorite_toggle"


class ListingFavoritesContractV154Tests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.seller = self.User.objects.create_user(
            username=f"seller-v154-{uuid4().hex[:8]}",
            email=f"seller-v154-{uuid4().hex[:8]}@example.com",
            password="pass12345",
        )
        self.buyer = self.User.objects.create_user(
            username=f"buyer-v154-{uuid4().hex[:8]}",
            email=f"buyer-v154-{uuid4().hex[:8]}@example.com",
            password="pass12345",
        )
        self.other_buyer = self.User.objects.create_user(
            username=f"other-buyer-v154-{uuid4().hex[:8]}",
            email=f"other-buyer-v154-{uuid4().hex[:8]}@example.com",
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
                values[field.name] = f"V154 Favorites {uuid4().hex[:8]}"
            elif field.name == "slug":
                values[field.name] = f"v154-favorites-{uuid4().hex[:8]}"
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
            return f"v154-{name}-{uuid4().hex[:8]}"

        if isinstance(field, models.CharField):
            if getattr(field, "choices", None):
                return list(field.choices)[0][0]
            value = f"V154 {name} {uuid4().hex[:8]}"
            max_length = field.max_length or 100
            return value[:max_length]

        if isinstance(field, models.TextField):
            return f"V154 contract test value for {name}."

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

    def favorite_url(self, listing=None):
        listing = listing or self.listing
        return reverse(f"listings:{FAVORITE_URL_NAME}", kwargs={"pk": listing.pk})

    def favorite_exists(self, user=None, listing=None):
        user = user or self.buyer
        listing = listing or self.listing
        return ListingFavorite.objects.filter(user=user, listing=listing).exists()

    def test_v154_favorite_contract_target_is_reexported_after_v155_move(self):
        self.assertTrue(hasattr(listing_views, FAVORITE_VIEW_NAME))
        self.assertTrue(hasattr(listing_favorite_views, FAVORITE_VIEW_NAME))
        self.assertIs(
            getattr(listing_views, FAVORITE_VIEW_NAME),
            getattr(listing_favorite_views, FAVORITE_VIEW_NAME),
        )

    def test_v154_favorite_url_name_route_and_callback_are_stable(self):
        url = self.favorite_url()
        match = resolve(url)

        self.assertEqual(match.url_name, FAVORITE_URL_NAME)
        self.assertTrue(hasattr(listing_views, FAVORITE_VIEW_NAME))
        self.assertIs(match.func, getattr(listing_views, FAVORITE_VIEW_NAME))

    def test_v154_anonymous_favorite_post_redirects_to_login(self):
        favorite_url = self.favorite_url()
        response = self.client.post(favorite_url)
        resolved_login_url = resolve_url(settings.LOGIN_URL)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(resolved_login_url))
        self.assertIn("next=", response.url)
        self.assertIn(favorite_url, response.url)
        self.assertFalse(self.favorite_exists())

    def test_v154_authenticated_get_favorite_request_is_method_not_allowed(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.favorite_url())

        self.assertEqual(response.status_code, 405)
        self.assertFalse(self.favorite_exists())

    def test_v154_authenticated_post_creates_favorite_for_current_user(self):
        self.client.force_login(self.buyer)

        response = self.client.post(self.favorite_url(), HTTP_REFERER="/listings/")

        self.assertIn(response.status_code, {200, 302})
        self.assertTrue(self.favorite_exists())

    def test_v154_second_authenticated_post_removes_existing_favorite_for_current_user(self):
        self.client.force_login(self.buyer)

        self.client.post(self.favorite_url(), HTTP_REFERER="/listings/")
        self.assertTrue(self.favorite_exists())

        response = self.client.post(self.favorite_url(), HTTP_REFERER="/listings/")

        self.assertIn(response.status_code, {200, 302})
        self.assertFalse(self.favorite_exists())

    def test_v154_favorite_toggle_is_scoped_to_current_user(self):
        ListingFavorite.objects.create(user=self.other_buyer, listing=self.listing)

        self.client.force_login(self.buyer)
        self.client.post(self.favorite_url(), HTTP_REFERER="/listings/")

        self.assertTrue(self.favorite_exists(user=self.buyer))
        self.assertTrue(self.favorite_exists(user=self.other_buyer))
