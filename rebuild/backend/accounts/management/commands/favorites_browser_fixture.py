"""Fresh reserved developer-only records; secrets arrive over stdin and are never echoed."""
import json
import re
import socket
import sys
from pathlib import Path

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.http import QueryDict
from django.utils import timezone

from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.favorites import add_favorite
from listings.models import Listing, ListingRevision
from listings.search.parsing import parse_search_spec, search_spec_to_dict
from notifications.services import save_search

MODES = ('desktop', 'mobile', 'nojs')


class Command(BaseCommand):
    help = 'Create fresh synthetic favorites/search UI data on the isolated developer only.'

    def handle(self, *args, **options):
        if (not settings.DEBUG or connection.vendor != 'postgresql'
                or not Site.objects.filter(pk=settings.SITE_ID, domain='localhost:8089').exists()
                or '/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media '
                not in Path('/proc/self/mountinfo').read_text()):
            raise CommandError('Developer fixture guard refused.')
        try:
            data = json.loads(sys.stdin.read(4096))
            if (set(data) != {'run', 'passwords', 'db_address'}
                    or not isinstance(data['run'], str) or not re.fullmatch('[a-f0-9]{16}', data['run'])
                    or not isinstance(data['passwords'], dict) or set(data['passwords']) != set(MODES)
                    or any(not isinstance(value, str) or not 32 <= len(value) <= 128 for value in data['passwords'].values())):
                raise ValueError
            with connection.cursor() as cursor:
                cursor.execute('SELECT current_database(), host(inet_server_addr())')
                database, address = cursor.fetchone()
            if (database != settings.DATABASES['default']['NAME'] or address != data['db_address']
                    or address != socket.gethostbyname(settings.DATABASES['default']['HOST'])):
                raise ValueError
            prefix = 'favorites-' + data['run']
            if User.objects.filter(email__startswith=prefix).exists() or Category.objects.filter(slug=prefix).exists():
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise CommandError('Invalid or reused developer fixture.') from None
        with transaction.atomic():
            seller = User.objects.create_user(email=prefix + '-seller@browser.example.test', password=None)
            users = {mode: User.objects.create_user(email=prefix + '-' + mode + '@browser.example.test',
                                                    password=data['passwords'][mode]) for mode in MODES}
            for user in users.values():
                EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
            category = Category.objects.create(name='Sentetik favori kabulü', slug=prefix)
            schema = AttributeSchema.objects.create(category=category, version=1, definition={'fields': {}})
            listings = []
            for number in range(13):
                listing = Listing.objects.create(owner=seller, lifecycle='live', first_published_at=timezone.now())
                revision = ListingRevision.objects.create(listing=listing, status='approved', category=category,
                    attribute_schema=schema, schema_version=1, title=f'Sentetik favori {number:02}',
                    description='Yalnız geliştirici kabul verisi.', price='1234.50', currency='TRY', location='Şişli')
                listing.public_revision = revision
                listing.save(update_fields=['public_revision'])
                listings.append(listing)
            for user in users.values():
                for number, listing in enumerate(listings[:12]):
                    add_favorite(actor=user, listing_id=listing.pk)
                    params = QueryDict('', mutable=True)
                    params['category'] = str(category.pk)
                    params['q'] = f'Sentetik {number:02}'
                    save_search(actor=user, name=f'Sentetik kayıt {number:02}',
                                payload=search_spec_to_dict(parse_search_spec(params)))
            # Only this run's new row changes; it exercises the content-free placeholder.
            Listing.objects.filter(pk=listings[0].pk).update(lifecycle='closed')
        self.stdout.write(json.dumps({'category': category.pk, 'listing': str(listings[-1].pk),
                                      'createdUsers': 4, 'createdListings': 13}))
