from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, ListingFavorite


class ActiveListingBuyerActionsRepairR002Tests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.seller = user_model.objects.create_user(
            username="repair-r002-seller",
            password="StrongPass123!",
        )
        self.buyer = user_model.objects.create_user(
            username="repair-r002-buyer",
            password="StrongPass123!",
        )
        self.category = Category.objects.create(
            name="Repair R002",
            slug="repair-r002",
        )
        self.expired_listing = Listing.objects.create(
            title="Expired buyer-action target",
            description="An expired listing must reject buyer actions.",
            price=Decimal("100.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.client.force_login(self.buyer)

    def test_expired_listing_rejects_favorite_toggle(self):
        response = self.client.post(
            reverse(
                "listings:listing_favorite_toggle",
                kwargs={"pk": self.expired_listing.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ListingFavorite.objects.filter(
                user=self.buyer,
                listing=self.expired_listing,
            ).exists()
        )

    def test_expired_listing_rejects_message_composer(self):
        response = self.client.get(
            reverse(
                "conversations:listing_contact",
                kwargs={"pk": self.expired_listing.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
