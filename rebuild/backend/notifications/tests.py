import json
from copy import deepcopy
from urllib.parse import urlsplit

from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import QueryDict
from django.test import Client, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import User
from catalog.models import AttributeSchema
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers
from listings.search.parsing import parse_search_spec, search_spec_to_dict
from listings.tests.test_drafts import DraftFixtures
from notifications.models import SavedSearch
from notifications.services import save_search, rename_search, delete_search


class SavedFixtures(DraftFixtures):
    def setUp(self):
        super().setUp()
        for user in (self.owner, self.other):
            EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)

    def payload(self, query='q=İstanbul&currency=eur&price_min=10.50&page=9&unrelated=discard'):
        return search_spec_to_dict(parse_search_spec(QueryDict(query)))

    def save(self, query='q=İstanbul', name='Aramam'):
        return save_search(actor=self.owner, name=name, payload=self.payload(query))[0]


class SavedSearchTests(SavedFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def post(self, payload=None, name='Aramam', **extra):
        return self.client.post('/kayitli-aramalarim/kaydet/',
            {'name': name, 'spec': json.dumps(self.payload() if payload is None else payload), **extra})

    def test_canonical_replay_preserves_original_name_and_excludes_page(self):
        self.assertEqual(self.post(name='İlk ad').status_code, 302)
        self.assertEqual(self.post(self.payload('currency=EUR&q=%20İstanbul%20&price_min=10.5&page=1'), name='Yeni ad').status_code, 302)
        row = SavedSearch.objects.get()
        self.assertEqual(row.name, 'İlk ad')
        self.assertEqual(row.spec['currency'], 'EUR')
        self.assertEqual(row.spec['price_min'], '10.50')
        self.assertNotIn('page', row.spec)
        self.assertNotIn('unrelated', row.spec)
        response = self.client.get(f'/kayitli-aramalarim/{row.pk}/ac/')
        params = QueryDict(urlsplit(response.url).query)
        self.assertEqual(params['q'], 'İstanbul')
        self.assertNotIn('page', params)

    def test_name_trim_length_empty_and_escape(self):
        for name in ('', ' ', 'x' * 81):
            self.assertEqual(self.post(name=name).status_code, 400)
        self.assertEqual(self.post(name='x' * 80).status_code, 302)
        row = SavedSearch.objects.get()
        response = self.client.post(f'/kayitli-aramalarim/{row.pk}/ad/', {'name': ' <script>bad</script> '})
        self.assertEqual(response.status_code, 302)
        response = self.client.get('/kayitli-aramalarim/')
        self.assertContains(response, '&lt;script&gt;bad&lt;/script&gt;')
        self.assertNotContains(response, '<script>bad</script>')

    def test_private_ownership_every_endpoint_and_body_owner_ignored(self):
        self.post(user=self.other.pk, next='//evil.test/')
        row = SavedSearch.objects.get()
        self.assertEqual(row.user_id, self.owner.pk)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/kayitli-aramalarim/'), row.name)
        for action, method in (('ac', 'get'), ('ad', 'get'), ('ad', 'post'), ('sil', 'post')):
            response = getattr(self.client, method)(f'/kayitli-aramalarim/{row.pk}/{action}/', {'name': 'Stolen'})
            self.assertEqual(response.status_code, 404)
            self.assertIn('no-store', response['Cache-Control'])
        self.assertTrue(SavedSearch.objects.filter(pk=row.pk).exists())

    def test_writes_require_auth_active_verified_and_csrf(self):
        self.assertEqual(Client().post('/kayitli-aramalarim/kaydet/').status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post('/kayitli-aramalarim/kaydet/').status_code, 403)
        EmailAddress.objects.filter(user=self.owner).update(verified=False)
        self.assertEqual(self.post().status_code, 403)
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertEqual(self.post().status_code, 302)
        self.assertFalse(SavedSearch.objects.exists())

    def test_no_get_mutations_and_fixed_redirect(self):
        self.assertEqual(self.client.get('/kayitli-aramalarim/kaydet/').status_code, 405)
        row = self.save()
        before = deepcopy(row.spec)
        self.assertEqual(self.client.get(f'/kayitli-aramalarim/{row.pk}/sil/').status_code, 405)
        self.client.get(f'/kayitli-aramalarim/{row.pk}/ad/?name=changed')
        row.refresh_from_db()
        self.assertEqual(row.name, 'Aramam')
        response = self.client.post(f'/kayitli-aramalarim/{row.pk}/ad/',
                                    {'name': 'Yeni', 'next': 'https://evil.test', 'spec': '{}'})
        self.assertEqual(response.url, '/kayitli-aramalarim/')
        row.refresh_from_db()
        self.assertEqual(row.spec, before)
        self.assertEqual(self.client.post(f'/kayitli-aramalarim/{row.pk}/sil/').status_code, 302)
        self.assertFalse(SavedSearch.objects.exists())

    def test_corrupt_or_unsupported_stored_spec_never_queries_results(self):
        row = self.save()
        cases = [{}, [], None, {**row.spec, 'version': 2}, {**row.spec, 'price_min': 'NaN'},
                 {**row.spec, 'unknown': True}, {**row.spec, 'attributes': [{'key': 'x'}]}]
        for payload in cases:
            # JSON null rather than SQL NULL preserves the NOT NULL column contract.
            from django.db.models import Value, JSONField
            SavedSearch.objects.filter(pk=row.pk).update(spec=Value(payload, output_field=JSONField()))
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(f'/kayitli-aramalarim/{row.pk}/ac/')
            self.assertEqual(response.status_code, 400)
            self.assertContains(response, 'Sonuç sorgusu çalıştırılmadı', status_code=400)
            self.assertFalse(any('"listings_listing"' in q['sql'] or '"listings_listingrevision"' in q['sql'] for q in queries))

    def test_invalid_post_never_stores_or_queries_listing(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.post({})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SavedSearch.objects.exists())
        self.assertFalse(any('"listings_listing"' in q['sql'] for q in queries))

    def test_noncanonical_stored_spec_cannot_drop_attribute_filters(self):
        row = self.save(f'category={self.category.pk}&schema={self.schema.pk}&schema_version=1&a.area.min=82.5')
        damaged = deepcopy(row.spec)
        damaged['attributes'] = []
        SavedSearch.objects.filter(pk=row.pk).update(spec=damaged)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(f'/kayitli-aramalarim/{row.pk}/ac/')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('Location', response)
        self.assertFalse(any('"listings_listing"' in q['sql'] for q in queries))

    def test_attribute_decimal_and_frozen_schemas_roundtrip(self):
        query = f'category={self.category.pk}&schema={self.schema.pk}&schema_version=1&a.area.min=82.500&a.electric.eq=false&q=Şişli&currency=try&price_max=1234.50'
        row = self.save(query)
        original = deepcopy(row.spec)
        AttributeSchema.objects.create(category=self.category, version=2, definition=self.schema.definition)
        response = self.client.get(f'/kayitli-aramalarim/{row.pk}/ac/')
        reopened = search_spec_to_dict(parse_search_spec(QueryDict(urlsplit(response.url).query)))
        self.assertEqual(reopened, original)
        self.assertEqual(reopened['resolved_schemas'], [{'id': self.schema.pk, 'category_id': self.category.pk, 'version': 1}])
        self.assertEqual(reopened['attributes'][0]['value'], '82.5')
        actual = self.client.get(response.url)
        self.assertTrue(actual.context['search_valid'])
        self.assertEqual(search_spec_to_dict(actual.context['search_spec']), original)

    def test_capacity_dedup_rename_delete_without_staff_exemption(self):
        rows = [self.save(f'q=arama{index}') for index in range(20)]
        self.assertEqual(self.save('q=arama0', name='Different').pk, rows[0].pk)
        for staff in (False, True):
            User.objects.filter(pk=self.owner.pk).update(is_staff=staff)
            with self.assertRaises(ValidationError):
                self.save('q=extra')
        rename_search(actor=self.owner, search_id=rows[0].pk, name='Yeni ad')
        delete_search(actor=self.owner, search_id=rows[0].pk)
        self.save('q=extra')
        self.assertEqual(SavedSearch.objects.count(), 20)

    def test_list_is_sql_paginated_stable_and_does_not_match_results(self):
        self.save('q=first')
        with CaptureQueriesContext(connection) as one:
            self.client.get('/kayitli-aramalarim/')
        for index in range(19):
            self.save(f'q=term{index}')
        SavedSearch.objects.all().update(created_at=timezone.now())
        with CaptureQueriesContext(connection) as many:
            response = self.client.get('/kayitli-aramalarim/')
        self.assertEqual(len(one), len(many))
        self.assertTrue(any('LIMIT 12' in q['sql'] for q in many))
        self.assertFalse(any('"listings_listing"' in q['sql'] for q in many))
        self.assertEqual([row.pk for row in response.context['page_obj']], list(SavedSearch.objects.order_by('-pk').values_list('pk', flat=True)[:12]))
        self.assertContains(response, '?page=2')

    def test_search_save_form_only_for_valid_results_and_no_page_in_payload(self):
        response = self.client.get('/?q=İstanbul&page=4')
        self.assertContains(response, 'Aramayı kaydet')
        self.assertNotIn('page', json.loads(response.context['save_search_form']['spec'].value()))
        invalid = self.client.get('/?currency=INVALID')
        self.assertNotContains(invalid, 'action="/kayitli-aramalarim/kaydet/"')


class SavedSearchConcurrencyTests(PostgresLimitWorkers, SavedFixtures, TransactionTestCase):
    def attempt(self, query):
        try:
            return self.save(query).pk
        except ValidationError:
            return 'full'

    def test_parallel_same_canonical_record(self):
        results = self.race(lambda: self.save('q=İstanbul').pk, lambda: self.save('q=%20İstanbul%20').pk)
        self.assertEqual(results[0], results[1])
        self.assertEqual(SavedSearch.objects.count(), 1)

    def test_parallel_last_slot_distinct_criteria(self):
        for index in range(19):
            self.save(f'q=term{index}')
        results = self.race(lambda: self.attempt('q=twentieth'), lambda: self.attempt('q=twentyfirst'))
        self.assertEqual(results.count('full'), 1)
        self.assertEqual(SavedSearch.objects.count(), 20)

    def test_waiting_replay_preserves_committed_name(self):
        results = self.ordered(lambda: self.save(name='First').pk, lambda: self.save(name='Second').pk, [self.owner.pk])
        self.assertEqual(results[0], results[1])
        self.assertEqual(SavedSearch.objects.get().name, 'First')
