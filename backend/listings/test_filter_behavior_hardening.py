from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class FilterBehaviorHardeningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="filter-hardening-v75@classifieds.local",
            username="filter_hardening_v75",
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

    def _listing(self, title, category, price, attributes):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal(price),
            category=category,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes,
        )

    def test_numeric_range_inputs_render_for_real_estate_and_vehicle_filters(self):
        home_response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "homes-for-sale"},
        )
        car_response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars"},
        )

        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, "FILTER_BEHAVIOR_HARDENING_V75")
        self.assertContains(home_response, 'name="attr_m2_brut"')
        self.assertContains(home_response, 'name="attr_m2_brut_min"')
        self.assertContains(home_response, 'name="attr_m2_brut_max"')
        self.assertContains(home_response, 'name="attr_m2_net_min"')

        self.assertEqual(car_response.status_code, 200)
        self.assertContains(car_response, 'name="attr_yil"')
        self.assertContains(car_response, 'name="attr_yil_min"')
        self.assertContains(car_response, 'name="attr_yil_max"')
        self.assertContains(car_response, 'name="attr_km_min"')
        self.assertContains(car_response, 'name="attr_km_max"')
        self.assertContains(car_response, 'name="attr_marka"')

    def test_real_estate_numeric_min_and_max_filters(self):
        self._listing(
            "V75 Home Big 120",
            self.homes,
            "2500000.00",
            {"m2_brut": "120", "oda_sayisi": "3+1"},
        )
        self._listing(
            "V75 Home Small 80",
            self.homes,
            "1500000.00",
            {"m2_brut": "80", "oda_sayisi": "2+1"},
        )

        min_response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "homes-for-sale", "attr_m2_brut_min": "100"},
        )
        max_response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "homes-for-sale", "attr_m2_brut_max": "100"},
        )

        self.assertEqual(min_response.status_code, 200)
        self.assertContains(min_response, "V75 Home Big 120")
        self.assertNotContains(min_response, "V75 Home Small 80")

        self.assertEqual(max_response.status_code, 200)
        self.assertContains(max_response, "V75 Home Small 80")
        self.assertNotContains(max_response, "V75 Home Big 120")

    def test_vehicle_numeric_filters_combine_with_text_filters(self):
        self._listing(
            "V75 Toyota 2020 45000",
            self.cars,
            "975000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )
        self._listing(
            "V75 Toyota 2018 90000",
            self.cars,
            "850000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2018", "km": "90000"},
        )
        self._listing(
            "V75 BMW 2021 30000",
            self.cars,
            "1750000.00",
            {"marka": "BMW", "model": "520i", "yil": "2021", "km": "30000"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "cars",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V75 Toyota 2020 45000")
        self.assertNotContains(response, "V75 Toyota 2018 90000")
        self.assertNotContains(response, "V75 BMW 2021 30000")
        self.assertContains(response, 'value="2019"')
        self.assertContains(response, 'value="50000"')

    def test_numeric_parser_accepts_dotted_thousands_values(self):
        self._listing(
            "V75 Home Large Dotted",
            self.homes,
            "3500000.00",
            {"m2_brut": "1.200", "oda_sayisi": "5+1"},
        )
        self._listing(
            "V75 Home Medium Plain",
            self.homes,
            "2400000.00",
            {"m2_brut": "850", "oda_sayisi": "4+1"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "homes-for-sale", "attr_m2_brut_min": "1.000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V75 Home Large Dotted")
        self.assertNotContains(response, "V75 Home Medium Plain")

    def test_existing_price_filters_still_work_with_numeric_attribute_filters(self):
        self._listing(
            "V75 Price Match Toyota",
            self.cars,
            "975000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )
        self._listing(
            "V75 Price Low Toyota",
            self.cars,
            "850000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )
        self._listing(
            "V75 Price High Toyota",
            self.cars,
            "1750000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "cars",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_yil_min": "2019",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V75 Price Match Toyota")
        self.assertNotContains(response, "V75 Price Low Toyota")
        self.assertNotContains(response, "V75 Price High Toyota")
