"""Fresh developer-only Phase 16 synthetic fixtures; never print credentials."""
import json
import re
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from allauth.account.models import EmailAddress
from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision
from promotions.models import PromotionProduct, Purchase, Activation, DemoEvidence
from promotions.services import require_demo


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--verify', action='store_true')
        parser.add_argument('--hide', action='store_true')

    def handle(self, *args, **options):
        require_demo()
        try:
            data=json.loads(sys.stdin.read(4096))
            run=data['run']
            if not isinstance(run,str) or not re.fullmatch('[a-f0-9]{16}',run):
                raise ValueError
            prefix='promotions-'+run
            users=User.objects.filter(email__startswith=prefix+'-',email__endswith='@browser.example.test')
            if options['verify'] or options['hide']:
                if set(data)!={'run'} or users.count()!=3:
                    raise ValueError
                if options['hide']:
                    listing=Listing.objects.get(owner__email=prefix+'-desktop@browser.example.test',public_revision__title='Demo desktop '+run)
                    listing.lifecycle='closed'
                    listing.save(update_fields=['lifecycle'])
                purchases=Purchase.objects.filter(owner__in=users)
                self.stdout.write(json.dumps({'purchases':purchases.count(),'activations':Activation.objects.filter(purchase__in=purchases).count(),'evidence':DemoEvidence.objects.filter(purchase__in=purchases).count()}))
                return
            if set(data)!={'run','passwords'} or set(data['passwords'])!={'desktop','mobile','nojs'}:
                raise ValueError
            if any(not isinstance(p,str) or not 32<=len(p)<=128 for p in data['passwords'].values()):
                raise ValueError
            if users.exists() or Category.objects.filter(slug=prefix).exists():
                raise ValueError
        except (ValueError,TypeError,KeyError):
            raise CommandError('Invalid or reused Phase 16 fixture.') from None
        result={'run':run,'users':{}}
        with transaction.atomic():
            category=Category.objects.create(name='Sentetik demo '+run,slug=prefix)
            schema=AttributeSchema.objects.create(category=category,version=1,definition={'fields':{}})
            product=PromotionProduct.objects.create(name='Sentetik 24 saat '+run,amount=Decimal('10.00'),currency='TRY',duration_seconds=86400,placement='search',terms_version='demo-v1')
            result['product']=product.pk
            result['category']=category.pk
            for mode,password in data['passwords'].items():
                email=prefix+'-'+mode+'@browser.example.test'
                user=User.objects.create_user(email=email,password=password)
                EmailAddress.objects.create(user=user,email=email,verified=True,primary=True)
                rows=[]
                for visible in (True,False):
                    listing=Listing.objects.create(owner=user,lifecycle='live' if visible else 'closed',first_published_at=timezone.now())
                    revision=ListingRevision.objects.create(listing=listing,status='approved',category=category,attribute_schema=schema,schema_version=1,title=('Demo '+mode if visible else 'Gizli demo '+mode)+' '+run,description='Yalnız sentetik geliştirici kabulü',price=Decimal('123'),currency='TRY',location='Berlin')
                    listing.public_revision=revision
                    listing.save(update_fields=['public_revision'])
                    rows.append(str(listing.pk))
                result['users'][mode]={'email':email,'listing':rows[0],'hidden':rows[1]}
        self.stdout.write(json.dumps(result))