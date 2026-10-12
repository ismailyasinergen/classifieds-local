from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier
from uuid import UUID

from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase

from accounts.models import User
from catalog.models import AttributeSchema, Category
from catalog.validation import validate_attributes
from listings.models import Listing, ListingRevision
from listings.services import (
    InvalidRevisionState, StaleEditVersion, create_listing_draft, start_revision, update_draft,
)


class DraftFixtures:
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.test", "password")
        self.other = User.objects.create_user("other@example.test", "password")
        self.category = Category.objects.create(name="Otomobil", slug="auto")
        self.schema = AttributeSchema.objects.create(
            category=self.category, version=1,
            definition={"fields": {
                "model_year": {"type": "integer", "required": True, "min": 1900},
                "area": {"type": "decimal", "required": True},
                "electric": {"type": "boolean"},
                "brand": {"type": "string"},
            }},
        )
        self.content = {
            "title": "  Araba  ", "description": "  Açıklama  ",
            "price": "1234.50", "currency": " eur ", "location": " Berlin ",
            "attributes": {"model_year": "2020", "area": "82.500", "electric": False},
        }

    def draft(self, **kwargs):
        return create_listing_draft(actor=kwargs.get("actor", self.owner),
                                    category_id=self.category.pk,
                                    content=kwargs.get("content", self.content))

    def approved(self):
        listing = Listing.objects.create(owner=self.owner)
        revision = ListingRevision.objects.create(
            listing=listing, category=self.category, attribute_schema=self.schema, schema_version=1,
            status=ListingRevision.Status.APPROVED, title="Yayındaki", description="Açıklama",
            price=Decimal("100"), currency="EUR", location="Berlin",
            attributes={"model_year": 2020, "area": "82.5"},
        )
        listing.public_revision = revision
        listing.lifecycle = Listing.Lifecycle.LIVE
        listing.save()
        return revision


