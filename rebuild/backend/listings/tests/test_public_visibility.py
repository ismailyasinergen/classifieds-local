from accounts.tests.mfa_support import authenticate_client
from datetime import timedelta
from tempfile import TemporaryDirectory
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone
from listings.models import Listing
from listings.tests.test_publication import PublicationFixtures
from moderation.models import Restriction
from media.models import MediaAsset, RevisionImage


class PublicVisibilityTests(PublicationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def detail(self, revision):
        return f"/ilanlar/{revision.listing_id}/"

    def photo(self, revision, asset):
        return f"/ilanlar/{revision.listing_id}/fotograflar/{revision.pk}/{asset.pk}/"

    def asset(self, revision):
        asset = MediaAsset(owner=self.owner, source_mime="image/jpeg", source_bytes=3,
                           width=1, height=1, state="ready")
        asset.original.save("ignored", ContentFile(b"original"), save=False)
        asset.derivative.save("ignored", ContentFile(b"jpg"), save=False)
        asset.save()
        RevisionImage.objects.create(revision=revision, asset=asset, position=0)
        return asset

    def test_visibility_for_no_expiry_future_expiry_and_exact_expiry(self):
        from listings.queries import public_listings
        public = self.publish()
        at = timezone.now()
        self.assertTrue(public_listings(at=at).filter(pk=public.listing_id).exists())
        for delta, expected in ((1, True), (0, False), (-1, False)):
            Listing.objects.filter(pk=public.listing_id).update(expires_at=at + timedelta(seconds=delta))
            self.assertEqual(public_listings(at=at).filter(pk=public.listing_id).exists(), expected)

    def test_paused_closed_and_restricted_listings_are_hidden(self):
        public = self.publish()
        self.assertEqual(self.client.get(self.detail(public)).status_code, 200)
        for lifecycle in ("paused", "closed"):
            Listing.objects.filter(pk=public.listing_id).update(lifecycle=lifecycle)
            self.assertEqual(self.client.get(self.detail(public)).status_code, 404)
        Listing.objects.filter(pk=public.listing_id).update(lifecycle="live")
        for target in ({"listing": public.listing}, {"seller": self.owner}):
            restriction = Restriction.objects.create(actor=self.reviewer, reason="Gizle", **target)
            self.assertEqual(self.client.get(self.detail(public)).status_code, 404)
            restriction.revoked_at = timezone.now() + timedelta(days=1)
            restriction.save()
            self.assertEqual(self.client.get(self.detail(public)).status_code, 200)

    def test_public_detail_never_leaks_draft(self):
        public = self.publish()
        self.edit(public, title="Gizli taslak")
        self.client.force_login(self.owner)
        response = self.client.get(self.detail(public))
        self.assertContains(response, "Araba")
        self.assertNotContains(response, "Gizli taslak")
        self.assertNotContains(response, self.owner.email)

    def test_private_preview_requires_owner_or_reviewer(self):
        revision = self.draft()
        url = f"/taslaklar/{revision.pk}/onizleme/"
        self.assertIn(self.client.get(url).status_code, (302, 403))
        for user in (self.owner, self.reviewer):
            if user.pk == self.reviewer.pk:
                authenticate_client(self.client, user)
            else:
                self.client.force_login(user)
            response = self.client.get(url)
            self.assertContains(response, "Özel önizleme")
            self.assertEqual(response.content.count(b"<h1"), 1)
            self.assertEqual(response["Cache-Control"], "private, no-store")
        from accounts.models import User
        outsider = User.objects.create_user("outsider@example.test", "password")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_draft_photo_is_absent_from_public_revision(self):
        public = self.publish()
        draft = self.edit(public, title="Gizli")
        asset = self.asset(draft)
        self.assertEqual(self.client.get(self.photo(draft, asset)).status_code, 404)
        self.assertNotContains(self.client.get(self.detail(public)), self.photo(draft, asset))

    def test_public_photo_visibility_and_exact_relation(self):
        revision = self.draft()
        asset = self.asset(revision)
        self.submit(revision)
        public = self.approve(revision)
        response = self.client.get(self.photo(public, asset))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertTrue(response["Content-Disposition"].startswith("inline"))
        self.assertEqual(b"".join(response.streaming_content), b"jpg")
        draft = self.edit(public)
        for state in ("submitted", "rejected", "withdrawn"):
            Listing.objects.filter(pk=public.listing_id).update(lifecycle="live")
            from listings.models import ListingRevision
            ListingRevision.objects.filter(pk=draft.pk).update(status=state)
            self.assertEqual(self.client.get(self.photo(draft, asset)).status_code, 404)
        Listing.objects.filter(pk=public.listing_id).update(expires_at=timezone.now())
        self.assertEqual(self.client.get(self.photo(public, asset)).status_code, 404)
        Listing.objects.filter(pk=public.listing_id).update(expires_at=None)
        Restriction.objects.create(actor=self.reviewer, seller=self.owner, reason="Gizle")
        self.assertEqual(self.client.get(self.photo(public, asset)).status_code, 404)

    def test_other_listing_pointer_and_superseded_photo_are_hidden(self):
        public = self.publish()
        other = self.publish()
        Listing.objects.filter(pk=other.listing_id).update(public_revision=public)
        self.assertEqual(self.client.get(self.detail(other)).status_code, 404)
        draft = self.edit(public)
        asset = self.asset(draft)
        newer = self.approve(self.submit(draft), expected=public.pk)
        self.assertEqual(self.client.get(self.photo(public, asset)).status_code, 404)
        response = self.client.get(self.photo(newer, asset))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"jpg")
