from django.core.exceptions import PermissionDenied
from django.test import TransactionTestCase, override_settings

from accounts.models import User
from conversations.services import set_contact_enabled
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers
from listings.models import Listing, ListingRevision
from .test_drafts import DraftFixtures


@override_settings(PILOT_NEW_LISTINGS_PER_DAY=1)
class CreationLimitConcurrencyTests(PostgresLimitWorkers, DraftFixtures, TransactionTestCase):
    def test_final_new_identity_slot_has_one_winner(self):
        results = self.race(
            lambda: self.limited_operation(lambda: self.draft()),
            lambda: self.limited_operation(lambda: self.draft(content={})),
        )
        self.assertEqual(results.count("new_listing"), 1)
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(ListingRevision.objects.count(), 1)

    def test_committed_identity_is_visible_to_waiting_creation(self):
        results = self.ordered(
            lambda: self.draft().pk,
            lambda: self.limited_operation(lambda: self.draft()),
            [self.owner.pk],
        )
        self.assertEqual(results[1], "new_listing")
        self.assertEqual(Listing.objects.count(), 1)

    def test_rolled_back_identity_leaves_waiting_creation_slot_free(self):
        results = self.ordered(
            lambda: self.draft().pk,
            lambda: self.limited_operation(lambda: self.draft()),
            [self.owner.pk], rollback=True,
        )
        self.assertNotEqual(results[1], "new_listing")
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(ListingRevision.objects.count(), 1)

    def test_waiting_creation_rechecks_committed_account_deactivation(self):
        def create():
            try:
                return self.draft().pk
            except PermissionDenied:
                return "inactive"

        results = self.ordered(
            lambda: User.objects.filter(pk=self.owner.pk).update(is_active=False),
            create, [self.owner.pk],
        )
        self.assertEqual(results[1], "inactive")
        self.assertEqual(Listing.objects.count(), 0)

    @override_settings(PILOT_NEW_LISTINGS_PER_DAY=2)
    def test_creation_overlaps_existing_listing_then_user_contact_toggle_without_inversion(self):
        existing = self.draft().listing
        results = self.ordered(
            lambda: self.draft().pk,
            lambda: set_contact_enabled(actor=self.owner, listing_id=existing.pk, enabled=False).pk,
            [self.owner.pk],
        )
        self.assertEqual(results[1], existing.pk)
        existing.refresh_from_db()
        self.assertFalse(existing.contact_enabled)
        self.assertEqual(Listing.objects.count(), 2)
        self.assertEqual(ListingRevision.objects.count(), 2)

    @override_settings(PILOT_NEW_LISTINGS_PER_DAY=2)
    def test_unordered_creation_and_contact_toggle_complete_without_deadlock(self):
        existing = self.draft().listing
        results = self.race(
            lambda: self.draft().pk,
            lambda: set_contact_enabled(actor=self.owner, listing_id=existing.pk, enabled=False).pk,
        )
        self.assertEqual(results[1], existing.pk)
        self.assertEqual(Listing.objects.count(), 2)
