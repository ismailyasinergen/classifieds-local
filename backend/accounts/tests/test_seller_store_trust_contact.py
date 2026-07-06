from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import SellerStore, UserProfile
from categories.models import Category
from listings.models import Listing


class SellerStoreTrustContactTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="trust_contact_seller_v109",
            email="trust-contact-seller-v109@classifieds.local",
            password="StrongPass123!",
        )
        self.buyer = User.objects.create_user(
            username="trust_contact_buyer_v109",
            email="trust-contact-buyer-v109@classifieds.local",
            password="StrongPass123!",
        )
        self.seller_profile, _ = UserProfile.objects.get_or_create(user=self.seller)
        self.seller_profile.location = "Berlin"
        self.seller_profile.save(update_fields=["location"])

        self.category = Category.objects.create(
            name="Trust Store Furniture",
            slug="trust-store-furniture-v109",
        )
        self.store = SellerStore.objects.create(
            owner=self.seller,
            name="Trusted Contact Store",
            headline="Trust signals and safer buyer actions.",
            description="A v109 store page for trust and contact testing.",
            location="Berlin",
        )

    def create_listing(self, title="Trust Contact Listing"):
        return Listing.objects.create(
            title=title,
            description="A listing for seller store trust/contact testing.",
            price=Decimal("149.00"),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

    def public_store_url(self):
        return reverse("accounts:seller_store_public", kwargs={"slug": self.store.slug})

    def test_public_store_shows_anonymous_trust_and_login_actions(self):
        self.create_listing()

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unverified seller")
        self.assertContains(response, "Member since")
        self.assertContains(response, "Store active since")
        self.assertContains(response, "Contact & safety")
        self.assertContains(response, "Login to message seller")
        self.assertContains(response, "Create account")
        self.assertNotContains(response, "Report seller")

    def test_public_store_shows_verified_seller_badge(self):
        self.seller_profile.verification_status = UserProfile.VerificationStatus.APPROVED
        self.seller_profile.save(update_fields=["verification_status"])
        self.create_listing()

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verified Seller")
        self.assertNotContains(response, "Unverified seller")

    def test_logged_in_buyer_gets_message_and_report_seller_actions(self):
        listing = self.create_listing("Buyer contact listing")
        self.client.force_login(self.buyer)

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Message seller about a listing")
        self.assertContains(
            response,
            reverse("conversations:listing_contact", kwargs={"pk": listing.pk}),
        )
        self.assertContains(response, "Report seller")
        self.assertContains(
            response,
            reverse("accounts:user_report", kwargs={"pk": self.seller.pk}),
        )

    def test_owner_gets_store_management_action_not_report_link(self):
        self.create_listing()
        self.client.force_login(self.seller)

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage my store")
        self.assertContains(response, reverse("accounts:seller_store_settings"))
        self.assertNotContains(response, "Report seller")
        self.assertNotContains(response, "Message seller about a listing")

    def test_messaging_block_disables_message_cta_but_keeps_report_link(self):
        self.seller_profile.seller_messaging_blocked_until = timezone.now() + timedelta(days=2)
        self.seller_profile.seller_messaging_block_reason = "Temporary trust and safety review"
        self.seller_profile.save(
            update_fields=[
                "seller_messaging_blocked_until",
                "seller_messaging_block_reason",
            ]
        )
        self.create_listing()
        self.client.force_login(self.buyer)

        response = self.client.get(self.public_store_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Messaging paused")
        self.assertContains(response, "Seller messaging is temporarily unavailable.")
        self.assertContains(response, "Report seller")
        self.assertNotContains(response, "Message seller about a listing")

    def test_directory_card_shows_verified_status_and_member_since(self):
        self.seller_profile.verification_status = UserProfile.VerificationStatus.APPROVED
        self.seller_profile.save(update_fields=["verification_status"])
        self.create_listing("Directory trust listing")

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trusted Contact Store")
        self.assertContains(response, "Verified Seller")
        self.assertContains(response, "Member since")
        self.assertContains(response, "seller-store-directory-trust-v109")

    def test_directory_card_shows_unverified_status_for_unverified_seller(self):
        self.create_listing("Directory unverified listing")

        response = self.client.get(reverse("accounts:seller_store_directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trusted Contact Store")
        self.assertContains(response, "Unverified seller")
        self.assertContains(response, "seller-store-directory-trust-v109")
