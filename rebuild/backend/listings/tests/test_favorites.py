from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import User
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers
from listings.favorites import add_favorite, remove_favorite
from listings.models import Favorite, Listing, ListingRevision
from media.models import MediaAsset, RevisionImage
from moderation.models import Restriction

from .test_drafts import DraftFixtures


class FavoritesEntryTests(DraftFixtures, TestCase):
    def test_authenticated_user_has_private_favorites_screen(self):
        self.client.force_login(self.owner)
        response = self.client.get('/favorilerim/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Favorilerim')
        self.assertIn('no-store', response['Cache-Control'])


class FavoriteFixtures(DraftFixtures):
    def setUp(self):
        super().setUp()
        for user in (self.owner, self.other):
            EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        self.revision = self.approved()
        self.listing_id = self.revision.listing_id

    def add(self, listing_id=None, actor=None):
        return add_favorite(actor=actor or self.other, listing_id=listing_id or self.listing_id)

    def fill(self, count):
        listings = Listing.objects.bulk_create([Listing(owner=self.owner) for _ in range(count)])
        Favorite.objects.bulk_create([Favorite(user=self.other, listing=item) for item in listings])


class FavoriteTests(FavoriteFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.other)
        self.add_url = f'/favorilerim/{self.listing_id}/ekle/'
        self.remove_url = f'/favorilerim/{self.listing_id}/kaldir/'

    def test_explicit_posts_are_idempotent_and_ignore_owner_and_next(self):
        for _ in range(2):
            response = self.client.post(self.add_url, {'user': self.owner.pk, 'next': 'https://evil.test/'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, f'/ilanlar/{self.listing_id}/')
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(Favorite.objects.get().user_id, self.other.pk)
        for _ in range(2):
            response = self.client.post(self.remove_url)
            self.assertEqual(response.status_code, 302)
        self.assertFalse(Favorite.objects.exists())

    def test_get_never_adds_or_removes(self):
        for url in (self.add_url, self.remove_url):
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertFalse(Favorite.objects.exists())

    def test_anonymous_inactive_unverified_and_csrf(self):
        anonymous = Client()
        self.assertEqual(anonymous.post(self.add_url).status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.other)
        self.assertEqual(csrf.post(self.add_url).status_code, 403)
        EmailAddress.objects.filter(user=self.other).update(verified=False)
        response = self.client.post(self.add_url)
        self.assertEqual(response.status_code, 403)
        self.assertIn('no-store', response['Cache-Control'])
        User.objects.filter(pk=self.other.pk).update(is_active=False)
        self.assertEqual(self.client.post(self.add_url).status_code, 302)
        with self.assertRaises(PermissionDenied):
            self.add()
        self.assertFalse(Favorite.objects.exists())

    def test_required_mfa_is_not_bypassed(self):
        User.objects.filter(pk=self.other.pk).update(is_staff=True)
        self.assertEqual(self.client.post(self.add_url).status_code, 403)
        self.assertFalse(Favorite.objects.exists())

    def test_non_public_lifecycles_and_expiry_cannot_be_added(self):
        for lifecycle in ('draft', 'paused', 'closed'):
            Listing.objects.filter(pk=self.listing_id).update(lifecycle=lifecycle)
            self.assertEqual(self.client.post(self.add_url).status_code, 404)
        Listing.objects.filter(pk=self.listing_id).update(lifecycle='live', expires_at=timezone.now())
        self.assertEqual(self.client.post(self.add_url).status_code, 404)
        self.assertFalse(Favorite.objects.exists())

    def test_restriction_is_rechecked_even_on_replay(self):
        self.add()
        Restriction.objects.create(listing_id=self.listing_id, actor=self.owner, reason='PRIVATE REASON')
        self.assertEqual(self.client.post(self.add_url).status_code, 404)
        response = self.client.get('/favorilerim/')
        self.assertContains(response, 'İlan şu anda kullanılamıyor')
        self.assertNotContains(response, 'PRIVATE REASON')
        self.assertNotContains(response, self.revision.title)

    def test_closed_favorite_has_no_content_but_can_be_removed(self):
        self.add()
        Listing.objects.filter(pk=self.listing_id).update(lifecycle='closed')
        response = self.client.get('/favorilerim/')
        self.assertContains(response, 'İlan şu anda kullanılamıyor')
        self.assertNotContains(response, self.revision.title)
        self.assertNotContains(response, 'EUR')
        self.assertNotContains(response, '/fotograflar/')
        self.assertEqual(self.client.post(self.remove_url).status_code, 302)

    def test_current_public_revision_only_and_guarded_image_route(self):
        self.add()
        asset = MediaAsset.objects.create(owner=self.owner, state='ready', source_bytes=1,
                                          width=1, height=1, derivative='derivatives/synthetic.jpg')
        RevisionImage.objects.create(revision=self.revision, asset=asset, position=0)
        draft = ListingRevision.objects.create(listing_id=self.listing_id, category=self.category,
            attribute_schema=self.schema, schema_version=1, title='PRIVATE DRAFT')
        response = self.client.get('/favorilerim/')
        self.assertContains(response, self.revision.title)
        self.assertNotContains(response, draft.title)
        self.assertContains(response, f'/ilanlar/{self.listing_id}/fotograflar/{self.revision.pk}/{asset.pk}/')
        ListingRevision.objects.filter(pk=draft.pk).update(status='approved', title='Yeni onaylı')
        Listing.objects.filter(pk=self.listing_id).update(public_revision=draft)
        response = self.client.get('/favorilerim/')
        self.assertContains(response, 'Yeni onaylı')
        self.assertNotContains(response, self.revision.title)

    def test_another_users_favorites_not_listed_or_removed(self):
        self.add(actor=self.owner)
        self.assertNotContains(self.client.get('/favorilerim/'), self.revision.title)
        self.client.post(self.remove_url, {'user': self.owner.pk})
        self.assertEqual(Favorite.objects.get().user_id, self.owner.pk)

    def test_unique_constraint(self):
        self.add()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=self.other, listing_id=self.listing_id)

    def test_capacity_replay_removal_and_staff_have_no_exemption(self):
        self.add()
        self.fill(199)
        self.assertEqual(self.add().pk, Favorite.objects.get(user=self.other, listing_id=self.listing_id).pk)
        second = self.approved()
        for staff in (False, True):
            User.objects.filter(pk=self.other.pk).update(is_staff=staff)
            with self.assertRaises(ValidationError):
                self.add(second.listing_id)
        remove_favorite(actor=self.other, listing_id=self.listing_id)
        self.add(second.listing_id)
        self.assertEqual(Favorite.objects.filter(user=self.other).count(), 200)

    def test_stable_sql_pagination_and_bounded_queries(self):
        self.add()
        with CaptureQueriesContext(connection) as one:
            self.client.get('/favorilerim/')
        for _ in range(24):
            self.add(self.approved().listing_id)
        Favorite.objects.all().update(created_at=timezone.now())
        with CaptureQueriesContext(connection) as many:
            response = self.client.get('/favorilerim/')
        self.assertLessEqual(len(many), len(one) + 1)
        self.assertTrue(any('LIMIT 12' in query['sql'] for query in many))
        ids = [row.pk for row in response.context['page_obj']]
        expected = list(Favorite.objects.order_by('-pk').values_list('pk', flat=True)[:12])
        self.assertEqual(ids, expected)
        second = self.client.get('/favorilerim/?page=2')
        self.assertFalse(set(ids) & {row.pk for row in second.context['page_obj']})


