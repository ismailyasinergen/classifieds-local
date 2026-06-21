from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class RealEstateDetailSpecsPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="realestate-detail-v69@classifieds.local",
            username="realestate_detail_v69",
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

    def test_real_estate_detail_has_grouped_specs_panel(self):
        listing = self._listing(
            "V69 grouped real estate specs",
            self.homes_for_sale,
            {
                "m2_brut": "180",
                "m2_net": "150",
                "acik_alan_m2": "25",
                "oda_sayisi": "4+1",
                "bina_yasi": "5-10 arası",
                "bulundugu_kat": "3",
                "kat_sayisi": "8",
                "isitma": "Kombi (Doğalgaz)",
                "banyo_sayisi": "2",
                "mutfak": "Kapalı",
                "balkon": True,
                "asansor": True,
                "otopark": "Kapalı Otopark",
                "esyali": False,
                "kullanim_durumu": "Boş",
                "site_i_cerisinde": True,
                "site_adi": "Deniz Sitesi",
                "aidat_tl": "1200",
                "krediye_uygun": True,
                "tapu_durumu": "Kat Mülkiyetli",
                "kimden": "Sahibinden",
                "takas": False,
                "foto_video": "Fotoğraflı",
                "harita": True,
            },
        )

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REAL_ESTATE_DETAIL_SPECS_V69")
        self.assertContains(response, "real-estate-detail-summary")
        self.assertContains(response, '<div class="real-estate-specs-panel"')
        self.assertContains(response, "Konut Özellikleri")
        self.assertContains(response, "Bina ve Kullanım")
        self.assertContains(response, "Tapu / İlan Bilgileri")
        self.assertContains(response, "m² (Brüt)")
        self.assertContains(response, "180")
        self.assertContains(response, "Oda Sayısı")
        self.assertContains(response, "4+1")
        self.assertContains(response, "Tapu Durumu")
        self.assertContains(response, "Kat Mülkiyetli")
        self.assertContains(response, "Site Adı")
        self.assertContains(response, "Deniz Sitesi")
        self.assertContains(response, "Krediye Uygun")
        self.assertContains(response, "Evet")
        self.assertContains(response, "Takaslı")
        self.assertContains(response, "Hayır")

    def test_non_real_estate_detail_keeps_generic_detail_grid(self):
        listing = self._listing(
            "V69 normal car detail specs",
            self.cars,
            {"marka": "Toyota", "model": "Corolla", "yil": "2020"},
        )

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "classified-detail-grid")
        self.assertContains(response, "V69 normal car detail specs")
        self.assertNotContains(response, '<div class="real-estate-specs-panel"')
