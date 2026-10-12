"""Reserved successful pilot history; never targets the original runtime."""
import json
import re
import socket
import sys
from pathlib import Path
from uuid import uuid4

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import override_settings

from accounts.models import User
from catalog.models import AttributeSchema, Category
from conversations.models import Conversation, Message, Participant
from conversations.services import send_message, start_conversation
from listings.models import Listing, ListingRevision
from listings.publication import submit_revision
from listings.services import create_listing_draft
from moderation.services import approve_revision

DEV_MOUNT = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "
ROLES = ("contact", "message", "creator", "seller", "reviewer")


class Command(BaseCommand):
    help = "Construct or inspect only fresh reserved pilot data on DEBUG developer8089."

    def handle(self, *args, **options):
        if (not settings.DEBUG or connection.vendor != "postgresql"
                or not Site.objects.filter(pk=settings.SITE_ID, domain="localhost:8089").exists()
                or DEV_MOUNT not in Path("/proc/self/mountinfo").read_text()):
            raise CommandError("Pilot fixture requires the isolated DEBUG developer runtime.")
        try:
            defaults = [settings.PILOT_NEW_CONTACTS_PER_HOUR, settings.PILOT_MESSAGES_PER_HOUR,
                        settings.PILOT_NEW_LISTINGS_PER_DAY]
            if defaults != [10, 120, 10] or any(type(value) is not int for value in defaults):
                raise ValueError()
            data = json.loads(sys.stdin.read(8192))
            run, action = data["run"], data["action"]
            if (not isinstance(run, str) or not re.fullmatch(r"[a-f0-9]{16}", run)
                    or action not in ("create", "inspect") or not isinstance(data["db_address"], str)):
                raise ValueError()
            allowed = {"run", "action", "db_address"}
            if action == "create":
                allowed.add("passwords")
            if set(data) != allowed:
                raise ValueError()
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), host(inet_server_addr())")
                database, address = cursor.fetchone()
            if (database != settings.DATABASES["default"]["NAME"]
                    or address != data["db_address"]
                    or address != socket.gethostbyname(settings.DATABASES["default"]["HOST"])):
                raise ValueError()
            prefix = f"pilot-{run}"
            emails = {role: f"{prefix}-{role}@browser.example.test" for role in ROLES}
            with transaction.atomic():
                if action == "create":
                    passwords = data["passwords"]
                    if (not isinstance(passwords, dict) or set(passwords) != set(ROLES)
                            or any(not isinstance(value, str) or not 24 <= len(value) <= 128
                                   for value in passwords.values())
                            or User.objects.filter(email__startswith=prefix).exists()
                            or Category.objects.filter(slug__startswith=prefix).exists()):
                        raise ValueError()
                    users = {role: User.objects.create_user(email=email, password=passwords[role])
                             for role, email in emails.items()}
                    for user in users.values():
                        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
                    reviewer = users["reviewer"]
                    reviewer.user_permissions.add(Permission.objects.get(
                        content_type__app_label="listings", codename="review_listingrevision"))
                    category = Category.objects.create(name="Sentetik pilot kategorisi", slug=prefix)
                    AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
                    # Only these fresh reserved seller identities exceed the default; the
                    # context exits before any actor histories or live HTTP acceptance.
                    with override_settings(PILOT_NEW_LISTINGS_PER_DAY=12):
                        for number in range(12):
                            revision = create_listing_draft(actor=users["seller"], category_id=category.pk,
                                content={"title": f"Sentetik pilot {number:02}",
                                         "description": "Yalnız sentetik geliştirici kabul verisi.",
                                         "location": "İstanbul", "price": "100.00", "currency": "TRY"})
                            submit_revision(actor=users["seller"], revision_id=revision.pk)
                            approve_revision(actor=reviewer, revision_id=revision.pk,
                                             expected_public_revision_id=None, reason="Sentetik pilot kabulü")
                    listings = list(Listing.objects.filter(owner=users["seller"],
                                    public_revision__category=category).order_by("public_revision__title"))
                    for listing in listings[:10]:
                        start_conversation(actor=users["contact"], listing_id=listing.pk,
                                           body="Sentetik başarılı başlangıç", client_token=uuid4())
                    initial = start_conversation(actor=users["message"], listing_id=listings[0].pk,
                                                 body="Sentetik mesaj geçmişi 000", client_token=uuid4())
                    for number in range(1, 119):
                        send_message(actor=users["message"], conversation_id=initial.conversation_id,
                                     body=f"Sentetik mesaj geçmişi {number:03}", client_token=uuid4())
                    for _ in range(10):
                        create_listing_draft(actor=users["creator"], category_id=category.pk, content={})
                else:
                    users = {role: User.objects.get(email=email) for role, email in emails.items()}
                    category = Category.objects.get(slug=prefix)
                result = self.inspect(run, users, category)
                result["defaults"] = defaults
        except Exception:
            # No submitted values, passwords, email addresses, cookies or tokens.
            raise CommandError("Guarded synthetic pilot operation failed.") from None
        self.stdout.write(json.dumps(result))

    def inspect(self, run, users, category):
        seller_listings = list(Listing.objects.filter(owner=users["seller"],
                               public_revision__category=category).order_by("public_revision__title"))
        creator_listings = Listing.objects.filter(owner=users["creator"], revisions__category=category)
        if (len(seller_listings) != 12 or creator_listings.distinct().count() != 10
                or ListingRevision.objects.filter(category=category).exclude(
                    listing__owner__in=[users["seller"], users["creator"]]).exists()):
            raise ValueError()
        conversations = Conversation.objects.filter(initiator__in=[users["contact"], users["message"]])
        for conversation in conversations:
            if (conversation.listing_id not in {item.pk for item in seller_listings}
                    or conversation.recipient_id != users["seller"].pk
                    or set(conversation.participants.values_list("user_id", flat=True)) !=
                       {conversation.initiator_id, conversation.recipient_id}):
                raise ValueError()
        thread = conversations.get(initiator=users["message"], listing=seller_listings[0])
        draft = ListingRevision.objects.filter(listing__owner=users["creator"], category=category).order_by("pk").first()
        return {"run": run, "category": category.pk, "target_listing": str(seller_listings[10].pk),
                "thread": str(thread.pk),
                "contact_thread": str(conversations.filter(initiator=users["contact"]).order_by("pk").first().pk),
                "draft": draft.pk,
                "totals": {"conversations": conversations.count(),
                           "participants": Participant.objects.filter(conversation__in=conversations).count(),
                           "messages": Message.objects.filter(conversation__in=conversations).count(),
                           "revisions": ListingRevision.objects.filter(category=category).count()},
                "counts": {role: {"contacts": Conversation.objects.filter(initiator=user).count(),
                                 "messages": Message.objects.filter(sender=user).count(),
                                 "listings": Listing.objects.filter(owner=user).count()}
                           for role, user in users.items()},
                "thread_state": {"sequence": thread.last_sequence,
                                 "last_message_at": thread.last_message_at.isoformat(),
                                 "participants": [{"read": item.last_read_sequence,
                                                   "archived": item.archived_at is not None}
                                                  for item in Participant.objects.filter(conversation=thread).order_by("pk")]},
                "draft_state": {"version": draft.edit_version, "title": draft.title},
                "guard": {"debug": True, "site": "localhost:8089", "database_verified": True,
                          "project_mount": "classifieds-rebuild-dev_rebuild_media"}}
