from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class RealEstateBrowsePolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="realestate-browse-v68@classifieds.local",
            username="realestate_browse_v68",
            password="Testpass12345",
        )

        self.real_estate, _ = Category.objects.get_or_create(
            slug="real-estate",
            defaults={"name": "Real Estate"},
        )
        self.homes_for_sale, _ = Category.objects.get_or_create(
            slug="homes-for-sale",
            defaults={"name": "Homes for Sale", "parent": self.real_estate},
        )
        self.vehicles, _ = Category.objects.get_or_create(
            slug="vehicles",
            defaults={"name": "Vehicles"},
        )
        self.cars, _ = Category.objects.get_or_create(
            slug="cars",
            defaults={"name": "Cars", "parent": self.vehicles},
        )

    def _listing(self, title, category, attributes=None):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal("5250000.00"),
            category=category,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes or {},
        )

    def test_real_estate_browse_uses_table_like_result_layout(self):
        self._listing(
            "V68 real estate table home",
            self.homes_for_sale,
            {
                "m2_brut": "180",
                "m2_net": "150",
                "oda_sayisi": "4+1",
                "bulundugu_kat": "3",
                "isitma": "Kombi (Doğalgaz)",
            },
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "homes-for-sale"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REAL_ESTATE_BROWSE_RESULTS_V68")
        self.assertContains(response, '<table class="real-estate-results-table">')
        self.assertContains(response, "İlan Başlığı")
        self.assertContains(response, "m² (Brüt)")
        self.assertContains(response, "Oda Sayısı")
        self.assertContains(response, "Fiyat")
        self.assertContains(response, "İlan Tarihi")
        self.assertContains(response, "İl / İlçe")
        self.assertContains(response, "V68 real estate table home")
        self.assertContains(response, "180")
        self.assertContains(response, "4+1")

    def test_non_real_estate_browse_keeps_card_grid(self):
        self._listing(
            "V68 normal car card listing",
            self.cars,
            {"marka": "Toyota", "model": "Corolla", "yil": "2020"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="listing-grid"')
        self.assertContains(response, "V68 normal car card listing")
        self.assertNotContains(response, '<table class="real-estate-results-table">')
