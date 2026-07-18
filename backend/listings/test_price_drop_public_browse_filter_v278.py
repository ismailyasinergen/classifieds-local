from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from categories.models import Category
from listings.listing_price_drop_filter_v278 import (
    PRICE_DROP_FILTER_ENABLED_VALUE_V278,
    PRICE_DROP_FILTER_PARAM_V278,
    PRICE_DROP_PUBLIC_BROWSE_FILTER_V278,
    apply_price_drop_filter_v278,
    price_drop_filter_is_enabled_v278,
)
from listings.models import (
    Listing,
    SavedSearch,
)
from listings.saved_searches import (
    SAVED_SEARCH_ALLOWED_KEYS,
)


class PriceDropPublicBrowseFilterV278Tests(
    TestCase
):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.seller = User.objects.create_user(
            username="v278-price-drop-seller",
            email=(
                "v278-price-drop-seller"
                "@example.test"
            ),
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=cls.seller,
        )

        cls.category = Category.objects.create(
            name="V278 Furniture",
            slug="v278-furniture",
        )

    def create_listing(
        self,
        title: str,
        *,
        price: str = "1000.00",
        location: str = "Berlin",
        category: Category | None = None,
    ) -> Listing:
        return Listing.objects.create(
            title=title,
            description=(
                f"{title} v278 public browse "
                "price-drop filter test."
            ),
            price=Decimal(price),
            category=category or self.category,
            owner=self.seller,
            location=location,
            status=Listing.Status.APPROVED,
            expires_at=(
                timezone.now()
                + timedelta(days=30)
            ),
        )

    def change_price(
        self,
        listing: Listing,
        price: str,
    ) -> Listing:
        listing.price = Decimal(price)
        listing.save(
            update_fields=[
                "price",
            ],
        )
        listing.refresh_from_db()
        return listing

    def browse(
        self,
        params: dict[str, str] | None = None,
    ):
        return self.client.get(
            reverse(
                "listings:listing_list",
            ),
            params or {},
        )

    @staticmethod
    def response_titles(
        response,
    ) -> list[str]:
        return [
            listing.title
            for listing in response.context[
                "listings"
            ]
        ]

    def test_v278_contract_and_source_markers_exist(
        self,
    ):
        self.assertTrue(
            PRICE_DROP_PUBLIC_BROWSE_FILTER_V278
        )

        self.assertEqual(
            PRICE_DROP_FILTER_PARAM_V278,
            "price_drops",
        )

        self.assertEqual(
            PRICE_DROP_FILTER_ENABLED_VALUE_V278,
            "1",
        )

        self.assertIn(
            "price_drops",
            SAVED_SEARCH_ALLOWED_KEYS,
        )

        base = Path(
            settings.BASE_DIR
        )

        template_source = (
            base
            / "listings"
            / "templates"
            / "listings"
            / "listing_list.html"
        ).read_text(
            encoding="utf-8",
        )

        filter_source = (
            base
            / "listings"
            / "listing_filter_helpers.py"
        ).read_text(
            encoding="utf-8",
        )

        self.assertIn(
            "PRICE_DROP_PUBLIC_BROWSE_FILTER_V278",
            template_source,
        )

        self.assertIn(
            'name="price_drops"',
            template_source,
        )

        self.assertIn(
            "apply_price_drop_filter_v278",
            filter_source,
        )

    def test_only_current_latest_reductions_are_returned(
        self,
    ):
        current_drop = self.create_listing(
            "V278 Current Drop",
        )
        self.change_price(
            current_drop,
            "900.00",
        )

        self.create_listing(
            "V278 Baseline Only",
        )

        increase = self.create_listing(
            "V278 Current Increase",
        )
        self.change_price(
            increase,
            "1100.00",
        )

        drop_then_increase = self.create_listing(
            "V278 Drop Then Increase",
        )
        self.change_price(
            drop_then_increase,
            "850.00",
        )
        self.change_price(
            drop_then_increase,
            "925.00",
        )

        stale_drop = self.create_listing(
            "V278 Stale Drop",
        )
        self.change_price(
            stale_drop,
            "800.00",
        )

        Listing.objects.filter(
            pk=stale_drop.pk,
        ).update(
            price=Decimal("775.00"),
        )

        response = self.browse(
            {
                "price_drops": "1",
            }
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self.response_titles(response),
            [
                "V278 Current Drop",
            ],
        )

    def test_missing_or_invalid_value_does_not_enable_filter(
        self,
    ):
        current_drop = self.create_listing(
            "V278 Unfiltered Drop",
        )
        self.change_price(
            current_drop,
            "900.00",
        )

        self.create_listing(
            "V278 Unfiltered Baseline",
        )

        unfiltered = self.browse()
        invalid = self.browse(
            {
                "price_drops": "yes",
            }
        )

        self.assertCountEqual(
            self.response_titles(unfiltered),
            [
                "V278 Unfiltered Drop",
                "V278 Unfiltered Baseline",
            ],
        )

        self.assertCountEqual(
            self.response_titles(invalid),
            [
                "V278 Unfiltered Drop",
                "V278 Unfiltered Baseline",
            ],
        )

        self.assertFalse(
            price_drop_filter_is_enabled_v278(
                invalid.wsgi_request
            )
        )

        self.assertFalse(
            any(
                chip["clear_param"]
                == "price_drops"
                for chip in invalid.context[
                    "active_filter_chips"
                ]
            )
        )

    def test_filter_combines_with_existing_search_and_price_filters(
        self,
    ):
        berlin_drop = self.create_listing(
            "V278 Oak Chair Berlin",
            location="Berlin Mitte",
        )
        self.change_price(
            berlin_drop,
            "800.00",
        )

        munich_drop = self.create_listing(
            "V278 Oak Chair Munich",
            location="Munich",
        )
        self.change_price(
            munich_drop,
            "800.00",
        )

        self.create_listing(
            "V278 Oak Chair Baseline",
            price="800.00",
            location="Berlin Mitte",
        )

        response = self.browse(
            {
                "q": "Oak Chair",
                "location": "Berlin",
                "min_price": "750",
                "max_price": "850",
                "price_drops": "1",
            }
        )

        self.assertEqual(
            self.response_titles(response),
            [
                "V278 Oak Chair Berlin",
            ],
        )

    def test_active_filter_chip_clears_only_price_drop_param(
        self,
    ):
        listing = self.create_listing(
            "V278 Chip Chair",
        )
        self.change_price(
            listing,
            "900.00",
        )

        response = self.browse(
            {
                "q": "Chip Chair",
                "price_drops": "1",
            }
        )

        chips = {
            chip["clear_param"]: chip
            for chip in response.context[
                "active_filter_chips"
            ]
        }

        self.assertIn(
            "price_drops",
            chips,
        )

        chip = chips[
            "price_drops"
        ]

        self.assertEqual(
            chip["label"],
            "Price",
        )

        self.assertEqual(
            chip["value"],
            "Price drops only",
        )

        parsed = urlsplit(
            chip["clear_url"]
        )

        query = parse_qs(
            parsed.query
        )

        self.assertNotIn(
            "price_drops",
            query,
        )

        self.assertEqual(
            query.get("q"),
            [
                "Chip Chair",
            ],
        )

    def test_pagination_preserves_price_drop_filter(
        self,
    ):
        for index in range(13):
            listing = self.create_listing(
                f"V278 Paginated Drop {index:02d}",
            )
            self.change_price(
                listing,
                "900.00",
            )

        response = self.browse(
            {
                "price_drops": "1",
            }
        )

        self.assertEqual(
            response.context[
                "page_obj"
            ].paginator.count,
            13,
        )

        self.assertEqual(
            response.context[
                "page_querystring"
            ],
            "price_drops=1",
        )

        self.assertTrue(
            response.context[
                "page_obj"
            ].has_next()
        )

        self.assertContains(
            response,
            "price_drops=1",
        )

        self.assertContains(
            response,
            "page=2",
        )

    def test_saved_search_round_trip_preserves_price_drop_filter(
        self,
    ):
        self.client.force_login(
            self.seller
        )

        response = self.browse(
            {
                "q": "discount chair",
                "price_drops": "1",
            }
        )

        querystring = response.context[
            "save_search_querystring"
        ]

        parsed = parse_qs(
            querystring
        )

        self.assertEqual(
            parsed.get(
                "price_drops"
            ),
            [
                "1",
            ],
        )

        self.assertEqual(
            parsed.get("q"),
            [
                "discount chair",
            ],
        )

        create_response = self.client.post(
            reverse(
                "listings:saved_search_create",
            ),
            {
                "name": (
                    "V278 price-drop search"
                ),
                "querystring": querystring,
            },
        )

        self.assertEqual(
            create_response.status_code,
            302,
        )

        saved_search = (
            SavedSearch.objects.get(
                user=self.seller,
                name=(
                    "V278 price-drop search"
                ),
            )
        )

        self.assertEqual(
            saved_search.query_params[
                "price_drops"
            ],
            "1",
        )

        self.assertEqual(
            saved_search.query_params[
                "q"
            ],
            "discount chair",
        )

    def test_queryset_helper_does_not_mutate_unfiltered_query(
        self,
    ):
        listing = self.create_listing(
            "V278 Direct Helper Drop",
        )
        self.change_price(
            listing,
            "900.00",
        )

        request = self.browse().wsgi_request

        queryset = Listing.objects.all()

        result = apply_price_drop_filter_v278(
            queryset,
            request,
        )

        self.assertEqual(
            str(result.query),
            str(queryset.query),
        )

    def test_v278_adds_no_migration(
        self,
    ):
        migration_dir = (
            Path(settings.BASE_DIR)
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_dir.glob(
                    "*v278*"
                )
            ),
            [],
        )