class FavoriteConcurrencyTests(PostgresLimitWorkers, FavoriteFixtures, TransactionTestCase):
    def result(self, listing_id):
        try:
            return self.add(listing_id).pk
        except ValidationError:
            return 'full'

    def test_parallel_same_record_has_one_row(self):
        results = self.race(lambda: self.add().pk, lambda: self.add().pk)
        self.assertEqual(results[0], results[1])
        self.assertEqual(Favorite.objects.count(), 1)

    def test_parallel_distinct_last_slot(self):
        self.fill(199)
        second = self.approved()
        results = self.race(lambda: self.result(self.listing_id), lambda: self.result(second.listing_id))
        self.assertEqual(results.count('full'), 1)
        self.assertEqual(Favorite.objects.count(), 200)

    def test_waiting_add_rechecks_active_account(self):
        def attempt():
            try:
                self.add()
            except PermissionDenied:
                return 'inactive'
        results = self.ordered(lambda: User.objects.filter(pk=self.other.pk).update(is_active=False),
                               attempt, [self.other.pk])
        self.assertEqual(results[1], 'inactive')
        self.assertFalse(Favorite.objects.exists())

    def test_authenticated_user_has_saved_searches_screen(self):
        self.client.force_login(self.owner)
        response = self.client.get('/kayitli-aramalarim/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kayıtlı Aramalarım')
        self.assertIn('no-store', response['Cache-Control'])
