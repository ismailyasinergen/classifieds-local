from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class CategoryFilterSidebarPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="category-filter-v74@classifieds.local",
            username="category_filter_v74",
            password="Testpass12345",
        )

        self.real_estate, _ = Category.objects.get_or_create(
            slug="real-estate",
            defaults={"name": "Real Estate"},
        )
        self.homes, _ = Category.objects.get_or_create(
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
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes,
        )

    def test_real_estate_filter_sidebar_uses_grouped_sahibinden_style_sections(self):
        self._listing(
            "V74 real estate filter listing",
            self.homes,
            {
                "m2_brut": "120",
                "oda_sayisi": "3+1",
                "bina_yasi": "5",
                "bulundugu_kat": "2",
                "krediye_uygun": "Evet",
            },
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "homes-for-sale"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CATEGORY_FILTER_SIDEBAR_V74")
        self.assertContains(response, "category-filter-sidebar-v74")
        self.assertContains(response, "Emlak filtreleri")
        self.assertContains(response, "Sahibinden tarzı emlak araması")
        self.assertContains(response, "Alan ve Oda")
        self.assertContains(response, "Bina ve Kullanım")
        self.assertContains(response, "Tapu / İlan Bilgileri")
        self.assertContains(response, 'name="attr_m2_brut"')
        self.assertContains(response, 'name="attr_oda_sayisi"')
        self.assertContains(response, '<table class="real-estate-results-table">')
        self.assertContains(response, "V74 real estate filter listing")

    def test_vehicle_filter_sidebar_uses_grouped_sahibinden_style_sections(self):
        self._listing(
            "V74 vehicle filter listing",
            self.cars,
            {
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
                "yakit_tipi": "Benzinli",
                "vites": "Otomatik",
            },
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CATEGORY_FILTER_SIDEBAR_V74")
        self.assertContains(response, "category-filter-sidebar-v74")
        self.assertContains(response, "Araç filtreleri")
        self.assertContains(response, "Sahibinden tarzı araç araması")
        self.assertContains(response, "Araç Özeti")
        self.assertContains(response, "Motor / Performans")
        self.assertContains(response, 'name="attr_marka"')
        self.assertContains(response, 'name="attr_yil"')
        self.assertContains(response, 'name="attr_km"')
        self.assertContains(response, '<table class="vehicle-results-table">')
        self.assertContains(response, "V74 vehicle filter listing")

    def test_generic_category_keeps_attribute_filter_sidebar_and_card_grid(self):
        self._listing(
            "V74 phone filter listing",
            self.phones,
            {"marka": "Apple", "model": "iPhone 14", "kapasite": "128 GB"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "phones"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CATEGORY_FILTER_SIDEBAR_V74")
        self.assertContains(response, "Kategori filtreleri")
        self.assertContains(response, "Kategori Detayları")
        self.assertContains(response, 'name="attr_marka"')
        self.assertContains(response, 'name="attr_kapasite"')
        self.assertContains(response, 'class="listing-grid"')
        self.assertContains(response, "V74 phone filter listing")

    def test_grouped_sidebar_preserves_filter_behavior(self):
        wanted = self._listing(
            "V74 Toyota filtered listing",
            self.cars,
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )
        self._listing(
            "V74 BMW filtered listing",
            self.cars,
            {"marka": "BMW", "model": "520i", "yil": "2018", "km": "90000"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars", "attr_marka": "Toyota"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, wanted.title)
        self.assertNotContains(response, "V74 BMW filtered listing")
        self.assertContains(response, 'value="Toyota"')
