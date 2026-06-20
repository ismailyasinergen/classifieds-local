from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class ListingCardHighlightTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="card_highlight_seller@classifieds.local",
            username="cardhighlightseller",
            password="Testpass12345",
        )

        self.vehicles, _ = Category.objects.get_or_create(
            slug="vehicles",
            defaults={"name": "Vehicles"},
        )
        self.cars, _ = Category.objects.get_or_create(
            slug="cars",
            defaults={"name": "Cars", "parent": self.vehicles},
        )

        self.electronics, _ = Category.objects.get_or_create(
            slug="electronics",
            defaults={"name": "Electronics"},
        )
        self.phones, _ = Category.objects.get_or_create(
            slug="phones",
            defaults={"name": "Phones", "parent": self.electronics},
        )

    def _listing(self, title, category, attributes):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal("1000.00"),
            category=category,
            owner=self.seller,
            location="Istanbul",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes,
        )

    def test_car_card_highlights_use_prioritized_attributes(self):
        listing = self._listing(
            "BMW 520i card highlight",
            self.cars,
            {"marka": "BMW", "model": "520i", "yil": "2018", "km": "90000"},
        )

        highlights = listing.card_highlights

        self.assertEqual([item["key"] for item in highlights], ["marka", "model", "yil", "km"])
        self.assertEqual([item["value"] for item in highlights], ["BMW", "520i", "2018", "90000"])

    def test_browse_card_renders_highlights(self):
        self._listing(
            "BMW 520i card highlight",
            self.cars,
            {"marka": "BMW", "model": "520i", "yil": "2018", "km": "90000"},
        )

        response = self.client.get(reverse("listings:listing_list"), {"category": "cars"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "listing-card-highlights")
        self.assertContains(response, "BMW")
        self.assertContains(response, "520i")
        self.assertContains(response, "2018")
        self.assertContains(response, "90000")

    def test_phone_card_highlights_use_phone_fields(self):
        listing = self._listing(
            "iPhone card highlight",
            self.phones,
            {"marka": "Apple", "model": "iPhone 14 Pro", "kapasite": "128 GB", "durum": "Used"},
        )

        highlights = listing.card_highlights

        self.assertEqual([item["key"] for item in highlights], ["marka", "model", "kapasite", "durum"])
        self.assertEqual([item["value"] for item in highlights], ["Apple", "iPhone 14 Pro", "128 GB", "Used"])
