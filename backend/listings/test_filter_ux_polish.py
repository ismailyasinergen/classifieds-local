from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class FilterUxPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="filter-ux-v76@classifieds.local",
            username="filter_ux_v76",
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

    def test_active_filter_chips_render_clear_links_for_category_price_search_and_attributes(self):
        self._listing(
            "V76 Toyota chip listing",
            self.cars,
            "975000.00",
            {
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
            },
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "cars",
                "q": "Toyota",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FILTER_UX_POLISH_V76")
        self.assertContains(response, "active-filter-list-v76")
        self.assertContains(response, "Clear this filter")
        self.assertContains(response, "Clear all filters")
        self.assertContains(response, 'data-clear-filter-param="category"')
        self.assertContains(response, 'data-clear-filter-param="q"')
        self.assertContains(response, 'data-clear-filter-param="min_price"')
        self.assertContains(response, 'data-clear-filter-param="max_price"')
        self.assertContains(response, 'data-clear-filter-param="attr_marka"')
        self.assertContains(response, 'data-clear-filter-param="attr_yil_min,attr_yil_max"')
        self.assertContains(response, 'data-clear-filter-param="attr_km_min,attr_km_max"')
        self.assertContains(response, "V76 Toyota chip listing")

    def test_clear_one_attribute_filter_link_preserves_other_filters(self):
        self._listing(
            "V76 Clear Link Toyota",
            self.cars,
            "975000.00",
            {
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
            },
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

        chips = {
            chip["clear_param"]: chip
            for chip in response.context["active_filter_chips"]
        }

        marka_clear_url = chips["attr_marka"]["clear_url"]
        self.assertNotIn("attr_marka=", marka_clear_url)
        self.assertIn("category=cars", marka_clear_url)
        self.assertIn("attr_yil_min=2019", marka_clear_url)
        self.assertIn("attr_km_max=50000", marka_clear_url)

        year_clear_url = chips["attr_yil_min,attr_yil_max"]["clear_url"]
        self.assertNotIn("attr_yil_min=", year_clear_url)
        self.assertNotIn("attr_yil_max=", year_clear_url)
        self.assertIn("attr_marka=Toyota", year_clear_url)
        self.assertIn("attr_km_max=50000", year_clear_url)

    def test_category_clear_link_removes_attribute_filters_because_they_are_category_specific(self):
        self._listing(
            "V76 Category Clear Home",
            self.homes,
            "2500000.00",
            {"m2_brut": "120", "oda_sayisi": "3+1"},
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "homes-for-sale",
                "q": "Home",
                "attr_m2_brut_min": "100",
                "attr_m2_brut_max": "150",
            },
        )

        chips = {
            chip["clear_param"]: chip
            for chip in response.context["active_filter_chips"]
        }
        category_clear_url = chips["category"]["clear_url"]

        self.assertNotIn("category=", category_clear_url)
        self.assertNotIn("attr_m2_brut_min=", category_clear_url)
        self.assertNotIn("attr_m2_brut_max=", category_clear_url)
        self.assertIn("q=Home", category_clear_url)

    def test_no_active_filter_chips_render_without_active_filters(self):
        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<div class="active-filter-list active-filter-list-v76"')
        self.assertEqual(response.context["active_filter_chips"], [])

    def test_v75_numeric_filter_behavior_is_preserved_after_v76_chip_polish(self):
        self._listing(
            "V76 Numeric Toyota Match",
            self.cars,
            "975000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2020", "km": "45000"},
        )
        self._listing(
            "V76 Numeric Toyota Old",
            self.cars,
            "850000.00",
            {"marka": "Toyota", "model": "Corolla", "yil": "2018", "km": "90000"},
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
        self.assertContains(response, "V76 Numeric Toyota Match")
        self.assertNotContains(response, "V76 Numeric Toyota Old")
        self.assertContains(response, "Clear this filter")
