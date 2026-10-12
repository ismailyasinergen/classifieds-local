"""Synthetic conversations acceptance, guarded to the separate developer runtime."""
import json
import re
import socket
import sys
from pathlib import Path
from datetime import timedelta
from uuid import uuid4

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import override_settings
from django.utils import timezone

from accounts.models import User
from catalog.models import AttributeSchema, Category
from conversations.models import Conversation, Participant
from conversations.queries import inbox_conversations
from conversations.services import send_message, start_conversation
from listings.models import Listing, ListingRevision


class Command(BaseCommand):
    help = "Create or mutate only fresh reserved synthetic conversations on developer8089."

    def handle(self, *args, **options):
        # A public Site alone is insufficient: require the developer media mount,
        # PostgreSQL identity and the DB address independently inspected by the driver.
        mount = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "
        if (not settings.DEBUG or not Site.objects.filter(
                pk=settings.SITE_ID, domain="localhost:8089").exists()
                or mount not in Path("/proc/self/mountinfo").read_text()
                or connection.vendor != "postgresql"):
            raise CommandError("Conversations fixture requires the isolated DEBUG developer runtime.")
        try:
            data = json.loads(sys.stdin.read(8192))
            run = data["run"]
            action = data["action"]
            if (not isinstance(run, str) or not re.fullmatch(r"[a-f0-9]{16}", run)
                    or action not in ("create", "close", "paginate", "inspect")
                    or not isinstance(data["db_address"], str)):
                raise ValueError()
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), host(inet_server_addr())")
                database, address = cursor.fetchone()
            if (database != settings.DATABASES["default"]["NAME"]
                    or address != data["db_address"]
                    or address != socket.gethostbyname(settings.DATABASES["default"]["HOST"])):
                raise ValueError()
            allowed = {"run", "action", "db_address", "passwords"} if action == "create" else {"run", "action", "db_address"}
            if set(data) != allowed:
                raise ValueError()
            prefix = f"conversations-{run}"
            emails = {role: f"{prefix}-{role}@browser.example.test"
                      for role in ("buyer", "seller", "newcomer")}
            with transaction.atomic():
                if action == "create":
                    passwords = data["passwords"]
                    if (set(passwords) != set(emails)
                            or any(not isinstance(value, str) or not 24 <= len(value) <= 128 for value in passwords.values())
                            or User.objects.filter(email__in=emails.values()).exists()
                            or Category.objects.filter(slug=prefix).exists()):
                        raise ValueError()
                    users = {role: User.objects.create_user(email=email, password=passwords[role])
                             for role, email in emails.items()}
                    for user in users.values():
                        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
                    category = Category.objects.create(name="Sentetik görüşmeler", slug=prefix)
                    schema = AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
                    listings = []
                    # Only fresh reserved synthetic construction exceeds contact capacity.
                    with override_settings(PILOT_NEW_CONTACTS_PER_HOUR=13):
                        for number in range(14):
                            listing = Listing.objects.create(owner=users["seller"])
                            revision = ListingRevision.objects.create(
                                listing=listing, category=category, attribute_schema=schema, schema_version=1,
                                status="approved", title=f"Sentetik görüşme {number:02}",
                                description="Yalnız geliştirici tarayıcı kabul verisi. Gerçek satış değildir.",
                                location="İstanbul", price="100.00", currency="TRY")
                            listing.lifecycle = "live"
                            listing.public_revision = revision
                            listing.save()
                            listings.append(listing)
                            if number:
                                start_conversation(actor=users["buyer"], listing_id=listing.pk,
                                                   body=f"Sentetik kutu {number}", client_token=uuid4())
                    # Preserve all 13 inbox rows, but leave a genuine final slot at
                    # the live default10. Only four just-created reserved contacts
                    # are historical; last_message_at and messages stay unchanged.
                    historical = Conversation.objects.filter(
                        initiator=users["buyer"], recipient=users["seller"],
                        listing_id__in=[item.pk for item in listings[1:5]])
                    if historical.update(created_at=timezone.now() - timedelta(hours=2)) != 4:
                        raise ValueError()
                    result = {"run": run, "listing": str(listings[0].pk), "threads": 13,
                              "guard": {"debug": True, "site": "localhost:8089",
                                        "project_mount": "classifieds-rebuild-dev_rebuild_media",
                                        "database_verified": True}}
                else:
                    users = {role: User.objects.get(email=email) for role, email in emails.items()}
                    category = Category.objects.get(slug=prefix)
                    listing = Listing.objects.get(owner=users["seller"],
                        public_revision__category=category, public_revision__title="Sentetik görüşme 00")
                    conversation = Conversation.objects.get(listing=listing, initiator=users["buyer"],
                                                             recipient=users["seller"])
                    if action == "close":
                        listing.lifecycle = "closed"
                        listing.save(update_fields=["lifecycle"])
                    elif action == "paginate":
                        for number in range(31):
                            send_message(actor=users["seller"], conversation_id=conversation.pk,
                                         body=f"Sentetik geçmiş {number:02}", client_token=uuid4())
                    result = {"run": run, "conversation": str(conversation.pk),
                              "last_sequence": Conversation.objects.get(pk=conversation.pk).last_sequence,
                              "buyer_read": Participant.objects.get(conversation=conversation, user=users["buyer"]).last_read_sequence,
                              "buyer_unread": inbox_conversations(actor=users["buyer"]).filter(pk=conversation.pk, has_unread=True).exists()}
        except Exception:
            # Submitted data and credentials never enter diagnostics.
            raise CommandError("Guarded synthetic conversations operation failed.") from None
        self.stdout.write(json.dumps(result))
