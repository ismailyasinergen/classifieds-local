from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


class RealEstateFormPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="realestate-form-v70@classifieds.local",
            username="realestate_form_v70",
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

    def test_create_form_groups_real_estate_fields(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("listings:listing_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REAL_ESTATE_FORM_GROUPS_V70")
        self.assertContains(response, "category-details-panel-v70")
        self.assertContains(response, "Konut Özellikleri")
        self.assertContains(response, "Bina ve Kullanım")
        self.assertContains(response, "Tapu / İlan Bilgileri")
        self.assertContains(response, "Other Category Details")
        self.assertContains(response, "data-real-estate-form-group")
        self.assertContains(response, "data-generic-form-group")

        for field_name in [
            "attr__m2_brut",
            "attr__m2_net",
            "attr__oda_sayisi",
            "attr__bina_yasi",
            "attr__bulundugu_kat",
            "attr__kat_sayisi",
            "attr__isitma",
            "attr__banyo_sayisi",
            "attr__mutfak",
            "attr__balkon",
            "attr__asansor",
            "attr__otopark",
            "attr__esyali",
            "attr__kullanim_durumu",
            "attr__site_i_cerisinde",
            "attr__krediye_uygun",
            "attr__tapu_durumu",
            "attr__kimden",
            "attr__takas",
        ]:
            self.assertContains(response, f'name="{field_name}"')

    def test_real_estate_form_still_saves_grouped_fields(self):
        self.client.force_login(self.seller)
        before_count = Listing.objects.count()

        response = self.client.post(
            reverse("listings:listing_create"),
            {
                "title": "V70 grouped form real estate listing",
                "description": "Real estate grouped form smoke test.",
                "price": "5250000.00",
                "category": str(self.homes_for_sale.pk),
                "location": "Istanbul / Kadikoy",
                "attr__m2_brut": "180",
                "attr__m2_net": "150",
                "attr__oda_sayisi": "4+1",
                "attr__bulundugu_kat": "3",
                "attr__kat_sayisi": "8",
                "attr__isitma": "Kombi (Doğalgaz)",
                "attr__banyo_sayisi": "2",
                "attr__mutfak": "Kapalı",
                "attr__balkon": "true",
                "attr__asansor": "true",
                "attr__otopark": "Kapalı Otopark",
                "attr__krediye_uygun": "true",
                "attr__tapu_durumu": "Kat Mülkiyetli",
                "attr__kimden": "Sahibinden",
                "attr__takas": "false",
            },
            follow=True,
        )

        listing = Listing.objects.filter(
            title="V70 grouped form real estate listing"
        ).order_by("-id").first()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(listing)
        self.assertEqual(listing.status, Listing.Status.PENDING)
        self.assertEqual(listing.attributes["m2_brut"], "180")
        self.assertEqual(listing.attributes["oda_sayisi"], "4+1")
        self.assertIs(listing.attributes["balkon"], True)
        self.assertIs(listing.attributes["takas"], False)
        self.assertEqual(Listing.objects.count(), before_count + 1)

        listing.delete()

    def test_non_real_estate_form_fields_remain_available(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("listings:listing_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Other Category Details")
        self.assertContains(response, 'name="attr__marka"')
        self.assertContains(response, 'name="attr__model"')
        self.assertContains(response, 'name="attr__yil"')
