"""Fresh, receipt-bound synthetic MFA browser data for developer8089 only.

This command never enrolls factors, creates sessions or changes MFA policy.
Its private stdin/stdout transport must be captured by the guarded browser runner.
"""
import ipaddress
import json
import re
import socket
import sys
from pathlib import Path

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django.core import signing
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from accounts.models import SecurityEvent, User
from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision
from listings.publication import submit_revision
from listings.services import create_listing_draft

MODES = ("desktop", "mobile", "nojs")
ROLES = tuple(f"{mode}-{role}" for mode in MODES for role in ("staff", "reviewer", "seller"))
DEV_MOUNT = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media "
RECEIPT_SALT = "classifieds.developer-mfa-browser.v1"


def _mountinfo():
    return Path("/proc/self/mountinfo").read_text()


def _database_identity():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), host(inet_server_addr())")
        return cursor.fetchone()


def _guard(data):
    if (not settings.DEBUG or connection.vendor != "postgresql"
            or DEV_MOUNT not in _mountinfo()
            or not Site.objects.filter(pk=settings.SITE_ID, domain="localhost:8089").exists()):
        raise ValueError()
    database, address = _database_identity()
    ipaddress.IPv4Address(data["db_address"])
    if (database != settings.DATABASES["default"]["NAME"]
            or address != data["db_address"]
            or address != socket.gethostbyname(settings.DATABASES["default"]["HOST"])):
        raise ValueError()
    if (settings.ACCOUNT_EMAIL_VERIFICATION != "mandatory"
            or set(settings.MFA_SUPPORTED_TYPES) != {"totp", "recovery_codes"}
            or settings.MFA_TRUST_ENABLED or settings.MFA_ALLOW_UNVERIFIED_EMAIL
            or not settings.MFA_RECOVERY_CODES_SHOW_ONCE):
        raise ValueError()


def _decode_input():
    raw = sys.stdin.read(16385)
    if len(raw) > 16384:
        raise ValueError()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError()
    run, action = data["run"], data["action"]
    if (not isinstance(run, str) or not re.fullmatch(r"[a-f0-9]{16}", run)
            or action not in {"create", "inspect"} or not isinstance(data["db_address"], str)):
        raise ValueError()
    expected = {"run", "action", "db_address", "passwords" if action == "create" else "receipt"}
    if set(data) != expected:
        raise ValueError()
    if action == "create":
        passwords = data["passwords"]
        if (not isinstance(passwords, dict) or set(passwords) != set(ROLES)
                or any(not isinstance(value, str) or not 24 <= len(value) <= 128
                       for value in passwords.values())):
            raise ValueError()
    elif not isinstance(data["receipt"], str) or len(data["receipt"]) > 8192:
        raise ValueError()
    return data


