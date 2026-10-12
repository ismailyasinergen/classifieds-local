"""Publication services exercise real PostgreSQL records and permission checks."""
from decimal import Decimal
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from listings.models import Listing, ListingRevision
from listings.services import InvalidRevisionState, start_revision, update_draft
from listings.tests.test_drafts import DraftFixtures


class PublicationFixtures(DraftFixtures):
    def setUp(self):
        super().setUp()
        self.other.user_permissions.add(Permission.objects.get(
            content_type__app_label="listings", codename="review_listingrevision"))
        self.reviewer = self.other

    def call(self, name, **kwargs):
        module_name = "listings.publication" if name in ("submit_revision", "withdraw_revision") else "moderation.services"
        from importlib import import_module
        return getattr(import_module(module_name), name)(**kwargs)

    def submit(self, revision=None):
        return self.call("submit_revision", actor=self.owner, revision_id=(revision or self.draft()).pk)

    def approve(self, revision, expected=None, actor=None):
        return self.call("approve_revision", actor=actor or self.reviewer,
                         revision_id=revision.pk, expected_public_revision_id=expected, reason="Uygun")

    def publish(self):
        return self.approve(self.submit())

    def edit(self, public, **content):
        revision = start_revision(actor=self.owner, listing_id=public.listing_id)
        return update_draft(actor=self.owner, revision_id=revision.pk,
                            expected_version=revision.edit_version, content=content)


