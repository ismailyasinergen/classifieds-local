from accounts.tests.mfa_support import authenticate_client
from copy import deepcopy
from html.parser import HTMLParser
from io import BytesIO
from secrets import token_urlsafe
from tempfile import TemporaryDirectory
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image
from listings.models import ListingRevision
from listings.tests.test_publication import PublicationFixtures


class UIContractsTests(PublicationFixtures, TestCase):
    def test_queue_paginates_database_with_count_and_limit(self):
        self.submit()
        authenticate_client(self.client, self.reviewer)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/inceleme/")
        self.assertContains(response, "Araba")
        statements = [item["sql"] for item in queries.captured_queries if "listings_listingrevision" in item["sql"]]
        self.assertTrue(any("COUNT(" in item for item in statements))
        self.assertTrue(any("LIMIT 1" in item or "LIMIT 12" in item for item in statements))

    def test_all_mutations_reject_missing_csrf(self):
        revision = self.draft()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        urls = ["/ilan-ver/", f"/taslaklar/{revision.pk}/duzenle/",
                f"/taslaklar/{revision.pk}/gonder/", f"/taslaklar/{revision.pk}/geri-cek/",
                f"/ilanlarim/{revision.listing_id}/duzenleme-baslat/",
                f"/taslaklar/{revision.pk}/fotograflar/ekle/",
                f"/taslaklar/{revision.pk}/fotograflar/1/kaldir/",
                f"/taslaklar/{revision.pk}/fotograflar/1/yeniden-dene/"]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(client.post(url, {}).status_code, 403)
        client.force_login(self.reviewer)
        self.assertEqual(client.post(f"/inceleme/{revision.pk}/", {}).status_code, 403)

    def test_withdrawn_stale_review_cannot_publish_and_current_replay_is_idempotent(self):
        revision = self.submit()
        authenticate_client(self.client, self.reviewer)
        url = f"/inceleme/{revision.pk}/"
        self.assertContains(self.client.get(url), "İnceleme kararı")
        self.call("withdraw_revision", actor=self.owner, revision_id=revision.pk)
        response = self.client.post(url, {"action": "approve", "reason": "Uygun"})
        self.assertEqual(response.status_code, 409)
        revision.listing.refresh_from_db()
        self.assertIsNone(revision.listing.public_revision_id)
        replacement = self.submit(self.edit(revision))
        url = f"/inceleme/{replacement.pk}/"
        for _ in range(2):
            self.assertEqual(self.client.post(url, {"action": "approve", "reason": "Uygun"}).status_code, 302)
        from moderation.models import ModerationDecision
        self.assertEqual(ModerationDecision.objects.filter(revision=replacement).count(), 1)

    def test_category_path_has_variable_depth_and_partial_schema_boolean(self):
        from catalog.models import Category, AttributeSchema
        parent = Category.objects.create(name="Üst", slug="upper")
        middle = Category.objects.create(name="Orta", slug="middle", parent=parent)
        category = Category.objects.create(name="Alt", slug="lower", parent=middle)
        AttributeSchema.objects.create(category=category, version=1, definition={"fields": {
            "available": {"type": "boolean", "required": True, "label": "Uygun mu?"}}})
        self.client.force_login(self.owner)
        self.assertContains(self.client.get("/ilan-ver/"), "Üst › Orta › Alt")
        self.client.post("/ilan-ver/", {"category": category.pk})
        revision = ListingRevision.objects.get(category=category)
        response = self.client.post(f"/taslaklar/{revision.pk}/duzenle/?step=details", {
            "edit_version": 1, "attr_available": "", "title": "", "description": "",
            "price": "", "currency": "", "location": ""})
        self.assertEqual(response.status_code, 302)
        revision.refresh_from_db()
        self.assertEqual(revision.attributes, {})

    def test_schema_options_reopen_selected_and_survive_another_field_change(self):
        from catalog.models import AttributeSchema

        class SelectOptions(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_choice = False
                self.values = []
                self.selected = []

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == "select":
                    self.in_choice = attributes.get("name") == "attr_choice"
                elif tag == "option" and self.in_choice:
                    value = attributes.get("value", "")
                    self.values.append(value)
                    if "selected" in attributes:
                        self.selected.append(value)

            def handle_endtag(self, tag):
                if tag == "select":
                    self.in_choice = False

        cases = [
            ("decimal_string", "decimal", ["1.00", "2.00"], "1.00", "1", "1"),
            ("decimal_float", "decimal", [1.0, 2.0], 1.0, "1", "1"),
            ("integer_zero_spelling", "integer", ["0.0", "1.0"], "0.0", 0, "0"),
            ("integer_nonzero_spelling", "integer", ["0.0", "1.0"], "1.0", 1, "1"),
            ("trimmed_string", "string", [" ready ", " done "], " ready ", "ready", "ready"),
            ("canonical_decimal_zero", "decimal", ["0", "1"], "0", "0", "0"),
            ("canonical_integer_zero", "integer", [0, 1], 0, 0, "0"),
            ("boolean_false", "boolean", [False, True], False, False, "false"),
        ]
        self.client.force_login(self.owner)
        for version, (case, kind, options, value, canonical, encoded) in enumerate(cases, start=2):
            with self.subTest(case=case):
                definition = {"fields": {"choice": {"type": kind, "options": options, "label": "Seçim"}}}
                original_definition = deepcopy(definition)
                schema = AttributeSchema.objects.create(category=self.category, version=version, definition=definition)
                revision = self.draft(content={"title": "İlk başlık", "attributes": {"choice": value}})
                self.assertEqual(revision.attribute_schema_id, schema.pk)
                self.assertEqual(revision.attributes, {"choice": canonical})
                url = f"/taslaklar/{revision.pk}/duzenle/?step=details"
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                rendered = SelectOptions()
                rendered.feed(response.content.decode())
                with self.subTest(phase="selected_on_reopen"):
                    self.assertEqual(rendered.selected, [encoded])
                # A single-select browser falls back to its first option when none matches.
                submitted = rendered.selected[0] if rendered.selected else rendered.values[0]
                response = self.client.post(url, {
                    "edit_version": revision.edit_version, "title": "Değişen başlık", "attr_choice": submitted})
                self.assertEqual(response.status_code, 302)
                revision.refresh_from_db()
                with self.subTest(phase="retained_after_post"):
                    self.assertEqual(revision.attributes, {"choice": canonical})
                self.assertEqual(revision.title, "Değişen başlık")
                self.assertEqual(revision.edit_version, 2)
                schema.refresh_from_db()
                self.assertEqual(schema.definition, original_definition)
                self.assertEqual(revision.attribute_schema_id, schema.pk)
                self.assertEqual(revision.schema_version, version)

    def test_anonymous_category_filter_handles_invalid_and_bounded_ids(self):
        public = self.publish()
        self.client.raise_request_exception = False
        for value in ("²", "not-a-category", "9" * 5000, "9223372036854775808", "0", "-1"):
            with self.subTest(category=value[:40]):
                response = self.client.get("/", {"category": value})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, public.title)
                self.assertEqual(response.context["selected_category"], "")
        response = self.client.get("/", {"category": str(self.category.pk)})
        self.assertContains(response, public.title)
        self.assertEqual(response.context["selected_category"], str(self.category.pk))
        response = self.client.get("/", {"category": "9223372036854775807"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, public.title)

    def test_preview_describes_private_route_for_public_and_pending_revisions(self):
        public = self.publish()
        draft = self.edit(public, title="Bekleyen düzenleme")
        self.client.force_login(self.owner)
        for revision in (public, draft):
            response = self.client.get(f"/taslaklar/{revision.pk}/onizleme/")
            self.assertContains(response, "Bu özel önizleme sayfasını yalnız ilan sahibi ve yetkili inceleyici görebilir.")
            self.assertNotContains(response, "Bu sürüm herkese açık değildir.")
            self.assertEqual(response["Cache-Control"], "private, no-store")
            if revision.status == "draft":
                self.assertContains(response, "Göndermeden önce son bir kez gözden geçir.")
            else:
                self.assertNotContains(response, "Göndermeden önce son bir kez gözden geçir.")
        self.submit(draft)
        response = self.client.get(f"/taslaklar/{draft.pk}/onizleme/")
        self.assertNotContains(response, "Göndermeden önce son bir kez gözden geçir.")
        self.client.logout()
        self.assertContains(self.client.get(f"/ilanlar/{public.listing_id}/"), public.title)
        self.assertNotContains(self.client.get(f"/ilanlar/{public.listing_id}/"), draft.title)

    def test_details_explain_category_fields_without_schema_version_jargon(self):
        revision = self.draft()
        self.client.force_login(self.owner)
        response = self.client.get(f"/taslaklar/{revision.pk}/duzenle/?step=details")
        self.assertContains(response, "Seçtiğin kategoriye uygun özellikleri aşağıdaki alanlarda belirt.")
        self.assertNotContains(response, "Özellik şeması")
        self.assertEqual(response.context["revision"].schema_version, revision.schema_version)
        self.assertEqual(response.context["revision"].attribute_schema_id, revision.attribute_schema_id)

    def test_public_text_is_escaped(self):
        public = self.publish()
        ListingRevision.objects.filter(pk=public.pk).update(title="<script>alert(1)</script>")
        response = self.client.get(f"/ilanlar/{public.listing_id}/")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_allauth_signup_requires_real_confirmation_and_reset_email(self):
        import re
        email = "ui-" + token_urlsafe(8).lower() + "@example.test"
        password = token_urlsafe(24)
        response = self.client.post(reverse("account_signup"), {
            "email": email, "password1": password, "password2": password})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        url = re.search(r"http[^\s]+/accounts/confirm-email/[^\s]+", mail.outbox[0].body).group(0)
        response = self.client.get(url)
        self.assertContains(response, "Classifieds Local")
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.post(reverse("account_login"), {"login": email, "password": password})
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("account_logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("account_reset_password"), {"email": email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("/accounts/password/reset/key/", mail.outbox[-1].body)


class UploadBoundaryTests(PublicationFixtures, TransactionTestCase):
    def test_real_upload_commits_link_original_and_worker_ready(self):
        with TemporaryDirectory() as directory, override_settings(
                PRIVATE_MEDIA_ROOT=directory, CELERY_TASK_ALWAYS_EAGER=True):
            revision = self.draft(content={})
            self.client.force_login(self.owner)
            stream = BytesIO()
            Image.new("RGB", (8, 8), (30, 130, 90)).save(stream, "PNG")
            response = self.client.post(f"/taslaklar/{revision.pk}/fotograflar/ekle/", {
                "image": SimpleUploadedFile("photo.png", stream.getvalue(), content_type="image/png")})
            self.assertEqual(response.status_code, 302)
            asset = revision.images.get().asset
            self.assertTrue(asset.original.storage.exists(asset.original.name))
            self.assertEqual(asset.state, "ready")
            self.assertTrue(asset.derivative.storage.exists(asset.derivative.name))
            response = self.client.get(reverse("media:derivative", args=[asset.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response["Content-Disposition"].startswith("inline"))
            self.assertTrue(b"".join(response.streaming_content).startswith(b"\xff\xd8"))