def _inspect(run, receipt, permission):
    prefix = f"mfa-{run}"
    if set(receipt) != {"run", "users", "group", "category", "revisions"} or receipt["run"] != run:
        raise ValueError()
    if set(receipt["users"]) != set(ROLES) or set(receipt["revisions"]) != set(MODES):
        raise ValueError()
    if User.objects.filter(email__startswith=prefix).count() != len(ROLES):
        raise ValueError()
    users = {}
    for role in ROLES:
        user = User.objects.get(pk=receipt["users"][role], email=f"{prefix}-{role}@browser.example.test")
        if (not user.is_active or user.is_superuser or user.is_staff != role.endswith("-staff")
                or user.user_permissions.exists()
                or EmailAddress.objects.filter(user=user).count() != 1
                or not EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists()):
            raise ValueError()
        expected_groups = {receipt["group"]} if role.endswith("-reviewer") else set()
        if set(user.groups.values_list("pk", flat=True)) != expected_groups:
            raise ValueError()
        users[role] = user
    group = Group.objects.get(pk=receipt["group"], name=f"{prefix}-reviewers")
    reviewer_ids = {users[f"{mode}-reviewer"].pk for mode in MODES}
    if (set(group.permissions.values_list("pk", flat=True)) != {permission.pk}
            or set(group.user_set.values_list("pk", flat=True)) != reviewer_ids):
        raise ValueError()
    category = Category.objects.get(pk=receipt["category"], slug=prefix)
    if AttributeSchema.objects.filter(category=category).count() != 1:
        raise ValueError()
    revisions = ListingRevision.objects.filter(category=category)
    if set(revisions.values_list("pk", flat=True)) != set(receipt["revisions"].values()):
        raise ValueError()
    states = {}
    for mode in MODES:
        revision = revisions.select_related("listing").get(pk=receipt["revisions"][mode])
        seller = users[f"{mode}-seller"]
        if (revision.listing.owner_id != seller.pk
                or revision.title != f"MFA kabul {run} {mode}"
                or Listing.objects.filter(owner=seller).count() != 1
                or revision.listing.revisions.count() != 1
                or revision.status not in {"submitted", "approved"}):
            raise ValueError()
        if (revision.status == "approved") != (revision.listing.public_revision_id == revision.pk):
            raise ValueError()
        states[mode] = revision.status
    for role, user in users.items():
        if not role.endswith("-seller") and Listing.objects.filter(owner=user).exists():
            raise ValueError()
    return {
        "counts": {"users": len(users), "groups": 1, "listings": 3, "revisions": 3},
        "roles": {role: {
            "primary": Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).count(),
            "recovery": Authenticator.objects.filter(user=user, type=Authenticator.Type.RECOVERY_CODES).count(),
            "events": SecurityEvent.objects.filter(actor=user).count(),
        } for role, user in users.items()},
        "revisions": states,
        "guard": {"debug": True, "developer_site": True, "database_verified": True, "media_verified": True},
    }


class Command(BaseCommand):
    help = "Create/inspect only receipt-bound fresh synthetic MFA data in the isolated developer runtime."

    def handle(self, *args, **options):
        try:
            data = _decode_input()
            _guard(data)
            run, action = data["run"], data["action"]
            permission = Permission.objects.get(content_type__app_label="listings", codename="review_listingrevision")
            with transaction.atomic():
                if action == "create":
                    prefix = f"mfa-{run}"
                    if (User.objects.filter(email__startswith=prefix).exists()
                            or Category.objects.filter(slug__startswith=prefix).exists()
                            or Group.objects.filter(name__startswith=prefix).exists()):
                        raise ValueError()
                    users = {role: User.objects.create_user(
                        email=f"{prefix}-{role}@browser.example.test",
                        password=data["passwords"][role], is_staff=role.endswith("-staff"),
                    ) for role in ROLES}
                    for user in users.values():
                        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
                    group = Group.objects.create(name=f"{prefix}-reviewers")
                    group.permissions.add(permission)
                    for mode in MODES:
                        users[f"{mode}-reviewer"].groups.add(group)
                    category = Category.objects.create(name="Sentetik MFA kabulü", slug=prefix)
                    AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
                    revisions = {}
                    for mode in MODES:
                        seller = users[f"{mode}-seller"]
                        revision = create_listing_draft(actor=seller, category_id=category.pk, content={
                            "title": f"MFA kabul {run} {mode}",
                            "description": "Yalnız izole geliştirici MFA kabul verisi.",
                            "location": "İstanbul", "price": "100.00", "currency": "TRY",
                        })
                        submit_revision(actor=seller, revision_id=revision.pk)
                        revisions[mode] = revision.pk
                    receipt = {"run": run, "users": {role: user.pk for role, user in users.items()},
                               "group": group.pk, "category": category.pk, "revisions": revisions}
                    state = _inspect(run, receipt, permission)
                    if any(value["primary"] or value["recovery"] or value["events"] for value in state["roles"].values()):
                        raise ValueError()
                    result = {"receipt": signing.dumps(receipt, salt=RECEIPT_SALT, compress=True), "state": state}
                else:
                    receipt = signing.loads(data["receipt"], salt=RECEIPT_SALT, max_age=7200)
                    result = _inspect(run, receipt, permission)
        except Exception:
            # Never emit exception text, submitted values, addresses or credentials.
            raise CommandError("Guarded MFA fixture operation refused.") from None
        self.stdout.write(json.dumps(result))
