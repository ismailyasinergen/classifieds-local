from django.test import TestCase, Client
from django.db import connection
from django.test.utils import CaptureQueriesContext
from allauth.account.models import EmailAddress
from notifications.models import NotificationDelivery
from listings.models import Listing
from django.utils import timezone
from notifications.tests import SavedFixtures
from listings.tests.test_publication import PublicationFixtures
from events.models import OutboxEvent
from accounts.tests.mfa_support import authenticate_client


class PublicationMetadataTests(PublicationFixtures, TestCase):
    def test_first_publication_has_versioned_boundary(self):
        revision = self.publish()
        event = OutboxEvent.objects.get(revision=revision)
        self.assertEqual(event.payload.get('notification_version'), 1)
        self.assertIs(event.payload.get('first_publication'), True)
        self.assertGreater(event.payload['publication_boundary'], 0)


class NotificationEntryTests(SavedFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_private_empty_inbox(self):
        response = self.client.get('/bildirimlerim/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Henüz bildiriminiz yok')
        self.assertIn('no-store', response['Cache-Control'])

    def test_enable_is_explicit_idempotent_post(self):
        row = self.save()
        response = self.client.post(f'/kayitli-aramalarim/{row.pk}/bildirim-ac/')
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertTrue(row.notifications_enabled)
        boundary = row.notification_boundary
        self.client.post(f'/kayitli-aramalarim/{row.pk}/bildirim-ac/')
        row.refresh_from_db()
        self.assertEqual(row.notification_boundary, boundary)

    def notice(self):
        revision = self.approved()
        event = OutboxEvent.objects.create(revision=revision, event_type=OutboxEvent.Type.REVISION_PUBLISHED)
        return NotificationDelivery.objects.create(event=event, listing=revision.listing, recipient=self.owner)

    def test_ownership_csrf_auth_and_get_no_mutation(self):
        row = self.save()
        self.assertEqual(self.client.get(f'/kayitli-aramalarim/{row.pk}/bildirim-ac/').status_code, 405)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(f'/kayitli-aramalarim/{row.pk}/bildirim-ac/').status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f'/kayitli-aramalarim/{row.pk}/bildirim-ac/').status_code, 404)
        self.assertEqual(Client().get('/bildirimlerim/').status_code, 302)
        self.client.force_login(self.owner)
        EmailAddress.objects.filter(user=self.owner).update(verified=False)
        self.assertEqual(self.client.post(f'/kayitli-aramalarim/{row.pk}/bildirim-ac/').status_code, 403)
        self.assertEqual(self.client.get('/bildirimlerim/').status_code, 403)

    def test_read_archive_idempotency_and_ownership(self):
        row = self.notice()
        base = f'/kayitli-aramalarim/bildirimler/{row.pk}/'
        for action in ['okundu', 'arsiv']:
            self.assertEqual(self.client.get(base+action+'/').status_code, 405)
        self.client.get('/bildirimlerim/')
        row.refresh_from_db()
        self.assertIsNone(row.read_at)
        for action, field in [('okundu', 'read_at'), ('arsiv', 'archived_at')]:
            self.assertEqual(self.client.post(base+action+'/', {'next': '//evil.test'}).url, '/bildirimlerim/')
            row.refresh_from_db()
            first = getattr(row, field)
            self.client.post(base+action+'/')
            row.refresh_from_db()
            self.assertEqual(first, getattr(row, field))
        self.assertContains(self.client.get('/bildirimlerim/'), 'Henüz bildiriminiz yok')
        self.assertTrue(NotificationDelivery.objects.filter(pk=row.pk).exists())
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(base+'okundu/').status_code, 404)

    def test_hidden_content_and_html_escaping(self):
        row = self.notice()
        row.listing.public_revision.title = '<script>PRIVATE_CANARY</script>'
        row.listing.public_revision.save(update_fields=['title'])
        response = self.client.get('/bildirimlerim/')
        self.assertContains(response, '&lt;script&gt;PRIVATE_CANARY&lt;/script&gt;')
        Listing.objects.filter(pk=row.listing_id).update(lifecycle='closed')
        response = self.client.get('/bildirimlerim/')
        self.assertContains(response, 'İlan şu anda kullanılamıyor')
        self.assertNotContains(response, 'PRIVATE_CANARY')
        self.assertIn('private', response['Cache-Control'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_sql_pagination_stable_queries_and_private_counter(self):
        self.notice()
        with CaptureQueriesContext(connection) as one:
            self.client.get('/bildirimlerim/')
        for _ in range(12):
            self.notice()
        NotificationDelivery.objects.update(created_at=timezone.now())
        with CaptureQueriesContext(connection) as many:
            response = self.client.get('/bildirimlerim/')
        self.assertEqual(len(one), len(many))
        self.assertTrue(any('LIMIT 12' in q['sql'] for q in many))
        self.assertEqual(len(response.context['page_obj']), 12)
        self.assertContains(response, '13 okunmamış')
        self.assertEqual([r.pk for r in response.context['page_obj']], list(NotificationDelivery.objects.order_by('-pk').values_list('pk', flat=True)[:12]))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/bildirimlerim/'), '13 okunmamış')

    def test_public_counter_requires_verified_email_and_current_role_mfa(self):
        row = self.notice()
        paths = ['/', f'/ilanlar/{row.listing_id}/', '/accounts/security/']
        for staff, verified in [(False, False), (True, True)]:
            self.owner.is_staff = staff
            self.owner.save(update_fields=['is_staff'])
            EmailAddress.objects.filter(user=self.owner).update(verified=verified)
            self.client.force_login(self.owner)
            for path in paths:
                with self.subTest(staff=staff, path=path):
                    with CaptureQueriesContext(connection) as queries:
                        response = self.client.get(path)
                    self.assertFalse('unread_notification_count' in response.context)
                    self.assertFalse(any('notifications_notificationdelivery' in q['sql'] for q in queries))
        authenticate_client(self.client, self.owner)
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.context['unread_notification_count'], 1)
            self.assertIn('private', response['Cache-Control'])
            self.assertIn('no-store', response['Cache-Control'])