class DraftTests(DraftFixtures, TestCase):
    def test_owner_can_create_draft(self):
        original = deepcopy(self.content)
        revision = self.draft()
        self.assertIsInstance(revision.listing_id, UUID)
        self.assertEqual(revision.listing.owner_id, self.owner.pk)
        self.assertEqual(revision.status, "draft")
        self.assertEqual(revision.edit_version, 1)
        self.assertEqual(revision.attribute_schema_id, self.schema.pk)
        self.assertEqual(revision.schema_version, 1)
        self.assertEqual(revision.title, "Araba")
        self.assertEqual(revision.location, "Berlin")
        self.assertEqual(revision.price, Decimal("1234.50"))
        self.assertEqual(revision.currency, "EUR")
        self.assertEqual(revision.attributes, {"model_year": 2020, "area": "82.5", "electric": False})
        self.assertIsNone(revision.listing.public_revision_id)
        self.assertEqual(self.content, original)

    def test_category_only_draft_is_allowed(self):
        revision = self.draft(content={})
        self.assertEqual(revision.title, "")
        self.assertEqual(revision.attributes, {})
        self.assertEqual(revision.currency, "")
        self.assertIsNone(revision.price)
        with self.assertRaises(ValidationError):
            validate_attributes(schema=self.schema, values=revision.attributes)

    def test_null_price_remains_null(self):
        self.assertIsNone(self.draft(content={"price": None}).price)

    def test_other_user_cannot_update_draft(self):
        revision = self.draft()
        with self.assertRaises(PermissionDenied):
            update_draft(actor=self.other, revision_id=revision.pk,
                         expected_version=1, content={"title": "Çalınan"})
        revision.refresh_from_db()
        self.assertEqual(revision.title, "Araba")
        self.assertEqual(revision.edit_version, 1)

    def test_inactive_and_anonymous_actors_cannot_mutate(self):
        revision = self.draft()
        self.owner.is_active = False
        self.owner.save()
        for actor in (self.owner, AnonymousUser()):
            with self.subTest(actor=type(actor).__name__):
                with self.assertRaises(PermissionDenied):
                    self.draft(actor=actor)
                with self.assertRaises(PermissionDenied):
                    update_draft(actor=actor, revision_id=revision.pk, expected_version=1, content={})
                with self.assertRaises(PermissionDenied):
                    start_revision(actor=actor, listing_id=revision.listing_id)

    def test_draft_updates_do_not_change_public_revision(self):
        public = self.approved()
        draft = start_revision(actor=self.owner, listing_id=public.listing_id)
        updated = update_draft(actor=self.owner, revision_id=draft.pk,
                               expected_version=1, content={"title": "Yeni", "price": "90"})
        self.assertEqual(updated.edit_version, 2)
        self.assertEqual(updated.title, "Yeni")
        self.assertEqual(updated.description, public.description)
        public.refresh_from_db()
        public.listing.refresh_from_db()
        self.assertEqual(public.title, "Yayındaki")
        self.assertEqual(public.price, Decimal("100"))
        self.assertEqual(public.listing.public_revision_id, public.pk)

    def test_stale_edit_version_is_rejected(self):
        revision = self.draft()
        update_draft(actor=self.owner, revision_id=revision.pk, expected_version=1, content={"title": "Yeni"})
        with self.assertRaises(StaleEditVersion):
            update_draft(actor=self.owner, revision_id=revision.pk,
                         expected_version=1, content={"price": "1", "attributes": {}})
        revision.refresh_from_db()
        self.assertEqual(revision.title, "Yeni")
        self.assertEqual(revision.price, Decimal("1234.50"))
        self.assertEqual(revision.edit_version, 2)

    def test_expected_version_requires_positive_integer(self):
        revision = self.draft()
        for value in (True, 1.0, "1", None, 0, -1):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                update_draft(actor=self.owner, revision_id=revision.pk,
                             expected_version=value, content={})

    def test_submitted_and_terminal_revisions_are_not_editable(self):
        for status in ("submitted", "approved", "rejected", "withdrawn"):
            with self.subTest(status=status):
                revision = self.draft()
                ListingRevision.objects.filter(pk=revision.pk).update(status=status)
                with self.assertRaises(InvalidRevisionState):
                    update_draft(actor=self.owner, revision_id=revision.pk,
                                 expected_version=1, content={"title": "Yeni"})
                revision.refresh_from_db()
                self.assertEqual(revision.title, "Araba")

    def test_start_returns_existing_open_revision(self):
        revision = self.draft()
        self.assertEqual(start_revision(actor=self.owner, listing_id=revision.listing_id).pk, revision.pk)
        ListingRevision.objects.filter(pk=revision.pk).update(status="submitted")
        with self.assertRaises(InvalidRevisionState):
            start_revision(actor=self.owner, listing_id=str(revision.listing_id))
        self.assertEqual(revision.listing.revisions.count(), 1)

    def test_other_user_cannot_start_revision(self):
        public = self.approved()
        with self.assertRaises(PermissionDenied):
            start_revision(actor=self.other, listing_id=public.listing_id)

    def test_start_copies_last_rejected_initial_revision(self):
        revision = self.draft()
        ListingRevision.objects.filter(pk=revision.pk).update(status="rejected")
        copy = start_revision(actor=self.owner, listing_id=revision.listing_id)
        self.assertNotEqual(copy.pk, revision.pk)
        self.assertEqual(copy.status, "draft")
        self.assertEqual(copy.title, revision.title)
        self.assertEqual(copy.attributes, revision.attributes)
        self.assertEqual(copy.edit_version, 1)

    def test_start_copies_last_withdrawn_initial_revision(self):
        revision = self.draft()
        ListingRevision.objects.filter(pk=revision.pk).update(status="withdrawn")
        self.assertEqual(start_revision(actor=self.owner, listing_id=revision.listing_id).title, revision.title)

    def test_start_preserves_latest_rejected_edits_on_published_listing(self):
        public = self.approved()
        rejected = ListingRevision.objects.create(
            listing=public.listing, category=self.category, attribute_schema=self.schema,
            schema_version=1, status="rejected", title="Son düzenleme")
        draft = start_revision(actor=self.owner, listing_id=public.listing_id)
        self.assertEqual(draft.title, rejected.title)
        self.assertEqual(draft.attribute_schema_id, rejected.attribute_schema_id)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.public_revision_id, public.pk)

    def test_start_without_source_is_invalid(self):
        listing = Listing.objects.create(owner=self.owner)
        with self.assertRaises(InvalidRevisionState):
            start_revision(actor=self.owner, listing_id=listing.pk)

    def test_blank_currency_can_remain_incomplete(self):
        self.assertEqual(self.draft(content={"currency": "  "}).currency, "")

    def test_schema_is_pinned_after_new_version(self):
        revision = self.draft()
        AttributeSchema.objects.create(category=self.category, version=2,
                                       definition={"fields": {"new": {"type": "boolean", "required": True}}})
        updated = update_draft(actor=self.owner, revision_id=revision.pk, expected_version=1,
                               content={"attributes": {"model_year": "2021"}})
        self.assertEqual(updated.attribute_schema_id, self.schema.pk)
        self.assertEqual(updated.schema_version, 1)
        new = self.draft(content={})
        self.assertEqual(new.schema_version, 2)

    def test_invalid_provided_values_are_rejected_atomically(self):
        invalid = [
            {"price": True}, {"price": "NaN"}, {"price": "Infinity"}, {"price": "-1"},
            {"price": "bad"}, {"price": "0.001"}, {"price": "10000000000000000"},
            {"currency": "EU"}, {"currency": "EURO"}, {"currency": 123}, {"currency": "€UR"},
            {"title": None}, {"title": 123}, {"location": []}, {"description": True},
            {"attributes": None}, {"attributes": []}, {"attributes": {"unknown": 1}},
            {"attributes": {"model_year": True}}, {"attributes": {"model_year": 1800}},
            {"attributes": {"area": "NaN"}}, {"attributes": {"electric": 1}},
            {"title": "a" * 201}, {"description": "a" * 20001}, {"location": "a" * 161},
            {"schema_version": 99}, {"owner": self.other.pk}, {"status": "approved"},
        ]
        revision = self.draft()
        for content in invalid:
            with self.subTest(content=content):
                with self.assertRaises(ValidationError):
                    self.draft(content=content)
                with self.assertRaises(ValidationError):
                    update_draft(actor=self.owner, revision_id=revision.pk,
                                 expected_version=1, content=content)
                revision.refresh_from_db()
                self.assertEqual(revision.edit_version, 1)
                self.assertEqual(revision.title, "Araba")
        self.assertEqual(Listing.objects.count(), 1)

    def test_non_dictionary_content_is_rejected(self):
        for content in (None, [], "title", True):
            with self.subTest(content=content), self.assertRaises(ValidationError):
                self.draft(content=content)

    def test_missing_category_schema_is_rejected_without_orphan(self):
        category = Category.objects.create(name="Boş", slug="empty")
        with self.assertRaises(ValidationError):
            create_listing_draft(actor=self.owner, category_id=category.pk, content={})
        self.assertEqual(Listing.objects.count(), 0)

    def test_category_change_is_explicitly_rejected(self):
        revision = self.draft()
        with self.assertRaises(ValidationError):
            update_draft(actor=self.owner, revision_id=revision.pk, expected_version=1,
                         content={"category_id": self.category.pk})

    def test_public_pointer_requires_same_listing_and_approved_state(self):
        public = self.approved()
        other = Listing.objects.create(owner=self.owner, public_revision=public)
        with self.assertRaises(ValidationError):
            other.full_clean()
        draft = self.draft()
        draft.listing.public_revision = draft
        with self.assertRaises(ValidationError):
            draft.listing.full_clean()

    def test_revision_schema_identity_must_match_category_and_version(self):
        revision = self.draft()
        revision.schema_version = 2
        with self.assertRaises(ValidationError):
            revision.full_clean()
        revision.schema_version = 1
        revision.category = Category.objects.create(name="Diğer", slug="other")
        with self.assertRaises(ValidationError):
            revision.full_clean()

    def test_reviewer_permission_is_defined(self):
        self.assertTrue(Permission.objects.filter(
            content_type__app_label="listings", codename="review_listingrevision").exists())

    def test_staff_flag_does_not_grant_review_permission(self):
        self.other.is_staff = True
        self.other.save()
        self.assertFalse(self.other.has_perm("listings.review_listingrevision"))


