from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from categories.models import Category
from conversations.models import ListingMessage
from conversations.views import build_conversation_threads
from listings.models import Listing


class ConversationThreadQueryEfficiencyR004Tests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.buyer = user_model.objects.create_user(
            username="r004-buyer",
            password="StrongPass123!",
        )
        self.sellers = [
            user_model.objects.create_user(
                username=f"r004-seller-{index}",
                password="StrongPass123!",
            )
            for index in range(2)
        ]
        category = Category.objects.create(
            name="R004 conversations",
            slug="r004-conversations",
        )
        self.listings = [
            Listing.objects.create(
                title=f"R004 listing {index}",
                description="Conversation query regression fixture.",
                price=Decimal("100.00"),
                location="Berlin",
                category=category,
                owner=seller,
                status=Listing.Status.APPROVED,
            )
            for index, seller in enumerate(self.sellers)
        ]

        ListingMessage.objects.create(
            listing=self.listings[0],
            sender=self.sellers[0],
            recipient=self.buyer,
            body="First unread message.",
        )
        ListingMessage.objects.create(
            listing=self.listings[0],
            sender=self.sellers[0],
            recipient=self.buyer,
            body="Second unread message.",
        )
        ListingMessage.objects.create(
            listing=self.listings[1],
            sender=self.sellers[1],
            recipient=self.buyer,
            body="Read message.",
            is_read=True,
        )

    def test_thread_grouping_uses_constant_query_count(self):
        with self.assertNumQueries(2):
            threads = build_conversation_threads(self.buyer)

        unread_by_listing = {
            thread.listing.pk: thread.unread_count
            for thread in threads
        }
        self.assertEqual(
            unread_by_listing,
            {
                self.listings[0].pk: 2,
                self.listings[1].pk: 0,
            },
        )
