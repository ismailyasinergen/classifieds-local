from accounts.tests.mfa_support import authenticate_client
from uuid import uuid4

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from conversations.models import Conversation, Message, Participant
from conversations.services import block_user
from listings.models import Listing, ListingRevision
from listings.services import create_listing_draft
from .helpers import ConversationFixtures


@override_settings(PILOT_NEW_CONTACTS_PER_HOUR=1, PILOT_MESSAGES_PER_HOUR=1,
                   PILOT_NEW_LISTINGS_PER_DAY=1)
class RateLimitHTTPTests(ConversationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.buyer)

    def url(self, name, obj=None):
        return reverse("conversations:" + name, args=[(obj or self.listing).pk])

    def post(self, name, obj=None, body="<script>retained & body</script>", token=None):
        return self.client.post(self.url(name, obj), {"body": body, "client_token": token or uuid4()})

    def limited(self, response, message):
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response["Retry-After"].isascii())
        self.assertTrue(response["Retry-After"].isdecimal())
        self.assertGreaterEqual(int(response["Retry-After"]), 1)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertContains(response, message, status_code=429)
        for user in (self.buyer, self.seller, self.outsider):
            self.assertNotContains(response, user.email, status_code=429)

    def test_contact_429_keeps_escaped_body_and_unchanged_token(self):
        self.start()
        second = self.public_listing(owner=self.outsider)
        token = uuid4()
        response = self.post("start", second, token=token)
        self.limited(response, "Yeni görüşme sınırına")
        self.assertContains(response, "&lt;script&gt;retained &amp; body&lt;/script&gt;", status_code=429)
        self.assertNotContains(response, "<script>retained", status_code=429)
        self.assertEqual(str(response.context["form"]["client_token"].value()), str(token))
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 2)

    def test_send_429_keeps_body_token_and_replay_conflict_contracts(self):
        token = uuid4()
        first = self.start(token=token)
        response = self.post("send", first.conversation)
        self.limited(response, "Mesaj gönderme sınırına")
        self.assertContains(response, "&lt;script&gt;retained &amp; body&lt;/script&gt;", status_code=429)
        form = response.context["form"]
        self.assertEqual(str(form["client_token"].value()), str(form.data["client_token"]))
        for name, obj in (("start", self.listing), ("send", first.conversation)):
            self.assertEqual(self.post(name, obj, body=first.body, token=token).status_code, 302)
            conflict = self.post(name, obj, body="Different", token=token)
            self.assertEqual(conflict.status_code, 409)
            self.assertNotIn("Retry-After", conflict)
            self.assertNotEqual(str(conflict.context["form"]["client_token"].value()), str(token))
        self.assertEqual(Message.objects.count(), 1)

    def test_listing_429_retains_category_and_explains_existing_drafts(self):
        create_listing_draft(actor=self.buyer, category_id=self.category.pk, content={})
        response = self.client.post(reverse("listings:create"), {"category": self.category.pk})
        self.limited(response, "Mevcut taslaklarınızı düzenlemeye devam")
        self.assertEqual(str(response.context["form"]["category"].value()), str(self.category.pk))
        self.assertContains(response, f'value="{self.category.pk}" selected', status_code=429)
        self.assertEqual(Listing.objects.filter(owner=self.buyer).count(), 1)

    def test_auth_csrf_validation_permission_missing_and_identity_precedence(self):
        first = self.start()
        second = self.public_listing()
        self.assertEqual(self.post("start", second, body="").status_code, 400)
        self.assertEqual(self.post("send", first.conversation, body="").status_code, 400)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.buyer)
        self.assertEqual(csrf.post(self.url("start", second), {"body": "ok", "client_token": uuid4()}).status_code, 403)
        self.assertEqual(csrf.post(reverse("listings:create"), {"category": self.category.pk}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.post("start", second).status_code, 302)
        self.assertEqual(self.client.post(reverse("listings:create"), {"category": self.category.pk}).status_code, 302)
        authenticate_client(self.client, self.outsider)
        self.assertEqual(self.post("send", first.conversation).status_code, 404)
        self.client.force_login(self.seller)
        self.assertEqual(self.post("start").status_code, 403)
        self.client.force_login(self.buyer)
        self.assertEqual(self.post("start", type("Missing", (), {"pk": uuid4()})()).status_code, 404)
        block_user(actor=self.seller, other_user_id=self.buyer.pk)
        self.assertEqual(self.post("send", first.conversation).status_code, 403)
        self.assertEqual(self.post("start", second).status_code, 403)
        Listing.objects.filter(pk=self.listing.pk).update(owner=self.outsider)
        self.assertEqual(self.post("start", token=first.client_token, body=first.body).status_code, 400)
        User.objects.filter(pk=self.buyer.pk).update(is_active=False)
        # Django rejects the inactive session during authentication.
        self.assertEqual(self.post("start", second).status_code, 302)

    def test_listing_ordinary_invalid_category_keeps_existing_response(self):
        create_listing_draft(actor=self.buyer, category_id=self.category.pk, content={})
        response = self.client.post(reverse("listings:create"), {"category": "missing"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Retry-After", response)

    def test_exhaustion_does_not_affect_advisory_get_history_or_state_operations(self):
        first = self.start()
        second = self.public_listing()
        for url in (self.url("start", second), self.url("detail", first.conversation),
                    self.url("history", first.conversation), reverse("conversations:inbox"),
                    reverse("listings:create")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("Retry-After", response)
        for name in ("mark_read", "archive", "unarchive", "block", "unblock"):
            response = self.client.post(self.url(name, first.conversation),
                                        {"through_message_id": first.pk})
            self.assertEqual(response.status_code, 302)
        draft = create_listing_draft(actor=self.buyer, category_id=self.category.pk, content={})
        self.assertEqual(self.client.get(reverse("listings:edit", args=[draft.pk])).status_code, 200)
        response = self.client.post(reverse("listings:edit", args=[draft.pk]), {
            "edit_version": 1, "title": "Updated", "description": "", "price": "",
            "currency": "", "location": "",
        })
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.title, "Updated")
        self.assertEqual(ListingRevision.objects.filter(listing__owner=self.buyer).count(), 1)
