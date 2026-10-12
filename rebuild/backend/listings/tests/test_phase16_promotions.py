from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from uuid import uuid4
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.utils import timezone
from django.db import transaction
from listings.models import Listing
from listings.search.parsing import parse_search_spec
from listings.tests.test_drafts import DraftFixtures


class DeveloperMountFixture:
    def setUp(self):
        super().setUp()
        self.mountinfo = Mock(spec=Path)
        self.mountinfo.read_text.return_value = (
            "42 31 0:40 /volumes/classifieds-rebuild-dev_rebuild_media/_data "
            "/var/lib/classifieds/media rw,relatime - ext4 /dev/test rw\n"
        )

        def service_path(*args, **kwargs):
            path = Path(*args, **kwargs)
            return self.mountinfo if path == Path('/proc/self/mountinfo') else path

        # Patch only this module's boundary; worker threads finish before cleanup.
        self.mount_patch = patch('promotions.services.Path', side_effect=service_path)
        self.addCleanup(self.mount_patch.stop)
        self.mount_patch.start()


@override_settings(PROMOTIONS_DEMO_ENABLED=True, DEPLOYMENT_ENVIRONMENT='developer')
class PromotionTests(DeveloperMountFixture, DraftFixtures, TestCase):
    def setUp(self):
        super().setUp()
        try:
            self.service = import_module('promotions.services')
            self.models = import_module('promotions.models')
        except ModuleNotFoundError as error:
            if error.name not in {'promotions', 'promotions.services', 'promotions.models'}:
                raise
            self.fail('Phase 16 demo promotions service is not implemented')
        Site.objects.update_or_create(pk=1, defaults={'domain':'localhost:8089','name':'Developer'})
        for user in (self.owner, self.other):
            EmailAddress.objects.create(user=user,email=user.email,verified=True,primary=True)
        self.listing = self.approved().listing
        self.product = self.models.PromotionProduct.objects.create(name='Sentetik demo', amount=Decimal('10.00'), currency='TRY', duration_seconds=86400, placement='search', terms_version='demo-v1')
        self.key = uuid4()

    def purchase(self, **kwargs):
        return self.service.purchase_demo(actor=kwargs.pop('actor',self.owner),listing_id=kwargs.pop('listing_id',self.listing.pk),product_id=kwargs.pop('product_id',self.product.pk),key=kwargs.pop('key',self.key),**kwargs)

    def activate(self, purchase=None, **kwargs):
        purchase = purchase or self.purchase()
        return self.service.complete_demo(actor=kwargs.pop('actor',self.owner),purchase_id=purchase.pk,**kwargs)

    def test_snapshot_idempotency_and_demo_evidence(self):
        purchase = self.purchase()
        self.product.amount=99
        self.product.duration_seconds=10
        self.product.save()
        again=self.purchase()
        self.assertEqual(again.pk,purchase.pk)
        self.assertEqual(again.amount,Decimal('10.00'))
        self.assertEqual(again.duration_seconds,86400)
        activation=self.activate(purchase)
        self.assertEqual(self.activate(purchase).pk,activation.pk)
        self.assertEqual(self.models.Activation.objects.count(),1)
        self.assertEqual(self.models.DemoEvidence.objects.get().kind,'demo_no_payment')
        self.assertEqual(activation.ends_at-activation.starts_at,timedelta(days=1))

    def test_conflicting_key_payload(self):
        self.purchase()
        second=self.approved().listing
        with self.assertRaises(ValidationError):
            self.purchase(listing_id=second.pk)

    def test_owner_and_staff_have_no_bypass(self):
        self.service.require_demo()
        for staff in (False,True):
            self.other.is_staff=staff
            self.other.save()
            with self.assertRaisesMessage(PermissionDenied, 'Bu ilanı düzenleme yetkiniz yok.'):
                self.purchase(actor=self.other)
            self.assert_no_promotion_records()

    def assert_no_promotion_records(self):
        for model in (self.models.Purchase, self.models.Activation, self.models.DemoEvidence):
            self.assertEqual(model.objects.count(), 0)

    def test_closed_flag_wrong_environment_and_site(self):
        self.service.require_demo()
        for settings in ({'PROMOTIONS_DEMO_ENABLED':False},{'DEPLOYMENT_ENVIRONMENT':'original'}):
            with override_settings(**settings),self.assertRaises(PermissionDenied):
                self.purchase()
            self.assert_no_promotion_records()
        Site.objects.filter(pk=1).update(domain='127.0.0.1:8088')
        with self.assertRaises(PermissionDenied):
            self.purchase()
        self.assert_no_promotion_records()

    def test_email_and_active_account_are_current(self):
        EmailAddress.objects.filter(user=self.owner).update(verified=False)
        with self.assertRaises(PermissionDenied):
            self.purchase()
        EmailAddress.objects.filter(user=self.owner).update(verified=True)
        type(self.owner).objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.purchase()

    def test_overlap_rollback_and_visibility_recheck(self):
        purchase=self.purchase()
        with patch('promotions.services.Activation.objects.create',side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError):
                self.activate(purchase)
        self.assertEqual(self.models.DemoEvidence.objects.count(),0)
        self.activate(purchase)
        with self.assertRaises(ValidationError):
            self.purchase(key=uuid4())
        self.listing.lifecycle='closed'
        self.listing.save()
        with self.assertRaises(ValidationError):
            self.activate(purchase)

    def test_time_bounds_and_public_filtering(self):
        now=timezone.now()
        with patch('promotions.services.timezone.now',return_value=now):
            activation=self.activate()
        spec=parse_search_spec(QueryDict(''))
        query=lambda at:self.service.sponsored_listings(spec=spec,at=at)
        self.assertFalse(query(now-timedelta(microseconds=1)).exists())
        self.assertTrue(query(now).exists())
        self.assertFalse(query(activation.ends_at).exists())
        self.assertFalse(self.service.sponsored_listings(spec=parse_search_spec(QueryDict('q=nevermatch')),at=now).exists())
        Listing.objects.filter(pk=self.listing.pk).update(lifecycle='paused')
        self.assertFalse(query(now).exists())

    def test_get_has_no_writes_post_csrf_and_private_responses(self):
        from django.test import Client
        self.client.force_login(self.owner)
        url=f'/one-cikar/{self.listing.pk}/'
        response=self.client.get(url)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Demo — gerçek ödeme alınmaz')
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.models.Purchase.objects.count(),0)
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(url,{'product':self.product.pk,'key':str(self.key)}).status_code,403)
        response=self.client.post(url,{'product':self.product.pk,'key':str(self.key),'paid':'true','amount':'0'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.models.Purchase.objects.get().amount,Decimal('10'))
        self.assertEqual(self.models.Activation.objects.count(),0)

    def test_sponsored_section_does_not_change_organic_results(self):
        self.activate()
        response=self.client.get('/')
        self.assertContains(response,'Sponsorlu')
        self.assertEqual(response.context['page_obj'].paginator.count,1)
        self.assertEqual(len(response.context['sponsored']),1)
        self.assertNotContains(self.client.get('/?sort=invalid'),'id="sponsored"')
    def test_evidence_and_purchase_snapshots_are_database_immutable(self):
        from django.db import DatabaseError
        purchase=self.purchase()
        self.activate(purchase)
        for operation in (
            lambda:self.models.Purchase.objects.filter(pk=purchase.pk).update(amount=Decimal('1.00')),
            lambda:self.models.DemoEvidence.objects.all().update(created_at=timezone.now()),
        ):
            with self.assertRaises(DatabaseError),transaction.atomic():
                operation()

    def test_role_mfa_required_for_direct_service_and_http(self):
        self.service.require_demo()
        self.owner.is_staff=True
        self.owner.save()
        with self.assertRaisesMessage(PermissionDenied, 'İki aşamalı doğrulama gerekli.'):
            self.purchase()
        self.assert_no_promotion_records()
        self.client.force_login(self.owner)
        response=self.client.post(f'/one-cikar/{self.listing.pk}/',{'product':self.product.pk,'key':str(self.key)})
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.models.Purchase.objects.count(),0)

    def test_cross_owner_status_and_completion_are_private_404(self):
        purchase=self.purchase()
        self.client.force_login(self.other)
        for path in (f'/one-cikar/islem/{purchase.pk}/',f'/one-cikar/islem/{purchase.pk}/tamamla/'):
            response=self.client.get(path) if path.endswith(str(purchase.pk)+'/') else self.client.post(path)
            self.assertEqual(response.status_code,404)
            self.assertIn('no-store',response['Cache-Control'])

    def test_multiple_pending_purchases_cannot_create_overlapping_rights(self):
        first=self.purchase()
        second=self.purchase(key=uuid4())
        self.activate(first)
        with self.assertRaises(ValidationError):
            self.activate(second)
        self.assertEqual(self.models.DemoEvidence.objects.count(),1)

    def test_sponsored_max_three_first_page_and_stable_order(self):
        now=timezone.now()
        ids=[]
        for i in range(14):
            listing=self.approved().listing
            if i < 4:
                purchase=self.purchase(listing_id=listing.pk,key=uuid4())
                with patch('promotions.services.timezone.now',return_value=now):
                    self.activate(purchase)
                ids.append(listing.pk)
        response=self.client.get('/')
        self.assertEqual([x.pk for x in response.context['sponsored']],list(reversed(ids))[:3])
        self.assertEqual(response.context['page_obj'].paginator.count,15)
        self.assertEqual(len(response.context['page_obj']),12)
        self.assertNotContains(self.client.get('/?page=2'),'id="sponsored"')

    def test_closed_listing_never_republished_and_no_outbox(self):
        from events.models import OutboxEvent
        before=OutboxEvent.objects.count()
        purchase=self.purchase()
        Listing.objects.filter(pk=self.listing.pk).update(lifecycle='closed')
        with self.assertRaises(ValidationError):
            self.activate(purchase)
        self.assertEqual(OutboxEvent.objects.count(),before)
        self.assertEqual(self.models.Activation.objects.count(),0)


    def test_test_named_database_without_developer_mount_is_refused(self):
        self.mountinfo.read_text.return_value = ''
        with self.assertRaises(PermissionDenied):
            self.purchase()
        self.assert_no_promotion_records()

    def test_original_mount_is_refused_without_writes(self):
        self.mountinfo.read_text.return_value = (
            "42 31 0:40 /volumes/classifieds-rebuild_rebuild_media/_data "
            "/var/lib/classifieds/media rw,relatime - ext4 /dev/test rw\n"
        )
        with self.assertRaises(PermissionDenied):
            self.purchase()
        self.assert_no_promotion_records()

    def test_mount_read_error_is_refused_without_writes(self):
        self.mountinfo.read_text.side_effect = OSError('Synthetic mount read failure')
        with self.assertRaises(PermissionDenied):
            self.purchase()
        self.assert_no_promotion_records()

    def test_mount_fixture_preserves_other_reads_and_restores_service_path(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'unrelated.txt'
            path.write_text('unrelated content', encoding='utf-8')
            self.assertEqual(self.service.Path(path).read_text(encoding='utf-8'), 'unrelated content')
            self.assertEqual(path.read_text(encoding='utf-8'), 'unrelated content')
        self.mount_patch.stop()
        self.assertIs(self.service.Path, Path)

    def test_same_http_purchase_retries_after_product_disabled(self):
        self.client.force_login(self.owner)
        url=f'/one-cikar/{self.listing.pk}/'
        payload={'product':self.product.pk,'key':str(self.key)}
        first=self.client.post(url,payload)
        self.assertEqual(first.status_code,302)
        self.product.enabled=False
        self.product.save()
        second=self.client.post(url,payload)
        self.assertEqual(second.status_code,302)
        self.assertEqual(second['Location'],first['Location'])
        self.assertEqual(self.models.Purchase.objects.count(),1)
        self.assertNotEqual(self.client.post(url,dict(payload,key=str(uuid4()))).status_code,302)

    def test_anonymous_direct_calls_are_permission_denied(self):
        from django.contrib.auth.models import AnonymousUser
        with self.assertRaises(PermissionDenied):
            self.purchase(actor=AnonymousUser())

    def test_current_revision_and_moderation_visibility(self):
        from listings.models import ListingRevision
        from moderation.models import Restriction
        activation=self.activate()
        new=ListingRevision.objects.create(listing=self.listing,status='approved',category=self.category,attribute_schema=self.schema,schema_version=1,title='Yeni public amber',description='Current',price=Decimal('5'),currency='TRY')
        Listing.objects.filter(pk=self.listing.pk).update(public_revision=new)
        result=self.service.sponsored_listings(spec=parse_search_spec(QueryDict('q=amber')))
        self.assertEqual(result.get().public_revision_id,new.pk)
        Restriction.objects.create(listing=self.listing,actor=self.other,reason='Synthetic hide',begins_at=timezone.now())
        self.assertFalse(self.service.sponsored_listings(spec=parse_search_spec(QueryDict(''))).exists())

    def test_evidence_delete_is_database_rejected(self):
        from django.db import DatabaseError
        self.activate()
        with self.assertRaises(DatabaseError),transaction.atomic():
            self.models.DemoEvidence.objects.all().delete()

    def test_fixture_rejects_wrong_context_before_writing(self):
        from django.core.management import call_command
        from io import StringIO
        before=type(self.owner).objects.count()
        with override_settings(DEPLOYMENT_ENVIRONMENT='original'),self.assertRaises(PermissionDenied):
            call_command('promotions_browser_fixture',stdout=StringIO())
        self.assertEqual(type(self.owner).objects.count(),before)

from django.test import TransactionTestCase
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers


@override_settings(PROMOTIONS_DEMO_ENABLED=True, DEPLOYMENT_ENVIRONMENT='developer')
class PromotionConcurrencyTests(DeveloperMountFixture, PostgresLimitWorkers, DraftFixtures, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.service=import_module('promotions.services')
        self.models=import_module('promotions.models')
        Site.objects.update_or_create(pk=1,defaults={'domain':'localhost:8089','name':'Developer'})
        EmailAddress.objects.create(user=self.owner,email=self.owner.email,verified=True,primary=True)
        self.listing=self.approved().listing
        self.product=self.models.PromotionProduct.objects.create(name='Concurrent demo',amount=Decimal('10'),currency='TRY',duration_seconds=86400,placement='search',terms_version='demo-v1')
        self.key=uuid4()

    def test_parallel_purchase_and_completion_produce_one_right(self):
        def purchase():
            return self.service.purchase_demo(actor=self.owner,listing_id=self.listing.pk,product_id=self.product.pk,key=self.key).pk
        purchases=self.race(purchase,purchase)
        self.assertEqual(purchases[0],purchases[1])
        def complete():
            return self.service.complete_demo(actor=self.owner,purchase_id=purchases[0]).pk
        activations=self.race(complete,complete)
        self.assertEqual(activations[0],activations[1])
        self.assertEqual(self.models.DemoEvidence.objects.count(),1)
        self.assertEqual(self.models.Activation.objects.count(),1)
