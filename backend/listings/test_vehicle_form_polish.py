from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import Listing


class VehicleFormPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="vehicle-form-v73@classifieds.local",
            username="vehicle_form_v73",
            password="Testpass12345",
        )
        self.client.force_login(self.seller)

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

    def test_create_form_groups_vehicle_fields(self):
        response = self.client.get(reverse("listings:listing_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VEHICLE_FORM_GROUPS_V73")
        self.assertContains(response, "Vehicle listings:")
        self.assertContains(response, "Araç Özeti")
        self.assertContains(response, "Motor ve Performans")
        self.assertContains(response, "Donanım / İlan Bilgileri")
        self.assertContains(response, "data-vehicle-form-group")
        self.assertContains(response, 'name="attr__marka"')
        self.assertContains(response, 'name="attr__model"')
        self.assertContains(response, 'name="attr__seri"')
        self.assertContains(response, 'name="attr__yil"')
        self.assertContains(response, 'name="attr__km"')
        self.assertContains(response, 'name="attr__yakit_tipi"')
        self.assertContains(response, 'name="attr__vites"')
        self.assertContains(response, 'name="attr__renk"')
        self.assertContains(response, 'name="attr__kasa_tipi"')
        self.assertContains(response, 'name="attr__motor_gucu"')
        self.assertContains(response, 'name="attr__motor_hacmi"')
        self.assertContains(response, 'name="attr__kimden"')

    def test_vehicle_form_saves_grouped_fields(self):
        count_before = Listing.objects.count()

        response = self.client.post(
            reverse("listings:listing_create"),
            {
                "title": "V73 grouped vehicle form listing",
                "description": "Vehicle form grouped fields should save.",
                "price": "975000.00",
                "category": str(self.cars.pk),
                "location": "Istanbul / Kadikoy",
                "attr__marka": "Toyota",
                "attr__model": "Corolla",
                "attr__seri": "Corolla",
                "attr__yil": "2020",
                "attr__km": "45000",
                "attr__yakit_tipi": "Benzinli",
                "attr__vites": "Otomatik",
                "attr__sanziman_cekis": "Otomatik / Önden Çekiş",
                "attr__renk": "Beyaz",
                "attr__kasa_tipi": "Sedan",
                "attr__motor_gucu": "132 hp",
                "attr__motor_hacmi": "1.6",
                "attr__kimden": "Sahibinden",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        listing = Listing.objects.filter(title="V73 grouped vehicle form listing").first()
        self.assertIsNotNone(listing)
        self.assertEqual(listing.status, Listing.Status.PENDING)
        self.assertEqual(listing.price, Decimal("975000.00"))
        self.assertEqual(listing.attributes.get("marka"), "Toyota")
        self.assertEqual(listing.attributes.get("model"), "Corolla")
        self.assertEqual(listing.attributes.get("seri"), "Corolla")
        self.assertEqual(listing.attributes.get("yil"), "2020")
        self.assertEqual(listing.attributes.get("km"), "45000")
        self.assertEqual(listing.attributes.get("yakit_tipi"), "Benzinli")
        self.assertEqual(listing.attributes.get("vites"), "Otomatik")
        self.assertEqual(listing.attributes.get("sanziman_cekis"), "Otomatik / Önden Çekiş")
        self.assertEqual(listing.attributes.get("renk"), "Beyaz")
        self.assertEqual(listing.attributes.get("kasa_tipi"), "Sedan")
        self.assertEqual(listing.attributes.get("motor_gucu"), "132 hp")
        self.assertEqual(listing.attributes.get("motor_hacmi"), "1.6")
        self.assertEqual(listing.attributes.get("kimden"), "Sahibinden")
        self.assertEqual(Listing.objects.count(), count_before + 1)

    def test_real_estate_and_generic_groups_remain_available(self):
        response = self.client.get(reverse("listings:listing_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REAL_ESTATE_FORM_GROUPS_V70")
        self.assertContains(response, "Konut Özellikleri")
        self.assertContains(response, "Bina ve Kullanım")
        self.assertContains(response, "Tapu / İlan Bilgileri")
        self.assertContains(response, "Other Category Details")
        self.assertContains(response, "data-generic-form-group")
