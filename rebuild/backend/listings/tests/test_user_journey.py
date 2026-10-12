from accounts.tests.mfa_support import authenticate_client
from django.test import Client, TestCase
from listings.models import ListingRevision
from listings.tests.test_publication import PublicationFixtures
from media.models import MediaAsset, RevisionImage
from django.core.exceptions import PermissionDenied, ValidationError
from listings.services import InvalidRevisionState


class UserJourneyTests(PublicationFixtures, TestCase):
    def details(self, revision, **overrides):
        data = {"edit_version": revision.edit_version, "title": "Ekrandan ilan",
                "description": "Gerçek açıklama", "price": "250.00", "currency": "TRY",
                "location": "İstanbul", "attr_model_year": "2022", "attr_area": "80.5",
                "attr_electric": "false", "attr_brand": ""}
        data.update(overrides)
        return self.client.post(f"/taslaklar/{revision.pk}/duzenle/?step=details", data)

    def test_seller_submits_reviewer_publishes_visitor_sees_only_approved_content(self):
        self.client.force_login(self.owner)
        response = self.client.post("/ilan-ver/", {"category": self.category.pk})
        self.assertEqual(response.status_code, 302)
        revision = ListingRevision.objects.get()
        self.assertEqual(revision.title, "")
        self.assertContains(self.client.get(response.url), "Fotoğraflar")
        self.assertEqual(self.details(revision).status_code, 302)
        self.assertEqual(self.client.post(f"/taslaklar/{revision.pk}/gonder/").status_code, 302)
        authenticate_client(self.client, self.reviewer)
        self.assertContains(self.client.get("/inceleme/"), "Ekrandan ilan")
        response = self.client.post(f"/inceleme/{revision.pk}/", {
            "action": "approve", "reason": "Uygun", "expected_public_revision_id": ""})
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        self.assertContains(self.client.get(f"/ilanlar/{revision.listing_id}/"), "Ekrandan ilan")
        self.client.force_login(self.owner)
        response = self.client.post(f"/ilanlarim/{revision.listing_id}/duzenleme-baslat/")
        self.assertEqual(response.status_code, 302)
        draft = ListingRevision.objects.get(status="draft")
        self.assertEqual(self.details(draft, title="Yeni gizli başlık").status_code, 302)
        self.assertEqual(self.client.post(f"/taslaklar/{draft.pk}/gonder/").status_code, 302)
        dashboard = self.client.get("/ilanlarim/")
        self.assertContains(dashboard, "İlan yayında")
        self.assertContains(dashboard, "Düzenlemen incelemede")
        response = self.client.get(f"/ilanlar/{revision.listing_id}/")
        self.assertContains(response, "Ekrandan ilan")
        self.assertNotContains(response, "Yeni gizli başlık")

    def test_partial_save_invalid_values_and_stale_edit(self):
        revision = self.draft(content={})
        self.client.force_login(self.owner)
        self.assertEqual(self.details(revision, price="", attr_model_year="", attr_area="").status_code, 302)
        revision.refresh_from_db()
        self.assertIsNone(revision.price)
        self.assertEqual(revision.attributes, {"electric": False})
        response = self.details(revision, price="-1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertEqual(self.details(revision).status_code, 302)
        response = self.details(revision, title="Eski ekran")
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "Taslak değişti", status_code=409)
        self.assertContains(response, f'value="{revision.edit_version}"', status_code=409)
        revision.refresh_from_db()
        self.assertEqual(revision.title, "Ekrandan ilan")

    def test_schema_validation_errors_bind_to_actual_field_without_saving(self):
        revision = self.draft()
        self.client.force_login(self.owner)
        for invalid in ("1800", "not-a-year"):
            response = self.details(revision, attr_model_year=invalid)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "id_attr_model_year_error")
            revision.refresh_from_db()
            self.assertEqual(revision.edit_version, 1)
            self.assertEqual(revision.attributes["model_year"], 2020)

    def test_owner_tampering_and_get_mutations_blocked(self):
        revision = self.draft()
        authenticate_client(self.client, self.reviewer)
        self.assertEqual(self.details(revision).status_code, 403)
        self.assertEqual(self.client.post(f"/taslaklar/{revision.pk}/gonder/").status_code, 403)
        self.client.force_login(self.owner)
        for url in (f"/taslaklar/{revision.pk}/gonder/",
                    f"/taslaklar/{revision.pk}/geri-cek/",
                    f"/ilanlarim/{revision.listing_id}/duzenleme-baslat/"):
            self.assertEqual(self.client.get(url).status_code, 405)

    def test_csrf_required_and_valid_token_creates_draft(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post("/ilan-ver/", {"category": self.category.pk}).status_code, 403)
        response = client.get("/ilan-ver/")
        self.assertEqual(response.status_code, 200)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post("/ilan-ver/", {
            "category": self.category.pk, "csrfmiddlewaretoken": token}).status_code, 302)

    def test_review_reason_permission_and_stale_pointer(self):
        public = self.publish()
        revision = self.submit(self.edit(public, title="Düzenleme"))
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get("/inceleme/").status_code, 403)
        authenticate_client(self.client, self.reviewer)
        url = f"/inceleme/{revision.pk}/"
        self.assertEqual(self.client.post(url, {"action": "reject", "reason": ""}).status_code, 200)
        response = self.client.post(url, {"action": "approve", "reason": "Uygun",
                                         "expected_public_revision_id": ""})
        self.assertEqual(response.status_code, 409)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "submitted")
        self.assertEqual(self.client.post(url, {"action": "reject", "reason": "Başlık açık değil"}).status_code, 302)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get("/ilanlarim/"), "Başlık açık değil")

    def test_photo_fragment_access_upload_form_and_csrf(self):
        revision = self.draft(content={})
        self.client.force_login(self.owner)
        response = self.client.post(f"/taslaklar/{revision.pk}/fotograflar/ekle/", {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertEqual(MediaAsset.objects.count(), 0)
        self.assertContains(self.client.get(f"/taslaklar/{revision.pk}/fotograflar/durum/"), "Fotoğraf yok")
        self.client.logout()
        self.assertIn(self.client.get(f"/taslaklar/{revision.pk}/fotograflar/durum/").status_code, (302, 403))

    def test_draft_unlink_preserves_shared_asset_and_frozen_links(self):
        from media.services import remove_image
        public = self.publish()
        asset = MediaAsset.objects.create(owner=self.owner, source_mime="image/jpeg", source_bytes=1,
                                           width=1, height=1, state="ready", derivative="private.jpg")
        RevisionImage.objects.create(revision=public, asset=asset, position=0)
        draft = self.edit(public)
        remove_image(actor=self.owner, revision_id=draft.pk, asset_id=asset.pk)
        self.assertFalse(draft.images.exists())
        self.assertTrue(public.images.filter(asset=asset).exists())
        self.assertTrue(MediaAsset.objects.filter(pk=asset.pk, derivative="private.jpg").exists())
        with self.assertRaises(InvalidRevisionState):
            remove_image(actor=self.owner, revision_id=public.pk, asset_id=asset.pk)
        with self.assertRaises(PermissionDenied):
            remove_image(actor=self.reviewer, revision_id=draft.pk, asset_id=asset.pk)
        with self.assertRaises(ValidationError):
            remove_image(actor=self.owner, revision_id=draft.pk, asset_id=asset.pk)
