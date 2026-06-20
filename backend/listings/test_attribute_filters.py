from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class AttributeBrowseFilterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="attribute_filter_seller@classifieds.local",
            username="attributefilterseller",
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

        self.bmw = self._listing(
            "BMW 520i",
            self.cars,
            {"marka": "BMW", "model": "520i", "yil": "2018", "km": "90000"},
        )
        self.audi = self._listing(
            "Audi A4",
            self.cars,
            {"marka": "Audi", "model": "A4", "yil": "2017", "km": "110000"},
        )
        self.iphone = self._listing(
            "iPhone 14 Pro",
            self.phones,
            {"marka": "Apple", "model": "iPhone 14 Pro", "kapasite": "128 GB"},
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

    def test_global_browse_filters_by_selected_category_attribute(self):
        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars", "attr_marka": "BMW"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BMW 520i")
        self.assertNotContains(response, "Audi A4")
        self.assertNotContains(response, "iPhone 14 Pro")
        self.assertContains(response, 'name="attr_marka"')

    def test_category_page_filters_by_attribute(self):
        response = self.client.get(
            reverse("categories:category_detail", kwargs={"slug": "cars"}),
            {"attr_model": "520i"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BMW 520i")
        self.assertNotContains(response, "Audi A4")
        self.assertContains(response, 'name="attr_model"')

    def test_attribute_filter_keeps_pagination_querystring(self):
        for index in range(14):
            self._listing(
                f"BMW extra {index}",
                self.cars,
                {"marka": "BMW", "model": f"extra-{index}"},
            )

        response = self.client.get(
            reverse("listings:listing_list"),
            {"category": "cars", "attr_marka": "BMW"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "attr_marka=BMW")
        self.assertContains(response, "category=cars")