class DraftConcurrencyTests(DraftFixtures, TransactionTestCase):
    def run_workers(self, callback):
        barrier = Barrier(2)

        def worker():
            connections.close_all()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=5)
                return pid, callback()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        return [result[1] for result in results]

    def test_only_one_open_revision_per_listing(self):
        self.assertEqual(connection.vendor, "postgresql")
        public = self.approved()
        result = self.run_workers(lambda: start_revision(actor=self.owner, listing_id=public.listing_id).pk)
        self.assertEqual(result[0], result[1])
        self.assertEqual(public.listing.revisions.filter(status__in=["draft", "submitted"]).count(), 1)

    def test_database_constraint_rejects_competing_open_revisions(self):
        public = self.approved()

        def insert():
            try:
                with transaction.atomic():
                    ListingRevision.objects.create(
                        listing_id=public.listing_id, category=self.category,
                        attribute_schema=self.schema, schema_version=1)
                return "inserted"
            except IntegrityError:
                return "conflict"

        self.assertCountEqual(self.run_workers(insert), ["inserted", "conflict"])

    def test_concurrent_edits_have_one_winner(self):
        revision = self.draft()

        def update():
            try:
                return update_draft(actor=self.owner, revision_id=revision.pk, expected_version=1,
                                    content={"title": "Kazanan"}).edit_version
            except StaleEditVersion:
                return "stale"

        self.assertCountEqual(self.run_workers(update), [2, "stale"])
        revision.refresh_from_db()
        self.assertEqual(revision.edit_version, 2)