class PublicationTests(PublicationFixtures, TestCase):
    def test_submit_freezes_real_draft(self):
        revision = self.submit()
        self.assertEqual(revision.status, "submitted")
        revision.refresh_from_db()
        self.assertEqual(revision.status, "submitted")

    def test_submitted_content_is_immutable(self):
        revision = self.submit()
        with self.assertRaises(InvalidRevisionState):
            update_draft(actor=self.owner, revision_id=revision.pk, expected_version=1, content={"title": "Changed"})
        revision.refresh_from_db()
        self.assertEqual(revision.title, "Araba")

    def test_first_approval_publishes_revision(self):
        revision = self.publish()
        revision.listing.refresh_from_db()
        self.assertEqual(revision.status, "approved")
        self.assertEqual(revision.listing.public_revision_id, revision.pk)
        self.assertEqual(revision.listing.lifecycle, "live")
        self.assertIsNotNone(revision.listing.first_published_at)

    def test_pending_edit_keeps_old_public_content(self):
        public = self.publish()
        edited = self.edit(public, title="Yeni", price="900")
        self.submit(edited)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.public_revision_id, public.pk)
        self.assertEqual(public.listing.public_revision.title, "Araba")

    def test_rejection_keeps_old_public_content(self):
        public = self.publish()
        revision = self.submit(self.edit(public, title="Yeni"))
        self.call("reject_revision", actor=self.reviewer, revision_id=revision.pk, reason="Uygun değil")
        revision.refresh_from_db()
        public.listing.refresh_from_db()
        self.assertEqual(revision.status, "rejected")
        self.assertEqual(public.listing.public_revision_id, public.pk)

    def test_withdrawn_revision_cannot_be_approved(self):
        revision = self.submit()
        self.call("withdraw_revision", actor=self.owner, revision_id=revision.pk)
        with self.assertRaises(InvalidRevisionState):
            self.approve(revision)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "withdrawn")
        replacement = start_revision(actor=self.owner, listing_id=revision.listing_id)
        self.assertEqual(replacement.title, revision.title)

    def test_staff_without_review_permission_cannot_approve(self):
        self.owner.is_staff = True
        self.owner.save()
        revision = self.submit()
        with self.assertRaises(PermissionDenied):
            self.approve(revision, actor=self.owner)

    def test_nonstaff_with_explicit_permission_can_approve(self):
        self.assertFalse(self.reviewer.is_staff)
        self.assertEqual(self.publish().status, "approved")

    def test_other_owner_and_inactive_reviewer_are_denied(self):
        revision = self.draft()
        with self.assertRaises(PermissionDenied):
            self.call("submit_revision", actor=self.other, revision_id=revision.pk)
        revision = self.submit(revision)
        with self.assertRaises(PermissionDenied):
            self.call("withdraw_revision", actor=self.other, revision_id=revision.pk)
        self.reviewer.is_active = False
        self.reviewer.save()
        with self.assertRaises(PermissionDenied):
            self.approve(revision)

    def test_reject_requires_permission_and_records_reason(self):
        from moderation.models import ModerationDecision
        revision = self.submit()
        with self.assertRaises(PermissionDenied):
            self.call("reject_revision", actor=self.owner, revision_id=revision.pk, reason="No")
        self.call("reject_revision", actor=self.reviewer, revision_id=revision.pk, reason="  Eksik  ")
        decision = ModerationDecision.objects.get()
        self.assertEqual((decision.actor_id, decision.revision_id, decision.outcome, decision.reason),
                         (self.reviewer.pk, revision.pk, "rejected", "Eksik"))
        with self.assertRaises(InvalidRevisionState):
            self.call("reject_revision", actor=self.reviewer, revision_id=revision.pk, reason="Again")

    def test_new_approval_rejects_invalid_reason_and_expected_pointer(self):
        revision = self.submit()
        for reason in ("", "  ", None, "a" * 2001):
            with self.subTest(reason_type=type(reason).__name__), self.assertRaises(ValidationError):
                self.call("approve_revision", actor=self.reviewer, revision_id=revision.pk,
                          expected_public_revision_id=None, reason=reason)
        for expected in (True, 1.0, "1", -1, 0):
            with self.subTest(expected=expected), self.assertRaises(ValidationError):
                self.approve(revision, expected=expected)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "submitted")

    def test_draft_cannot_be_reviewed_or_withdrawn(self):
        revision = self.draft()
        for name in ("approve_revision", "reject_revision", "withdraw_revision"):
            kwargs = {"actor": self.owner if name == "withdraw_revision" else self.reviewer, "revision_id": revision.pk}
            if name != "withdraw_revision":
                kwargs["reason"] = "Test"
            if name == "approve_revision":
                kwargs["expected_public_revision_id"] = None
            with self.subTest(name=name), self.assertRaises(InvalidRevisionState):
                self.call(name, **kwargs)

    def test_review_permission_revocation_is_rechecked(self):
        self.reviewer.has_perm("listings.review_listingrevision")
        self.reviewer.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            self.approve(self.submit())

    def test_submit_requires_complete_canonical_content(self):
        for content in ({}, {"title": "Only"}, {"price": None}, {"attributes": {}}):
            with self.subTest(content=content):
                revision = self.draft(content=content)
                with self.assertRaises(ValidationError):
                    self.submit(revision)
                revision.refresh_from_db()
                self.assertEqual(revision.status, "draft")

    def test_publish_revalidates_full_schema_and_canonical_content(self):
        revision = self.submit()
        ListingRevision.objects.filter(pk=revision.pk).update(attributes={})
        with self.assertRaises(ValidationError):
            self.approve(revision)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "submitted")
        ListingRevision.objects.filter(pk=revision.pk).update(attributes={"model_year": 2020, "area": "82.5"}, title="  raw  ")
        with self.assertRaises(ValidationError):
            self.approve(revision)

    def test_repeated_approval_creates_one_event(self):
        from events.models import OutboxEvent
        from moderation.models import ModerationDecision, PriceChange
        revision = self.publish()
        self.approve(revision, expected=None)
        self.assertEqual(OutboxEvent.objects.count(), 1)
        self.assertEqual(ModerationDecision.objects.count(), 1)
        self.assertEqual(PriceChange.objects.count(), 0)

    def test_old_approval_replay_cannot_replace_new_public_revision(self):
        public = self.publish()
        newer = self.approve(self.submit(self.edit(public, title="Yeni")), expected=public.pk)
        with self.assertRaises(InvalidRevisionState):
            self.approve(public)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.public_revision_id, newer.pk)

    def test_stale_expected_pointer_is_conflict(self):
        from listings.publication import StalePublicRevision
        public = self.publish()
        revision = self.submit(self.edit(public, title="Yeni"))
        with self.assertRaises(StalePublicRevision):
            self.approve(revision, expected=None)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "submitted")

    def test_price_history_only_changes_on_publication(self):
        from moderation.models import PriceChange
        from events.models import OutboxEvent
        public = self.publish()
        timestamp = public.listing.first_published_at
        revision = self.edit(public, price="900")
        self.assertEqual(PriceChange.objects.count(), 0)
        self.submit(revision)
        self.assertEqual(PriceChange.objects.count(), 0)
        self.approve(revision, expected=public.pk)
        change = PriceChange.objects.get()
        self.assertEqual((change.old_amount, change.new_amount), (Decimal("1234.50"), Decimal("900")))
        self.assertTrue(change.is_price_drop)
        self.assertEqual(OutboxEvent.objects.count(), 3)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.first_published_at, timestamp)

    def test_failed_publication_rolls_back_pointer_history_and_event(self):
        from events.models import OutboxEvent
        from moderation.models import ModerationDecision, PriceChange
        public = self.publish()
        revision = self.submit(self.edit(public, price="900"))
        timestamp = public.listing.first_published_at
        with connection.cursor() as cursor:
            cursor.execute("""CREATE FUNCTION task4_fail_outbox() RETURNS trigger LANGUAGE plpgsql AS
                $$ BEGIN IF NEW.event_type = 'listing.price_changed' THEN
                RAISE EXCEPTION 'intentional test outbox persistence failure'; END IF; RETURN NEW; END $$""")
            cursor.execute("""CREATE TRIGGER task4_fail_outbox BEFORE INSERT ON events_outboxevent
                FOR EACH ROW EXECUTE FUNCTION task4_fail_outbox()""")
        from django.db import DatabaseError
        with self.assertRaises(DatabaseError):
            self.approve(revision, expected=public.pk)
        revision.refresh_from_db()
        public.listing.refresh_from_db()
        self.assertEqual(revision.status, "submitted")
        self.assertEqual(public.listing.public_revision_id, public.pk)
        self.assertEqual(public.listing.first_published_at, timestamp)
        self.assertEqual(ModerationDecision.objects.count(), 1)
        self.assertEqual(PriceChange.objects.count(), 0)
        self.assertEqual(OutboxEvent.objects.count(), 1)
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER task4_fail_outbox ON events_outboxevent")
            cursor.execute("DROP FUNCTION task4_fail_outbox()")

    def test_same_price_edit_does_not_create_price_event(self):
        from moderation.models import PriceChange
        from events.models import OutboxEvent
        public = self.publish()
        self.approve(self.submit(self.edit(public, title="Yeni")), expected=public.pk)
        self.assertEqual(PriceChange.objects.count(), 0)
        self.assertEqual(OutboxEvent.objects.filter(event_type="listing.price_changed").count(), 0)

    def test_currency_change_is_not_price_drop(self):
        from moderation.models import PriceChange
        public = self.publish()
        self.approve(self.submit(self.edit(public, price="1", currency="USD")), expected=public.pk)
        change = PriceChange.objects.get()
        self.assertFalse(change.is_price_drop)
        self.assertEqual((change.old_currency, change.new_currency), ("EUR", "USD"))

    def test_paused_listing_stays_paused_and_replay_keeps_lifecycle(self):
        public = self.publish()
        Listing.objects.filter(pk=public.listing_id).update(lifecycle="paused")
        newer = self.approve(self.submit(self.edit(public, title="Yeni")), expected=public.pk)
        self.approve(newer, expected=public.pk)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.lifecycle, "paused")

    def test_closed_listing_blocks_new_approval(self):
        public = self.publish()
        revision = self.submit(self.edit(public, title="Yeni"))
        Listing.objects.filter(pk=public.listing_id).update(lifecycle="closed")
        with self.assertRaises(InvalidRevisionState):
            self.approve(revision, expected=public.pk)
        self.approve(public)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.lifecycle, "closed")

    def test_submit_and_publish_require_all_linked_media_ready_and_owned(self):
        from media.models import MediaAsset, RevisionImage
        revision = self.draft()
        asset = MediaAsset.objects.create(owner=self.owner, source_mime="image/jpeg", source_bytes=1, width=1, height=1)
        RevisionImage.objects.create(revision=revision, asset=asset, position=0)
        with self.assertRaises(ValidationError):
            self.submit(revision)
        with TemporaryDirectory() as directory, override_settings(PRIVATE_MEDIA_ROOT=directory):
            from django.core.files.base import ContentFile
            asset.state = "ready"
            asset.derivative.save("ignored", ContentFile(b"test"), save=False)
            asset.save()
            self.submit(revision)
            asset.owner = self.other
            asset.save()
            with self.assertRaises(ValidationError):
                self.approve(revision)

    def test_outbox_unique_event_type_revision_and_safe_payload(self):
        from events.models import OutboxEvent
        revision = self.publish()
        event = OutboxEvent.objects.get()
        self.assertEqual(event.event_type, "listing.revision_published")
        self.assertEqual(event.payload["listing_id"], str(revision.listing_id))
        self.assertEqual(event.payload["revision_id"], revision.pk)
        self.assertEqual(event.payload["price"], "1234.50")
        self.assertNotIn("@", str(event.payload))
        with self.assertRaises(IntegrityError), transaction.atomic():
            OutboxEvent.objects.create(event_type=event.event_type, revision=revision, payload={})

    def test_restriction_targets_xor_and_active_time_boundaries(self):
        from moderation.models import Restriction
        from moderation.policies import public_visibility_restrictions
        public = self.publish()
        now = timezone.now()
        for targets in ({}, {"listing": public.listing, "seller": self.owner}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Restriction.objects.create(actor=self.reviewer, reason="Gizle", begins_at=now, **targets)
        restriction = Restriction.objects.create(actor=self.reviewer, listing=public.listing, reason="Gizle", begins_at=now)
        self.assertTrue(public_visibility_restrictions(at=now).filter(pk=restriction.pk).exists())
        restriction.ends_at = now
        restriction.save()
        self.assertFalse(public_visibility_restrictions(at=now).filter(pk=restriction.pk).exists())
        restriction.ends_at = now + timedelta(seconds=1)
        restriction.revoked_at = now
        restriction.save()
        self.assertFalse(public_visibility_restrictions(at=now).filter(pk=restriction.pk).exists())

    def assert_future_revocation_inactive(self, target):
        from moderation.models import Restriction
        from moderation.policies import public_visibility_restrictions, visible_listings
        public = self.publish()
        now = timezone.now()
        targets = {"listing": public.listing} if target == "listing" else {"seller": self.owner}
        restriction = Restriction.objects.create(
            actor=self.reviewer, reason="Gizle", begins_at=now, **targets)
        self.assertTrue(public_visibility_restrictions(at=now).filter(pk=restriction.pk).exists())
        self.assertFalse(visible_listings(at=now).filter(pk=public.listing_id).exists())
        restriction.revoked_at = now + timedelta(minutes=1)
        restriction.save(update_fields=["revoked_at"])
        with self.subTest(check="restriction_excluded"):
            self.assertFalse(public_visibility_restrictions(at=now).filter(pk=restriction.pk).exists())
        with self.subTest(check="listing_visible"):
            self.assertTrue(visible_listings(at=now).filter(pk=public.listing_id).exists())

    def test_future_revoked_listing_restriction_does_not_hide_public_listing(self):
        self.assert_future_revocation_inactive("listing")

    def test_future_revoked_seller_restriction_does_not_hide_public_listing(self):
        self.assert_future_revocation_inactive("seller")

    def test_listing_and_seller_visibility_restrictions_share_query(self):
        from moderation.models import Restriction
        from moderation.policies import visible_listings
        public = self.publish()
        other = self.publish()
        self.assertEqual(visible_listings().count(), 2)
        Restriction.objects.create(actor=self.reviewer, listing=public.listing, reason="Gizle")
        self.assertCountEqual(visible_listings().values_list("pk", flat=True), [other.listing_id])
        Restriction.objects.create(actor=self.reviewer, seller=self.owner, reason="Gizle")
        self.assertEqual(visible_listings().count(), 0)

    def test_visibility_checks_exact_expiry_and_approved_pointer(self):
        from moderation.policies import visible_listings
        public = self.publish()
        now = timezone.now()
        Listing.objects.filter(pk=public.listing_id).update(expires_at=now)
        self.assertFalse(visible_listings(at=now).exists())
        Listing.objects.filter(pk=public.listing_id).update(expires_at=now + timedelta(seconds=1))
        self.assertTrue(visible_listings(at=now).exists())
        Listing.objects.filter(pk=public.listing_id).update(lifecycle="paused")
        self.assertFalse(visible_listings(at=now).exists())
