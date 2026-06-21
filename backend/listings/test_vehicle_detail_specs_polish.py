from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class VehicleDetailSpecsPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="vehicle-detail-v72@classifieds.local",
            username="vehicle_detail_v72",
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
            price=Decimal("975000.00"),
            category=category,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes or {},
        )

    def test_vehicle_detail_uses_grouped_specs(self):
        listing = self._listing(
            "V72 grouped vehicle detail listing",
            self.cars,
            {
                "marka": "Toyota",
                "model": "Corolla",
                "seri": "Corolla",
                "yil": "2020",
                "km": "45000",
                "yakit_tipi": "Benzinli",
                "vites": "Otomatik",
                "sanziman_cekis": "Otomatik / Önden Çekiş",
                "renk": "Beyaz",
                "kasa_tipi": "Sedan",
                "motor_gucu": "132 hp",
                "motor_hacmi": "1.6",
                "garanti": "Evet",
                "kimden": "Sahibinden",
                "takas": "Hayır",
            },
        )

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VEHICLE_DETAIL_SPECS_V72")
        self.assertContains(response, '<div class="vehicle-detail-summary"')
        self.assertContains(response, '<div class="vehicle-specs-panel"')
        self.assertContains(response, "Araç Özeti")
        self.assertContains(response, "Motor ve Performans")
        self.assertContains(response, "Donanım / İlan Bilgileri")

        for value in [
            "Toyota",
            "Corolla",
            "2020",
            "45000",
            "Benzinli",
            "Otomatik",
            "Otomatik / Önden Çekiş",
            "Beyaz",
            "Sedan",
            "132 hp",
            "1.6",
            "Sahibinden",
        ]:
            self.assertContains(response, value)

        self.assertNotContains(response, '<div class="classified-detail-grid">')

    def test_non_vehicle_detail_keeps_generic_detail_grid(self):
        listing = self._listing(
            "V72 normal phone detail listing",
            self.phones,
            {"marka": "Apple", "model": "iPhone 14", "kapasite": "128 GB"},
        )

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "VEHICLE_DETAIL_SPECS_V72")
        self.assertContains(response, '<div class="classified-detail-grid">')
        self.assertContains(response, "Apple")
        self.assertContains(response, "iPhone 14")
        self.assertContains(response, "128 GB")
