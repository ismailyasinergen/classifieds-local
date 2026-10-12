from accounts.tests.mfa_support import authenticate_client
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from listings.models import ListingRevision
from listings.services import InvalidRevisionState, start_revision
from .helpers import MediaFixtures


class MediaAccessTests(MediaFixtures, TestCase):
    def test_foreign_asset_cannot_be_attached(self):
        asset = self.attach()
        foreign = self.draft(actor=self.other)
        with self.assertRaises(PermissionDenied):
            self.module("services").link_image(
                actor=self.other, revision_id=foreign.pk, asset_id=asset.pk, position=0)
        self.assertEqual(foreign.images.count(), 0)

    def test_private_original_requires_authorization(self):
        asset = self.attach()
        url = reverse("media:original", args=[asset.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertNotIn(asset.original.name, response["Content-Disposition"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"\xff\xd8"))

    def test_staff_alone_has_no_original_access(self):
        asset = self.attach()
        self.other.is_staff = True
        self.other.save(update_fields=["is_staff"])
        authenticate_client(self.client, self.other)
        self.assertEqual(self.client.get(reverse("media:original", args=[asset.pk])).status_code, 403)

    def test_explicit_reviewer_can_preview(self):
        asset = self.attach()
        self.other.user_permissions.add(Permission.objects.get(
            content_type__app_label="listings", codename="review_listingrevision"))
        authenticate_client(self.client, self.other)
        response = self.client.get(reverse("media:original", args=[asset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content))

    def test_inactive_owner_cannot_preview_or_attach(self):
        asset = self.attach()
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("media:original", args=[asset.pk])).status_code, 403)
        with self.assertRaises(PermissionDenied):
            self.attach()

    def test_frozen_revision_cannot_change_links(self):
        asset = self.attach()
        for status in ("submitted", "approved", "rejected", "withdrawn"):
            ListingRevision.objects.filter(pk=self.revision.pk).update(status=status)
            with self.subTest(status=status):
                with self.assertRaises(InvalidRevisionState):
                    self.module("services").link_image(
                        actor=self.owner, revision_id=self.revision.pk, asset_id=asset.pk, position=1)
                with self.assertRaises(InvalidRevisionState):
                    self.attach()
        self.assertEqual(self.revision.images.count(), 1)

    def test_derivative_is_also_private(self):
        asset = self.attach()
        self.module("tasks").process_image(asset.pk)
        url = reverse("media:derivative", args=[asset.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertTrue(b"".join(response.streaming_content))

    def test_status_shows_failure_without_storage_paths(self):
        asset = self.attach()
        asset.original.storage.delete(asset.original.name)
        self.module("tasks").process_image(asset.pk)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("media:status", args=[asset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "failed")
        self.assertEqual(response.json()["error"], "processing_failed")
        self.assertNotIn(self.directory.name, response.content.decode())
        self.assertNotIn(asset.original.name, response.content.decode())

    def test_start_revision_copies_only_ready_from_latest_terminal(self):
        older_asset = self.attach()
        self.module("tasks").process_image(older_asset.pk)
        ListingRevision.objects.filter(pk=self.revision.pk).update(status="approved")
        listing = self.revision.listing
        listing.public_revision = self.revision
        listing.save(update_fields=["public_revision"])
        latest = start_revision(actor=self.owner, listing_id=listing.pk)
        new_asset = self.attach(latest)
        pending = self.attach(latest)
        self.module("tasks").process_image(new_asset.pk)
        ListingRevision.objects.filter(pk=latest.pk).update(status="withdrawn")
        copied = start_revision(actor=self.owner, listing_id=listing.pk)
        self.assertEqual(list(copied.images.values_list("asset_id", flat=True)),
                         [older_asset.pk, new_asset.pk])
        self.assertNotIn(pending.pk, copied.images.values_list("asset_id", flat=True))
        self.assertEqual(latest.images.count(), 3)
        listing.refresh_from_db()
        self.assertEqual(listing.public_revision_id, self.revision.pk)
