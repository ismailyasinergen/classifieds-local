from uuid import uuid4

from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision


class ConversationFixtures:
    def setUp(self):
        self.seller = User.objects.create_user("seller@example.test")
        self.buyer = User.objects.create_user("buyer@example.test")
        self.outsider = User.objects.create_user("outsider@example.test", is_staff=True, is_superuser=True)
        self.category = Category.objects.create(name="Otomobil", slug="auto")
        self.schema = AttributeSchema.objects.create(category=self.category, version=1, definition={"fields": {}})
        self.listing = self.public_listing()

    def public_listing(self, owner=None, title="Onaylı başlık"):
        listing = Listing.objects.create(owner=owner or self.seller)
        revision = ListingRevision.objects.create(
            listing=listing, category=self.category, attribute_schema=self.schema,
            schema_version=1, status=ListingRevision.Status.APPROVED,
            title=title, description="Public content")
        listing.lifecycle = Listing.Lifecycle.LIVE
        listing.public_revision = revision
        listing.save()
        return listing

    def start(self, actor=None, listing=None, body="İlk mesaj", token=None):
        from conversations.services import start_conversation
        return start_conversation(actor=actor or self.buyer, listing_id=(listing or self.listing).pk,
                                  body=body, client_token=token or uuid4())

    def send(self, conversation, actor=None, body="Yanıt", token=None):
        from conversations.services import send_message
        return send_message(actor=actor or self.seller, conversation_id=conversation.pk,
                            body=body, client_token=token or uuid4())
