from accounts.tests.mfa_support import authenticate_client
from uuid import uuid4

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.test.utils import CaptureQueriesContext
from django.db import connection

from conversations.models import Conversation, Message, Participant, UserBlock
from listings.models import Listing
from .helpers import ConversationFixtures


class ConversationHTTPTests(ConversationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.buyer)

    def url(self, name, conversation=None):
        if name in ("start", "contact"):
            return reverse("conversations:" + name, args=[self.listing.pk])
        if name == "inbox":
            return reverse("conversations:inbox")
        return reverse("conversations:" + name, args=[conversation.pk])

    def post_message(self, name="start", conversation=None, body="Merhaba", token=None):
        return self.client.post(self.url(name, conversation), {"body": body, "client_token": token or uuid4()})

    def private(self, response, status=200):
        self.assertEqual(response.status_code, status)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        for email in [self.seller.email, self.buyer.email, self.outsider.email]:
            self.assertNotContains(response, email, status_code=status)

    def test_anonymous_login_return_for_inbox_and_start(self):
        self.client.logout()
        for name in ["inbox", "start"]:
            response = self.client.get(self.url(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/?next=", response.url)
            self.assertIn(self.url(name), response.url)

    def test_first_send_prg_and_existing_start_redirect(self):
        self.private(self.client.get(self.url("start")))
        response = self.post_message()
        conversation = Conversation.objects.get()
        self.assertRedirects(response, self.url("detail", conversation))
        self.assertEqual(Message.objects.get().body, "Merhaba")
        self.assertEqual(Participant.objects.count(), 2)
        self.assertRedirects(self.client.get(self.url("start")), self.url("detail", conversation))

    def test_participant_reply_and_fixed_redirect_ignore_posted_next(self):
        conversation = self.start().conversation
        self.client.force_login(self.seller)
        response = self.client.post(self.url("send", conversation), {
            "body": "Yanıt", "client_token": uuid4(), "next": "https://example.test"})
        self.assertRedirects(response, self.url("detail", conversation))
        self.assertEqual(Message.objects.order_by("-sequence").first().sender_id, self.seller.pk)

    def test_self_start_denied(self):
        self.client.force_login(self.seller)
        self.private(self.client.get(self.url("start")), 403)
        self.private(self.post_message(), 403)
        self.assertFalse(Conversation.objects.exists())

    def test_outsider_staff_and_injected_participant_cannot_access_any_endpoint(self):
        conversation = self.start().conversation
        Participant.objects.create(conversation=conversation, user=self.outsider)
        authenticate_client(self.client, self.outsider)
        for name in ["detail", "history"]:
            self.private(self.client.get(self.url(name, conversation)), 404)
        for name in ["send", "mark_read", "archive", "unarchive", "block", "unblock"]:
            self.private(self.client.post(self.url(name, conversation), {
                "body": "Denied", "client_token": uuid4(), "through_message_id": Message.objects.get().pk}), 404)
        self.private(self.client.get(self.url("inbox")))
        self.assertEqual(len(self.client.get(self.url("inbox")).context["page_obj"]), 0)
        self.assertEqual(Message.objects.count(), 1)
        self.assertFalse(UserBlock.objects.exists())

    def test_absent_thread_and_malformed_uuid_are_404(self):
        for value in ["not-uuid", str(uuid4())]:
            for suffix in ["", "mesajlar/", "gonder/", "okundu/", "arsivle/", "engelle/"]:
                path = "/mesajlar/" + value + "/" + suffix
                response = self.client.post(path) if suffix in ["gonder/", "okundu/", "arsivle/", "engelle/"] else self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_all_mutations_reject_get_and_missing_csrf(self):
        conversation = self.start().conversation
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.buyer)
        for name in ["contact", "send", "mark_read", "archive", "unarchive", "block", "unblock"]:
            url = self.url(name, conversation)
            self.private(self.client.get(url), 405)
            self.assertEqual(csrf.post(url).status_code, 403)
        self.assertEqual(csrf.post(self.url("start"), {"body": "No csrf", "client_token": uuid4()}).status_code, 403)
        self.assertEqual(Message.objects.count(), 1)

    def test_body_limits_unicode_normalization_and_no_utf16_maxlength(self):
        response = self.client.get(self.url("start"))
        self.assertNotContains(response, 'maxlength="4000"')
        for body in ["", " \r\n ", "a\x00b", "x" * 4001, " " * 8001]:
            self.private(self.post_message(body=body), 400)
        self.assertFalse(Conversation.objects.exists())
        self.assertEqual(self.post_message(body="😀" * 4000).status_code, 302)
        self.assertEqual(len(Message.objects.get().body), 4000)
        conversation = Conversation.objects.get()
        self.assertEqual(self.post_message("send", conversation, " a\rb\r\nc ").status_code, 302)
        self.assertEqual(Message.objects.order_by("-sequence").first().body, "a\nb\nc")

    def test_malformed_token_body_retained_and_escaped(self):
        response = self.post_message(body="<script>alert(1)</script>", token="broken")
        self.private(response, 400)
        self.assertContains(response, "&lt;script&gt;", status_code=400)
        self.assertNotContains(response, "<script>alert(1)</script>", status_code=400)
        self.assertFalse(Conversation.objects.exists())

    def test_token_retry_conflict_retains_text_and_offers_new_token(self):
        token = uuid4()
        self.post_message(token=token)
        conversation = Conversation.objects.get()
        before = Conversation.objects.values().get()
        self.assertEqual(self.post_message(token=token).status_code, 302)
        self.assertEqual(Conversation.objects.values().get(), before)
        response = self.post_message("send", conversation, "<script>changed</script>", token)
        self.private(response, 409)
        self.assertContains(response, "&lt;script&gt;", status_code=409)
        self.assertNotEqual(str(response.context["form"]["client_token"].value()), str(token))
        self.assertEqual(Message.objects.count(), 1)

    def test_pages_fragments_preview_and_bound_errors_do_not_leak_private_metadata(self):
        conversation = self.start(body="<script>hello</script>").conversation
        for name in ["inbox", "detail", "history"]:
            response = self.client.get(self.url(name, conversation))
            self.private(response)
            self.assertContains(response, "&lt;script&gt;")
            self.assertNotContains(response, "<script>hello</script>")
        self.private(self.post_message("send", conversation, "x" * 4001), 400)

    def test_gets_and_poll_do_not_write_read_or_archive_state(self):
        conversation = self.start().conversation
        before = list(Participant.objects.values())
        for name in ["inbox", "detail", "history"]:
            self.client.get(self.url(name, conversation))
        response = self.client.get(self.url("history", conversation), {"after_sequence": conversation.last_sequence})
        self.private(response, 204)
        self.assertEqual(list(Participant.objects.values()), before)

    def test_poll_permission_precedes_204_and_invalid_sequence_is_404(self):
        conversation = self.start().conversation
        authenticate_client(self.client, self.outsider)
        self.private(self.client.get(self.url("history", conversation), {"after_sequence": 1}), 404)
        self.client.force_login(self.buyer)
        for value in ["-1", "1e3", "١", "9223372036854775808"]:
            self.private(self.client.get(self.url("history", conversation), {"after_sequence": value}), 404)

    def test_explicit_read_keeps_later_incoming_unread_and_is_monotonic(self):
        conversation = self.start().conversation
        displayed = self.send(conversation)
        response = self.client.get(self.url("detail", conversation))
        self.assertEqual(response.context["through_message_id"], displayed.pk)
        later = self.send(conversation, body="Later")
        self.assertEqual(self.client.post(self.url("mark_read", conversation),
                                         {"through_message_id": displayed.pk}).status_code, 302)
        participant = Participant.objects.get(conversation=conversation, user=self.buyer)
        self.assertEqual(participant.last_read_sequence, displayed.sequence)
        self.assertTrue(self.client.get(self.url("inbox")).context["page_obj"][0].has_unread)
        self.client.post(self.url("mark_read", conversation), {"through_message_id": Message.objects.order_by("sequence").first().pk})
        participant.refresh_from_db()
        self.assertEqual(participant.last_read_sequence, displayed.sequence)
        self.assertGreater(later.sequence, participant.last_read_sequence)

    def test_malformed_and_foreign_read_ids_never_change_state(self):
        conversation = self.start().conversation
        foreign = self.start(listing=self.public_listing())
        for value in ["", "-1", "0", "1.0", "١", "9223372036854775808", str(foreign.pk)]:
            self.private(self.client.post(self.url("mark_read", conversation), {"through_message_id": value}), 400)
        self.assertEqual(Participant.objects.get(conversation=conversation, user=self.buyer).last_read_sequence, 0)

    def test_personal_archive_and_incoming_unarchive(self):
        conversation = self.start().conversation
        self.assertEqual(self.client.post(self.url("archive", conversation)).status_code, 302)
        self.assertEqual(len(self.client.get(self.url("inbox")).context["page_obj"]), 0)
        self.assertEqual(len(self.client.get(self.url("inbox"), {"archived": "1"}).context["page_obj"]), 1)
        self.assertIsNone(Participant.objects.get(conversation=conversation, user=self.seller).archived_at)
        self.send(conversation)
        self.assertEqual(len(self.client.get(self.url("inbox")).context["page_obj"]), 1)
        self.client.post(self.url("archive", conversation))
        self.client.post(self.url("unarchive", conversation))
        self.assertIsNone(Participant.objects.get(conversation=conversation, user=self.buyer).archived_at)

    def test_directional_block_derived_from_thread_and_owned_unblock(self):
        conversation = self.start().conversation
        self.client.post(self.url("block", conversation), {"other_user_id": self.outsider.pk})
        self.assertTrue(UserBlock.objects.filter(blocker=self.buyer, blocked=self.seller).exists())
        self.assertFalse(UserBlock.objects.filter(blocked=self.outsider).exists())
        self.private(self.post_message("send", conversation), 403)
        self.client.force_login(self.seller)
        self.client.post(self.url("unblock", conversation))
        self.private(self.post_message("send", conversation), 403)
        self.client.post(self.url("block", conversation))
        self.client.force_login(self.buyer)
        self.client.post(self.url("unblock", conversation))
        self.private(self.post_message("send", conversation), 403)
        self.client.force_login(self.seller)
        self.client.post(self.url("unblock", conversation))
        self.assertEqual(self.post_message("send", conversation).status_code, 302)

    def test_contact_requires_owner_strict_boolean_and_preserves_public_visibility(self):
        self.private(self.client.post(self.url("contact"), {"enabled": "0"}), 403)
        self.client.force_login(self.seller)
        for value in ["false", "", "2", "true"]:
            self.private(self.client.post(self.url("contact"), {"enabled": value}), 400)
        self.assertEqual(self.client.post(self.url("contact"), {"enabled": "0"}).status_code, 302)
        self.listing.refresh_from_db()
        self.assertFalse(self.listing.contact_enabled)
        self.assertEqual(self.client.get(reverse("listings:detail", args=[self.listing.pk])).status_code, 200)
        self.client.force_login(self.buyer)
        self.private(self.client.get(self.url("start")), 403)

    def test_closed_listing_preserves_existing_history_and_reply(self):
        conversation = self.start().conversation
        Listing.objects.filter(pk=self.listing.pk).update(lifecycle="closed", contact_enabled=False)
        response = self.client.get(self.url("detail", conversation))
        self.private(response)
        self.assertContains(response, "İlan artık yayında değil.")
        self.assertEqual(self.post_message("send", conversation).status_code, 302)
        authenticate_client(self.client, self.outsider)
        self.private(self.post_message(), 403)

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=13)
    def test_inbox_13_threads_sql_page_12_ties_and_archived_retention(self):
        for index in range(13):
            self.start(listing=self.public_listing(title=f"Konu {index}"))
        at = timezone.now()
        Conversation.objects.update(last_message_at=at)
        expected = list(Conversation.objects.order_by("-pk").values_list("pk", flat=True))
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url("inbox"))
        self.private(response)
        self.assertEqual([row.pk for row in response.context["page_obj"]], expected[:12])
        self.assertLess(len(queries), 20)
        self.assertTrue(any("LIMIT 12" in query["sql"] for query in queries))
        self.assertEqual([row.pk for row in self.client.get(self.url("inbox"), {"page": 2}).context["page_obj"]], expected[12:])
        Participant.objects.filter(user=self.buyer).update(archived_at=at)
        response = self.client.get(self.url("inbox"), {"archived": "1"})
        self.assertContains(response, "?archived=1&amp;page=2")

    def test_message_31_pagination_is_bounded_chronological_and_older_has_no_poll(self):
        conversation = self.start().conversation
        for index in range(30):
            self.send(conversation, body=f"Mesaj {index}")
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url("detail", conversation))
        self.private(response)
        self.assertEqual([row.sequence for row in response.context["history_messages"]], list(range(2, 32)))
        self.assertLess(len(queries), 25)
        self.assertTrue(any("LIMIT 30" in query["sql"] for query in queries))
        older = self.client.get(self.url("detail", conversation), {"page": "2"})
        self.assertEqual([row.sequence for row in older.context["history_messages"]], [1])
        self.assertNotContains(older, "every 15s")
        self.assertContains(response, "every 15s")

    def test_strict_page_validation_on_all_paginated_routes(self):
        conversation = self.start().conversation
        for name in ["inbox", "detail", "history"]:
            for value in ["0", "-1", "1.0", "1e2", "١", "0000000001", "1000000000", "999999999", ""]:
                self.private(self.client.get(self.url(name, conversation), {"page": value}), 404)

    def test_public_detail_contact_cta_and_owner_preference(self):
        detail = reverse("listings:detail", args=[self.listing.pk])
        self.assertContains(self.client.get(detail), "Mesaj gönder")
        self.client.force_login(self.seller)
        response = self.client.get(detail)
        self.assertContains(response, "Yeni görüşmeleri kapat")
        self.assertNotContains(response, ">Mesaj gönder<")
        self.client.logout()
        self.assertContains(self.client.get(detail), "Mesaj gönder")
