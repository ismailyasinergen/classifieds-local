"""Active listing-card promotion presentation contracts for V343."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from categories.models import Category
from listings.listing_card_promotions_v343 import (
    LISTING_CARD_PROMOTIONS_V343,
    annotate_listing_card_promotions_v343,
)
from listings.listing_recently_viewed import (
    RECENTLY_VIEWED_SESSION_KEY_V272,
    get_recently_viewed_listings_v272,
)
from listings.listing_recommendations import (
    get_related_listings_v271,
)
from listings.models import Listing
from promotions.doping_catalog_v342 import (
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
)
from promotions.models import ListingPromotion, PromotionPackage


class ListingCardPromotionsV343Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="v343-card-owner",
            email="v343-card-owner@example.com",
            password="testpass123",
        )
        cls.category = Category.objects.create(
            name="V343 Vehicles",
            slug="v343-vehicles",
        )

        cls.listings = [
            Listing.objects.create(
                title=f"V343 card listing {index}",
                description="Card promotion annotation test.",
                price=Decimal("15000.00"),
                category=cls.category,
                owner=cls.owner,
                location="Berlin",
                status=Listing.Status.APPROVED,
                expires_at=timezone.now() + timedelta(days=30),
            )
            for index in range(1, 7)
        ]

        cls.packages = {}

        for code, mode in (
            (
                PromotionCodeV342.SMALL_PHOTO,
                DurationModeV342.LISTING_LIFETIME,
            ),
            (
                PromotionCodeV342.URGENT,
                DurationModeV342.FIXED_WEEKS,
            ),
            (
                PromotionCodeV342.COLORFUL_TITLE,
                DurationModeV342.LISTING_LIFETIME,
            ),
        ):
            cls.packages[code] = PromotionPackage.objects.create(
                name=f"V343 {code.value}",
                package_type=PromotionPackage.PackageType.FEATURED,
                duration_days=7 if mode == DurationModeV342.FIXED_WEEKS else 0,
                price=Decimal("100.00"),
                catalog_code=code,
                price_group=PriceGroupV342.VEHICLES,
                duration_mode=mode,
            )

    def create_active_promotion(
        self,
        listing,
        code,
        *,
        starts_at=None,
        ends_at=Ellipsis,
        status=ListingPromotion.Status.ACTIVE,
    ):
        now = timezone.now()
        resolved_ends_at = (
            now + timedelta(days=7)
            if ends_at is Ellipsis
            else ends_at
        )

        return ListingPromotion.objects.create(
            listing=listing,
            package=self.packages[code],
            user=self.owner,
            status=status,
            payment_status=ListingPromotion.PaymentStatus.PAID,
            price_snapshot=Decimal("100.00"),
            promotion_code_snapshot=code,
            price_group_snapshot=PriceGroupV342.VEHICLES,
            duration_mode_snapshot=self.packages[code].duration_mode,
            requested_weeks=(
                1
                if code == PromotionCodeV342.URGENT
                else None
            ),
            unit_price_snapshot=Decimal("100.00"),
            starts_at=starts_at or now - timedelta(hours=1),
            ends_at=resolved_ends_at,
        )

    def annotated_listing(self, listing):
        return annotate_listing_card_promotions_v343(
            Listing.objects.filter(pk=listing.pk)
        ).get()

    def test_foundation_marker_is_enabled(self):
        self.assertTrue(LISTING_CARD_PROMOTIONS_V343)

    def test_active_card_promotions_are_annotated_independently(self):
        listing = self.listings[0]

        self.create_active_promotion(
            listing,
            PromotionCodeV342.SMALL_PHOTO,
        )
        self.create_active_promotion(
            listing,
            PromotionCodeV342.URGENT,
        )
        self.create_active_promotion(
            listing,
            PromotionCodeV342.COLORFUL_TITLE,
        )

        annotated = self.annotated_listing(listing)

        self.assertTrue(
            annotated.has_small_photo_promotion_v343
        )
        self.assertTrue(
            annotated.has_urgent_promotion_v343
        )
        self.assertTrue(
            annotated.has_colorful_title_promotion_v343
        )

    def test_expired_promotion_fails_closed(self):
        listing = self.listings[1]
        now = timezone.now()

        self.create_active_promotion(
            listing,
            PromotionCodeV342.URGENT,
            starts_at=now - timedelta(days=8),
            ends_at=now - timedelta(seconds=1),
        )

        annotated = self.annotated_listing(listing)

        self.assertFalse(
            annotated.has_urgent_promotion_v343
        )

    def test_future_promotion_fails_closed(self):
        listing = self.listings[2]
        now = timezone.now()

        self.create_active_promotion(
            listing,
            PromotionCodeV342.SMALL_PHOTO,
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(days=8),
        )

        annotated = self.annotated_listing(listing)

        self.assertFalse(
            annotated.has_small_photo_promotion_v343
        )

    def test_null_end_remains_active_for_lifetime_products(self):
        listing = self.listings[3]

        self.create_active_promotion(
            listing,
            PromotionCodeV342.SMALL_PHOTO,
            ends_at=None,
        )
        self.create_active_promotion(
            listing,
            PromotionCodeV342.COLORFUL_TITLE,
            ends_at=None,
        )

        annotated = self.annotated_listing(listing)

        self.assertTrue(
            annotated.has_small_photo_promotion_v343
        )
        self.assertTrue(
            annotated.has_colorful_title_promotion_v343
        )

    def test_null_end_fails_closed_for_fixed_week_urgent(self):
        listing = self.listings[4]

        self.create_active_promotion(
            listing,
            PromotionCodeV342.URGENT,
            ends_at=None,
        )

        annotated = self.annotated_listing(listing)

        self.assertFalse(
            annotated.has_urgent_promotion_v343
        )

    def test_pending_promotion_fails_closed(self):
        listing = self.listings[3]

        self.create_active_promotion(
            listing,
            PromotionCodeV342.COLORFUL_TITLE,
            status=ListingPromotion.Status.PENDING,
        )

        annotated = self.annotated_listing(listing)

        self.assertFalse(
            annotated.has_colorful_title_promotion_v343
        )

    def test_annotation_evaluates_many_listings_in_one_query(self):
        self.create_active_promotion(
            self.listings[0],
            PromotionCodeV342.URGENT,
        )

        queryset = annotate_listing_card_promotions_v343(
            Listing.objects
            .filter(pk__in=[item.pk for item in self.listings])
            .order_by("pk")
        )

        with CaptureQueriesContext(connection) as captured:
            evaluated = list(queryset)

        self.assertEqual(len(evaluated), 6)
        self.assertEqual(len(captured), 1)
        self.assertTrue(
            evaluated[0].has_urgent_promotion_v343
        )

    def test_shared_card_contains_all_v343_presentation_hooks(self):
        backend_root = Path(__file__).resolve().parents[1]
        template = (
            backend_root
            / "listings"
            / "templates"
            / "listings"
            / "_listing_card.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "LISTING_CARD_PROMOTIONS_V343",
            template,
        )
        self.assertIn(
            "listing-card-small-photo-v343",
            template,
        )
        self.assertIn(
            "listing-badge-urgent-v343",
            template,
        )
        self.assertIn(
            "listing-card-colorful-title-v343",
            template,
        )
        self.assertIn(
            "data-v343-card-promotions",
            template,
        )

    def test_css_contains_accessible_presentation_contracts(self):
        backend_root = Path(__file__).resolve().parents[1]
        stylesheet = (
            backend_root
            / "listings"
            / "static"
            / "listings"
            / "listing-card-promotions-v343.css"
        ).read_text(encoding="utf-8")
        base_template = (
            backend_root
            / "templates"
            / "base.html"
        ).read_text(encoding="utf-8")
        asset_tag = (
            "{% static "
            "'listings/listing-card-promotions-v343.css' %}"
        )

        self.assertEqual(
            base_template.count(asset_tag),
            1,
        )
        self.assertIn(
            "data-listing-card-promotions-v343",
            base_template,
        )
        self.assertLess(
            base_template.index(asset_tag),
            base_template.index(
                "{% block extra_styles %}{% endblock %}"
            ),
        )

        self.assertIn(
            "LISTING_CARD_DOPING_PRESENTATION_V343",
            stylesheet,
        )
        self.assertIn(
            ".listing-badge-urgent-v343",
            stylesheet,
        )
        self.assertIn(
            ".listing-badge-small-photo-v343",
            stylesheet,
        )
        self.assertIn(
            ".listing-card-colorful-title-link-v343",
            stylesheet,
        )
        self.assertIn(
            "prefers-reduced-motion",
            stylesheet,
        )

    def test_public_listing_page_renders_active_promotion_styles(self):
        listing = self.listings[4]

        self.create_active_promotion(
            listing,
            PromotionCodeV342.SMALL_PHOTO,
        )
        self.create_active_promotion(
            listing,
            PromotionCodeV342.URGENT,
        )
        self.create_active_promotion(
            listing,
            PromotionCodeV342.COLORFUL_TITLE,
        )

        response = self.client.get("/listings/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-v343-small-photo="true"',
        )
        self.assertContains(
            response,
            'data-v343-urgent="true"',
        )
        self.assertContains(
            response,
            'data-v343-colorful-title="true"',
        )
        self.assertContains(response, "Small Photo")
        self.assertContains(response, "Urgent")

    def test_category_page_renders_active_urgent_badge(self):
        listing = self.listings[5]

        self.create_active_promotion(
            listing,
            PromotionCodeV342.URGENT,
        )

        response = self.client.get(
            f"/categories/{self.category.slug}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "listing-badge-urgent-v343",
        )


    def test_related_service_keeps_card_promotion_annotations(self):
        current_listing = self.listings[0]
        promoted_listing = self.listings[1]

        self.create_active_promotion(
            promoted_listing,
            PromotionCodeV342.URGENT,
        )

        related = get_related_listings_v271(
            current_listing,
            limit=8,
        )

        promoted_result = next(
            item
            for item in related
            if item.pk == promoted_listing.pk
        )

        self.assertTrue(
            promoted_result.has_urgent_promotion_v343
        )

    def test_recently_viewed_service_keeps_card_annotations(self):
        promoted_listing = self.listings[2]

        self.create_active_promotion(
            promoted_listing,
            PromotionCodeV342.SMALL_PHOTO,
        )

        request = RequestFactory().get("/")
        request.session = {
            RECENTLY_VIEWED_SESSION_KEY_V272: [
                promoted_listing.pk,
            ],
        }

        recent = get_recently_viewed_listings_v272(
            request,
            current_listing=None,
        )

        self.assertEqual(
            [item.pk for item in recent],
            [promoted_listing.pk],
        )
        self.assertTrue(
            recent[0].has_small_photo_promotion_v343
        )

    def test_all_remaining_card_surfaces_use_v343_helper(self):
        backend_root = Path(__file__).resolve().parents[1]

        paths = (
            backend_root
            / "listings"
            / "listing_recommendations.py",
            backend_root
            / "listings"
            / "listing_recently_viewed.py",
            backend_root
            / "listings"
            / "listing_reports_views.py",
        )

        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")

                self.assertIn(
                    "annotate_listing_card_promotions_v343",
                    source,
                )
