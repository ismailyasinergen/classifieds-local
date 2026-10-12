"""Only fresh developer synthetic accounts. Private transport; no task dispatch."""
import json
import re
import sys

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core import signing
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.management.commands.mfa_browser_fixture import _guard
from accounts.models import User
from catalog.models import AttributeSchema, Category
from events.models import EventConsumption, OutboxEvent
from listings.publication import submit_revision
from listings.services import create_listing_draft
from notifications.consumer import CONSUMER
from notifications.models import NotificationDelivery

MODES = ('desktop', 'mobile', 'nojs')
SALT = 'phase12.synthetic.browser.v1'


class Command(BaseCommand):
    def handle(self, **options):
        try:
            raw = sys.stdin.read(8193)
            if len(raw) > 8192:
                raise ValueError
            data = json.loads(raw)
            _guard(data)
            if not settings.IN_APP_NOTIFICATIONS_ENABLED or not re.fullmatch('[a-f0-9]{16}', data['run']):
                raise ValueError
            action = data['action']
            if action == 'inspect':
                if set(data) != {'action', 'run', 'db_address', 'receipt'}:
                    raise ValueError
                binding = signing.loads(data['receipt'], salt=SALT, max_age=7200)
                if binding['run'] != data['run']:
                    raise ValueError
                events = OutboxEvent.objects.filter(revision_id__in=binding['revisions'])
                jobs = EventConsumption.objects.filter(event__in=events, consumer=CONSUMER)
                deliveries = NotificationDelivery.objects.filter(event__in=events, recipient_id__in=binding['users'])
                self.stdout.write(json.dumps({'events': events.count(), 'completed': jobs.filter(status='completed').count(),
                    'failed': jobs.filter(status__in=['failed', 'retry']).count(), 'deliveries': deliveries.count(),
                    'archived': deliveries.exclude(archived_at=None).count()}))
                return
            if action != 'create' or set(data) != {'action', 'run', 'db_address', 'passwords'}:
                raise ValueError
            if set(data['passwords']) != {*MODES, 'reviewer'} or any(not isinstance(v, str) or not 32 <= len(v) <= 128 for v in data['passwords'].values()):
                raise ValueError
            prefix = 'notifications-' + data['run']
            if User.objects.filter(email__startswith=prefix).exists() or Category.objects.filter(slug=prefix).exists():
                raise ValueError
        except (ValueError, TypeError, KeyError, signing.BadSignature):
            raise CommandError('notification_fixture_refused') from None
        with transaction.atomic():
            seller = User.objects.create_user(prefix+'-seller@browser.example.test', password=None)
            users = {mode: User.objects.create_user(prefix+'-'+mode+'@browser.example.test', data['passwords'][mode]) for mode in (*MODES, 'reviewer')}
            for user in [seller, *users.values()]:
                EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
            users['reviewer'].user_permissions.add(Permission.objects.get(content_type__app_label='listings', codename='review_listingrevision'))
            category = Category.objects.create(name='Sentetik bildirim kabulü', slug=prefix)
            AttributeSchema.objects.create(category=category, version=1, definition={'fields': {}})
            revisions = {}
            for mode in MODES:
                revisions[mode] = []
                for number in range(2):
                    revision = create_listing_draft(actor=seller, category_id=category.pk, content={
                        'title': f'Sentetik bildirim {mode} {number}', 'description': 'Yalnız yeni geliştirici kabul kaydı.',
                        'price': '1234.50', 'currency': 'EUR', 'location': 'Şişli', 'attributes': {}})
                    submit_revision(actor=seller, revision_id=revision.pk)
                    revisions[mode].append(revision.pk)
            binding = {'run': data['run'], 'users': [users[m].pk for m in MODES], 'revisions': [pk for ids in revisions.values() for pk in ids]}
        self.stdout.write(json.dumps({'category': category.pk, 'revisions': revisions,
            'receipt': signing.dumps(binding, salt=SALT), 'createdUsers': 5, 'createdListings': 6}))
