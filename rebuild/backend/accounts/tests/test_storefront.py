from allauth.account.models import EmailAddress
from django.test import TestCase
from accounts.models import User, Storefront
from datetime import timedelta
from uuid import UUID
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from accounts.storefronts import create_storefront, change_storefront, public_storefronts, StorefrontConflict
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers
from listings.tests.test_drafts import DraftFixtures
from listings.models import Listing, ListingRevision
from moderation.models import Restriction, MessagingRestriction
from events.models import OutboxEvent


def verified(user):
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)


class StorefrontFixtures(DraftFixtures):
    def setUp(self):
        super().setUp()
        verified(self.owner)
        verified(self.other)
        self.store = create_storefront(actor=self.owner, name="Özel vitrin", intro="Tanıtım")
        self.client.force_login(self.owner)

    def change(self, action, **data):
        self.store.refresh_from_db()
        self.store = change_storefront(actor=self.owner, storefront_id=self.store.pk,
            expected_version=self.store.edit_version, action=action, **data)
        return self.store

    def public_url(self):
        return reverse("storefronts:public", args=[self.store.pk])

    def action_url(self, action):
        return reverse("storefronts:" + action, args=[self.store.pk])


class StorefrontServiceTests(StorefrontFixtures, TestCase):
    def test_optional_private_uuid_and_no_account_fallback(self):
        self.assertIsInstance(self.store.pk, UUID)
        self.assertFalse(self.store.is_published)
        self.assertEqual(self.store.published_name, "")
        self.assertNotEqual(str(self.store.pk), str(self.owner.pk))
        self.assertFalse(Storefront.objects.filter(owner=self.other).exists())

    def test_repeated_create_does_not_overwrite_draft(self):
        same = create_storefront(actor=self.owner, name="Overwrite", intro="Other")
        self.assertEqual(same.pk, self.store.pk)
        self.assertEqual(same.draft_name, "Özel vitrin")
        self.assertEqual(Storefront.objects.count(), 1)

    def test_database_rejects_duplicate_owner(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Storefront.objects.create(owner=self.owner, draft_name="Second")

    def test_name_intro_limits_no_email_fallback(self):
        for name, intro in [(" ", ""), ("x"*81, ""), ("OK", "x"*2001), ("\x00", "")]:
            with self.subTest(length=len(name)), self.assertRaises(ValidationError):
                create_storefront(actor=self.other, name=name, intro=intro)
        created = create_storefront(actor=self.other, name="x"*80, intro="x"*2000)
        self.assertEqual(len(created.draft_intro), 2000)

    def test_draft_save_preserves_public_snapshot_until_explicit_publish(self):
        self.change("publish")
        self.change("save", name="Yeni taslak", intro="Özel yeni metin")
        response = self.client.get(self.public_url())
        self.assertContains(response, "Özel vitrin")
        self.assertNotContains(response, "Özel yeni metin")
        preview = self.client.get(self.action_url("preview"))
        self.assertContains(preview, "Özel yeni metin")
        self.change("publish")
        self.assertContains(self.client.get(self.public_url()), "Özel yeni metin")

    def test_stale_save_and_publish_conflict_without_overwrite(self):
        version = self.store.edit_version
        self.change("save", name="Current", intro="Current intro")
        for action in ["save", "publish"]:
            with self.assertRaises(StorefrontConflict):
                change_storefront(actor=self.owner, storefront_id=self.store.pk,
                    expected_version=version, action=action, name="Lost", intro="Lost")
        self.store.refresh_from_db()
        self.assertEqual(self.store.draft_name, "Current")
        self.assertFalse(self.store.is_published)

    def test_unpublish_idempotent_republish_uuid_stable_stale_removal_rejected(self):
        original = self.store.pk
        self.change("publish")
        old = self.store.edit_version
        self.change("unpublish")
        version = self.store.edit_version
        same = change_storefront(actor=self.owner, storefront_id=original, expected_version=old, action="unpublish")
        self.assertEqual(same.edit_version, version)
        self.change("publish")
        self.assertEqual(self.store.pk, original)
        with self.assertRaises(StorefrontConflict):
            change_storefront(actor=self.owner, storefront_id=original, expected_version=old, action="unpublish")

    def test_no_listing_outbox_or_notification_side_effect(self):
        from notifications.models import SavedSearch, NotificationDelivery
        revision = self.approved()
        before = list(Listing.objects.values())
        counts = (OutboxEvent.objects.count(), SavedSearch.objects.count(), NotificationDelivery.objects.count())
        for action in ["publish", "unpublish", "publish"]:
            self.change(action)
        self.assertEqual(list(Listing.objects.values()), before)
        self.assertEqual((OutboxEvent.objects.count(), SavedSearch.objects.count(), NotificationDelivery.objects.count()), counts)
        self.change("unpublish")
        self.assertEqual(self.client.get(reverse("listings:detail", args=[revision.listing_id])).status_code, 200)


class StorefrontAccessTests(StorefrontFixtures, TestCase):
    def test_anonymous_private_routes_redirect_without_writes(self):
        self.client.logout()
        for url in [reverse("storefronts:manage"), self.action_url("preview")]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/accounts/login/?next=/vitrinim/"))
            self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(Storefront.objects.count(), 1)

    def test_owner_body_and_external_next_ignored(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("storefronts:create"), {"name": "Other", "intro": "",
            "owner": self.owner.pk, "user": self.owner.pk, "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("storefronts:manage"))
        self.assertTrue(Storefront.objects.filter(owner=self.other, draft_name="Other").exists())

    def test_other_owner_cannot_preview_or_write_even_staff(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.action_url("preview")).status_code, 404)
        for action in ["save", "publish", "unpublish"]:
            self.assertEqual(self.client.post(self.action_url(action), {
                "edit_version": 1, "name": "Attack", "intro": "Attack"}).status_code, 404)
        self.other.is_staff = True
        self.other.save()
        with self.assertRaises(Exception) as error:
            change_storefront(actor=self.other, storefront_id=self.store.pk, expected_version=1, action="publish")
        from django.http import Http404
        self.assertIsInstance(error.exception, Http404)

    def test_unverified_and_inactive_actor_denied_by_service(self):
        EmailAddress.objects.filter(user=self.owner).update(verified=False)
        self.assertEqual(self.client.get(reverse("storefronts:manage")).status_code, 403)
        with self.assertRaises(PermissionDenied):
            self.change("publish")
        EmailAddress.objects.filter(user=self.owner).update(verified=True)
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.change("publish")

    def test_current_email_change_hides_profile(self):
        self.change("publish")
        self.owner.email = "different@example.test"
        self.owner.save()
        self.assertEqual(self.client.get(self.public_url()).status_code, 404)

    def test_staff_mfa_boundary_stays_and_public_has_no_private_counter(self):
        self.change("publish")
        self.owner.is_staff = True
        self.owner.save()
        response = self.client.post(self.action_url("publish"), {"edit_version": self.store.edit_version})
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.public_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("unread_notification_count", response.context)

    def test_csrf_and_get_writes_denied_with_private_headers(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url in [reverse("storefronts:create"), *[self.action_url(a) for a in ["save", "publish", "unpublish"]]]:
            self.assertEqual(client.get(url).status_code, 405)
            response = client.post(url, {"name": "No", "edit_version": 1})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_unpublished_public_is_generic_404_even_owner(self):
        response = self.client.get(self.public_url())
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Özel vitrin", status_code=404)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_conflict_http409_and_invalid_fields400(self):
        self.change("save", name="Current", intro="")
        response = self.client.post(self.action_url("save"), {"name": "Old", "intro": "", "edit_version": 1})
        self.assertContains(response, "Vitrin değişti", status_code=409)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        response = self.client.post(self.action_url("save"), {"name": "", "edit_version": 2})
        self.assertEqual(response.status_code, 400)

    def test_html_escape_and_private_identity_not_rendered(self):
        self.change("save", name="<script>name</script>", intro='<img src=x onerror="alert(1)">')
        self.change("publish")
        response = self.client.get(self.public_url())
        self.assertContains(response, "&lt;script&gt;name&lt;/script&gt;")
        self.assertNotContains(response, '<img src=x')
        self.assertNotContains(response, self.owner.email)

    def test_seller_listing_and_messaging_restrictions_are_distinct(self):
        revision = self.approved()
        self.change("publish")
        MessagingRestriction.objects.create(user=self.owner, actor=self.other, reason="Private messaging reason")
        Restriction.objects.create(listing=revision.listing, actor=self.other, reason="Private listing reason")
        response = self.client.get(self.public_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        restriction = Restriction.objects.create(seller=self.owner, actor=self.other, reason="Private seller reason")
        response = self.client.get(self.public_url())
        self.assertNotContains(response, "Private seller reason", status_code=404)
        restriction.revoked_at = timezone.now()
        restriction.save()
        self.assertTrue(public_storefronts().filter(pk=self.store.pk).exists())

    def test_restriction_expiry_and_future_start(self):
        self.change("publish")
        now = timezone.now()
        for begins, ends in [(now-timedelta(days=2), now-timedelta(days=1)), (now+timedelta(days=1), None)]:
            Restriction.objects.create(seller=self.owner, actor=self.other, reason="Private", begins_at=begins, ends_at=ends)
        self.assertTrue(public_storefronts().filter(pk=self.store.pk).exists())


class StorefrontSearchTests(StorefrontFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.change("publish")

    def test_two_sellers_scope_and_no_save_search_action(self):
        own = self.approved()
        other_listing = Listing.objects.create(owner=self.other, lifecycle="live")
        other = ListingRevision.objects.create(listing=other_listing, category=self.category,
            attribute_schema=self.schema, schema_version=1, status="approved", title="Other secret title")
        other_listing.public_revision = other
        other_listing.save()
        response = self.client.get(self.public_url(), {"owner": self.other.pk, "q": "Yayındaki"})
        self.assertEqual([r.pk for r in response.context["page_obj"]], [own.listing_id])
        self.assertNotContains(response, "Other secret title")
        self.assertNotContains(response, "Aramayı kaydet")
        self.assertNotContains(response, "Uygulama içi bildirimleri aç")
        self.assertContains(response, 'action="'+self.public_url()+'"')
        self.assertContains(response, 'class="search-page"')

    def test_preview_contains_only_public_set_and_current_revision(self):
        approved = self.approved()
        self.draft(content={**self.content, "title": "Private draft canary"})
        ListingRevision.objects.create(listing=approved.listing, category=self.category,
            attribute_schema=self.schema, schema_version=1, title="New private revision")
        response = self.client.get(self.action_url("preview"))
        self.assertContains(response, "Yayındaki")
        self.assertNotContains(response, "Private draft canary")
        self.assertNotContains(response, "New private revision")
        Listing.objects.filter(pk=approved.listing_id).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.get(self.public_url()).context["page_obj"].paginator.count, 0)

    def test_invalid_filter_never_queries_listing_results(self):
        self.approved()
        self.client.logout()
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(self.public_url(), {"currency": "INVALID", "price_min": "5"})
        self.assertFalse(response.context["search_valid"])
        self.assertIsNone(response.context["page_obj"])
        self.assertFalse(any('"listings_listing"' in q["sql"] for q in captured))

    def test_turkish_decimal_category_frozen_schema_filters(self):
        revision = self.approved()
        ListingRevision.objects.filter(pk=revision.pk).update(title="İstanbul araç", location="Şişli")
        from catalog.models import AttributeSchema
        AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": {"new": {"type": "string"}}})
        params = {"q": "istanbul", "currency": "EUR", "price_min": "99.50", "price_max": "100.00",
            "category": self.category.pk, "schema": self.schema.pk, "schema_version": 1, "a.model_year.eq": "2020"}
        response = self.client.get(self.public_url(), params)
        self.assertTrue(response.context["search_valid"])
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertEqual(response.context["search_spec"].attribute_schema.version, 1)
        self.assertEqual(response.context["search_spec"].attribute_schema.id, self.schema.pk)

    def test_sql_pagination_stable_and_bounded_queries(self):
        for _ in range(25):
            self.approved()
        self.client.logout()
        with CaptureQueriesContext(connection) as first:
            response = self.client.get(self.public_url(), {"currency": "EUR", "sort": "price_asc"})
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertEqual(response.context["page_obj"].paginator.count, 25)
        self.assertTrue(response.context["next_url"].startswith(self.public_url()+"?"))
        self.assertIn("currency=EUR", response.context["next_url"])
        self.assertLessEqual(len(first), 12)
        self.assertTrue(any("LIMIT 12" in q["sql"] for q in first))
        second = self.client.get(response.context["next_url"])
        self.assertFalse({r.pk for r in response.context["page_obj"]} & {r.pk for r in second.context["page_obj"]})

    def test_listing_detail_links_only_visible_storefront(self):
        revision = self.approved()
        url = reverse("listings:detail", args=[revision.listing_id])
        self.assertContains(self.client.get(url), self.public_url())
        self.change("unpublish")
        self.assertNotContains(self.client.get(url), "Satıcının vitrini")

    def test_closed_listing_and_private_revision_image_not_exposed(self):
        from media.models import MediaAsset, RevisionImage
        revision = self.approved()
        asset = MediaAsset.objects.create(owner=self.owner, state="ready", source_bytes=1,
            width=1, height=1, source_mime="image/jpeg", derivative="derivatives/synthetic.jpg")
        RevisionImage.objects.create(revision=revision, asset=asset, position=0)
        response = self.client.get(self.public_url())
        image_url = reverse("listings:public_image", args=[revision.listing_id, revision.pk, asset.pk])
        self.assertContains(response, image_url)
        Listing.objects.filter(pk=revision.listing_id).update(lifecycle="closed")
        self.assertNotContains(self.client.get(self.public_url()), image_url)
        self.assertEqual(self.client.get(image_url).status_code, 404)

    def test_inactive_owner_hides_public_profile(self):
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.client.logout()
        self.assertEqual(self.client.get(self.public_url()).status_code, 404)


class StorefrontConcurrencyTests(PostgresLimitWorkers, TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user("concurrent-store@example.test", "test-only")
        verified(self.owner)

    def test_parallel_creates_have_one_stable_owner_record(self):
        def create():
            return create_storefront(actor=User.objects.get(pk=self.owner.pk), name="Concurrent").pk
        result = self.race(create, create)
        self.assertEqual(result[0], result[1])
        self.assertEqual(Storefront.objects.count(), 1)

    def test_parallel_save_publish_one_conflict(self):
        store = create_storefront(actor=self.owner, name="Before")
        def write(action):
            try:
                change_storefront(actor=User.objects.get(pk=self.owner.pk), storefront_id=store.pk,
                    expected_version=1, action=action, name="After", intro="New")
                return "ok"
            except StorefrontConflict:
                return "conflict"
        self.assertCountEqual(self.race(lambda: write("save"), lambda: write("publish")), ["ok", "conflict"])
        store.refresh_from_db()
        self.assertEqual(store.edit_version, 2)


class StorefrontEntryTests(TestCase):
    def test_verified_owner_gets_private_management_without_creating_profile(self):
        user = User.objects.create_user("storefront-entry@example.test", "test-only")
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        self.client.force_login(user)
        response = self.client.get("/vitrinim/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vitrin oluştur")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertFalse(Storefront.objects.exists())
