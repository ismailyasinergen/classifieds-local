from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.attribute_schema import get_attribute_definitions_for_category
from listings.attribute_filters import ATTRIBUTE_FILTERS_BY_CATEGORY
from listings.models import Listing


class RealEstateAttributeExpansionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="realestate-seller-v67@classifieds.local",
            username="realestate_sellerv67",
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

    def _listing(self, title, attributes):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            price=Decimal("5250000.00"),
            category=self.homes_for_sale,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes=attributes,
        )

    def test_real_estate_schema_contains_sahibinden_style_specs(self):
        keys = [
            attribute["key"]
            for attribute in get_attribute_definitions_for_category(self.homes_for_sale)
        ]

        for key in [
            "m2_brut",
            "m2_net",
            "acik_alan_m2",
            "oda_sayisi",
            "bina_yasi",
            "bulundugu_kat",
            "kat_sayisi",
            "isitma",
            "banyo_sayisi",
            "mutfak",
            "balkon",
            "asansor",
            "otopark",
            "esyali",
            "kullanim_durumu",
            "site_i_cerisinde",
            "krediye_uygun",
            "tapu_durumu",
            "kimden",
            "takas",
            "foto_video",
            "harita",
        ]:
            self.assertIn(key, keys)

    def test_real_estate_browse_filters_are_available(self):
        filter_keys = [
            spec["key"]
            for spec in ATTRIBUTE_FILTERS_BY_CATEGORY["homes-for-sale"]
        ]

        self.assertIn("m2_brut", filter_keys)
        self.assertIn("m2_net", filter_keys)
        self.assertIn("oda_sayisi", filter_keys)
        self.assertIn("isitma", filter_keys)
        self.assertIn("tapu_durumu", filter_keys)

    def test_real_estate_detail_and_card_show_core_specs(self):
        listing = self._listing(
            "Kadikoy 4+1 real estate v67",
            {
                "m2_brut": "180",
                "m2_net": "150",
                "oda_sayisi": "4+1",
                "bulundugu_kat": "3",
                "kat_sayisi": "8",
                "isitma": "Kombi (Doğalgaz)",
                "banyo_sayisi": "2",
                "mutfak": "Kapalı",
                "balkon": True,
                "asansor": True,
                "otopark": "Kapalı Otopark",
                "esyali": False,
                "krediye_uygun": True,
                "tapu_durumu": "Kat Mülkiyetli",
                "kimden": "Sahibinden",
            },
        )

        response = self.client.get(listing.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "m² (Brüt)")
        self.assertContains(response, "180")
        self.assertContains(response, "Oda Sayısı")
        self.assertContains(response, "4+1")
        self.assertContains(response, "Kat Mülkiyetli")

        highlights = {item["key"]: item["value"] for item in listing.card_highlights}
        self.assertEqual(highlights.get("m2_brut"), "180")
        self.assertEqual(highlights.get("oda_sayisi"), "4+1")

    def test_real_estate_global_browse_filters_by_specs(self):
        self._listing(
            "Matching 4+1 real estate v67",
            {
                "m2_brut": "180",
                "oda_sayisi": "4+1",
                "isitma": "Kombi (Doğalgaz)",
            },
        )
        self._listing(
            "Nonmatching 1+1 real estate v67",
            {
                "m2_brut": "60",
                "oda_sayisi": "1+1",
                "isitma": "Klima",
            },
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "category": "homes-for-sale",
                "attr_oda_sayisi": "4+1",
                "attr_m2_brut": "180",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Matching 4+1 real estate v67")
        self.assertNotContains(response, "Nonmatching 1+1 real estate v67")
        self.assertContains(response, 'name="attr_oda_sayisi"')
        self.assertContains(response, 'name="attr_m2_brut"')
