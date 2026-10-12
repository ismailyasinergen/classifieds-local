from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from listings.models import Listing, ListingRevision
from listings.publication import submit_revision, withdraw_revision
from listings.services import start_revision, update_draft
from .test_drafts import DraftFixtures


@override_settings(PILOT_NEW_LISTINGS_PER_DAY=1)
class CreationLimitTests(DraftFixtures, TestCase):
    def test_category_only_new_identity_consumes_budget(self):
        self.draft(content={})
        with self.assertRaises(ValidationError) as caught:
            self.draft(content={})
        self.assertEqual(caught.exception.action, "new_listing")
        self.assertGreaterEqual(caught.exception.retry_after, 1)
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(ListingRevision.objects.count(), 1)

    def test_every_lifecycle_counts(self):
        for lifecycle in Listing.Lifecycle.values:
            with self.subTest(lifecycle=lifecycle):
                listing = Listing.objects.create(owner=self.owner, lifecycle=lifecycle)
                with self.assertRaises(ValidationError) as caught:
                    self.draft()
                self.assertEqual(caught.exception.action, "new_listing")
                listing.delete()

    def test_other_actor_capacity_is_independent(self):
        self.draft()
        self.draft(actor=self.other)
        self.assertEqual(Listing.objects.count(), 2)

    def test_invalid_creation_first_revision_failure_and_rollback_consume_none(self):
        with self.assertRaises(ValidationError):
            self.draft(content={"price": "bad"})
        with patch.object(ListingRevision, "full_clean", side_effect=ValidationError("revision failed")):
            with self.assertRaises(ValidationError):
                self.draft()
        with patch.object(ListingRevision, "save", side_effect=ValidationError("save failed")):
            with self.assertRaises(ValidationError):
                self.draft()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.draft()
                raise RuntimeError("rollback")
        self.assertEqual(Listing.objects.count(), 0)
        self.draft()

    def test_exhaustion_keeps_edit_submit_withdraw_and_replacement_revision_working(self):
        revision = self.draft()
        revision = update_draft(actor=self.owner, revision_id=revision.pk,
                                expected_version=1, content={"title": "Updated"})
        self.assertEqual(start_revision(actor=self.owner, listing_id=revision.listing_id).pk, revision.pk)
        submit_revision(actor=self.owner, revision_id=revision.pk)
        withdraw_revision(actor=self.owner, revision_id=revision.pk)
        replacement = start_revision(actor=self.owner, listing_id=revision.listing_id)
        self.assertNotEqual(replacement.pk, revision.pk)
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(ListingRevision.objects.count(), 2)

    def test_creation_cutoff_expires_exactly_and_counts_one_microsecond_inside(self):
        at = timezone.now()
        old = self.draft()
        cutoff = at - timedelta(days=1)
        Listing.objects.filter(pk=old.listing_id).update(created_at=cutoff)
        with patch("listings.services.timezone.now", return_value=at):
            second = self.draft(content={})
        Listing.objects.filter(pk=second.listing_id).update(
            created_at=cutoff + timedelta(microseconds=1))
        with patch("listings.services.timezone.now", return_value=at):
            with self.assertRaises(ValidationError) as caught:
                self.draft()
        self.assertEqual(caught.exception.action, "new_listing")
        self.assertEqual(caught.exception.retry_after, 1)
        self.assertEqual(Listing.objects.count(), 2)

    def test_prevalidation_remains_authoritative_at_exhaustion(self):
        self.draft()
        with self.assertRaises(ValidationError) as caught:
            self.draft(content={"price": "bad"})
        self.assertIn("price", caught.exception.message_dict)
        self.assertEqual(Listing.objects.count(), 1)

    def test_current_locked_actor_is_rechecked(self):
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.draft()
        self.assertEqual(Listing.objects.count(), 0)
