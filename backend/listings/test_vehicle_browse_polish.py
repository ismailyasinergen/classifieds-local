from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class VehicleBrowsePolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="vehicle-browse-v71@classifieds.local",
            username="vehicle_browse_v71",
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

    def _listing(self, title, category, attributes=None):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal("900000.00"),
            category=category,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes or {},
        )

    def test_car_browse_uses_vehicle_table_like_result_layout(self):
        self._listing(
            "V71 vehicle table car",
            self.cars,
            {
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
                "yakit_tipi": "Benzinli",
                "vites": "Otomatik",
                "renk": "Beyaz",
            },
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VEHICLE_BROWSE_RESULTS_V71")
        self.assertContains(response, '<table class="vehicle-results-table">')
        self.assertContains(response, "İlan Başlığı")
        self.assertContains(response, "Marka")
        self.assertContains(response, "Model")
        self.assertContains(response, "Yıl")
        self.assertContains(response, "KM")
        self.assertContains(response, "Yakıt")
        self.assertContains(response, "Vites")
        self.assertContains(response, "İl / İlçe")
        self.assertContains(response, "V71 vehicle table car")
        self.assertContains(response, "Toyota")
        self.assertContains(response, "Corolla")
        self.assertContains(response, "2020")
        self.assertContains(response, "45000")
        self.assertContains(response, "Benzinli")
        self.assertContains(response, "Otomatik")

    def test_non_vehicle_non_real_estate_browse_keeps_card_grid(self):
        self._listing(
            "V71 normal phone card listing",
            self.phones,
            {"marka": "Apple", "model": "iPhone 14", "kapasite": "128 GB"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "phones"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="listing-grid"')
        self.assertContains(response, "V71 normal phone card listing")
        self.assertNotContains(response, '<table class="vehicle-results-table">')
        self.assertNotContains(response, '<table class="real-estate-results-table">')
