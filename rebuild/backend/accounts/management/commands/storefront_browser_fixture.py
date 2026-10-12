"""New developer-only synthetic accounts; credentials use stdin only."""
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
from django.utils import timezone
from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision

MODES = ("desktop", "mobile", "nojs")


class Command(BaseCommand):
    help = "Fresh developer-only storefront browser fixtures. Never resets existing rows."

    def handle(self, *args, **options):
        if (not settings.DEBUG or connection.vendor != "postgresql"
                or not Site.objects.filter(pk=settings.SITE_ID, domain="localhost:8089").exists()
                or "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "
                not in Path("/proc/self/mountinfo").read_text()):
            raise CommandError("Developer fixture guard refused.")
        try:
            data = json.loads(sys.stdin.read(4096))
            if (set(data) != {"run", "passwords", "db_address"}
                    or not isinstance(data["run"], str) or not re.fullmatch("[a-f0-9]{16}", data["run"])
                    or not isinstance(data["passwords"], dict) or set(data["passwords"]) != set(MODES)
                    or any(not isinstance(v, str) or not 32 <= len(v) <= 128 for v in data["passwords"].values())):
                raise ValueError
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), host(inet_server_addr())")
                database, address = cursor.fetchone()
            if (database != settings.DATABASES["default"]["NAME"] or address != data["db_address"]
                    or address != socket.gethostbyname(settings.DATABASES["default"]["HOST"])):
                raise ValueError
            prefix = "storefront-" + data["run"]
            if User.objects.filter(email__startswith=prefix).exists() or Category.objects.filter(slug=prefix).exists():
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise CommandError("Invalid or reused developer fixture.") from None
        with transaction.atomic():
            users = {mode: User.objects.create_user(email=prefix+"-"+mode+"@browser.example.test",
                password=data["passwords"][mode]) for mode in MODES}
            for user in users.values():
                EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
            category = Category.objects.create(name="Sentetik vitrin kabulü", slug=prefix)
            schema = AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
            for mode, user in users.items():
                for number in range(14):
                    listing = Listing.objects.create(owner=user,
                        lifecycle="live" if number < 13 else "closed", first_published_at=timezone.now())
                    revision = ListingRevision.objects.create(listing=listing, status="approved", category=category,
                        attribute_schema=schema, schema_version=1,
                        title=f"Sentetik {mode} ilan {number:02}" if number < 13 else "Gizli vitrin canary",
                        description="Yalnız geliştirici kabul verisi.", price="1234.50", currency="TRY", location="Şişli")
                    listing.public_revision = revision
                    listing.save(update_fields=["public_revision"])
        self.stdout.write(json.dumps({"createdUsers": 3, "createdListings": 42, "category": category.pk}))
