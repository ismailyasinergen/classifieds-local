"""Receipt-bound synthetic developer data; authentication and cases are UI-only."""
import json
import re
import sys
from uuid import uuid4
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth.models import Group, Permission
from django.core import signing
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import User
from accounts.management.commands.mfa_browser_fixture import _guard
from catalog.models import Category, AttributeSchema
from conversations.models import Message, UserBlock
from conversations.services import start_conversation, send_message
from listings.models import ListingRevision
from listings.services import create_listing_draft, start_revision
from listings.publication import submit_revision
from moderation.services import approve_revision
from moderation.models import ContentReport, ReportDecision, Appeal, AppealDecision, MessagingRestriction

MODES = ("desktop", "mobile", "nojs")
ROLES = tuple(f"{mode}-{role}" for mode in MODES for role in ("sender", "recipient", "report-reviewer", "appeal-reviewer"))
SALT = "classifieds.developer-case-browser.v1"


def _input():
    raw = sys.stdin.read(16385)
    if len(raw) > 16384:
        raise ValueError()
    data = json.loads(raw)
    if (not isinstance(data, dict) or not isinstance(data.get("run"), str)
            or not re.fullmatch(r"[a-f0-9]{16}", data["run"])
            or data.get("action") not in {"create", "inspect"} or not isinstance(data.get("db_address"), str)):
        raise ValueError()
    extra = "passwords" if data["action"] == "create" else "receipt"
    if set(data) != {"action", "run", "db_address", extra}:
        raise ValueError()
    if extra == "passwords":
        if (not isinstance(data[extra], dict) or set(data[extra]) != set(ROLES)
                or any(not isinstance(value, str) or not 24 <= len(value) <= 128 for value in data[extra].values())):
            raise ValueError()
    elif not isinstance(data[extra], str) or len(data[extra]) > 8192:
        raise ValueError()
    return data


def _permissions(role):
    names = []
    if role == "publisher":
        return Permission.objects.filter(content_type__app_label="listings", codename="review_listingrevision")
    if role.endswith("report-reviewer"):
        names = ["review_reports", "review_appeals", "restrict_messaging"]
    elif role.endswith("appeal-reviewer"):
        names = ["review_appeals", "restrict_messaging"]
    return Permission.objects.filter(content_type__app_label="moderation", codename__in=names)


def _inspect(run, receipt):
    if set(receipt) != {"run", "users", "category", "targets"} or receipt["run"] != run:
        raise ValueError()
    prefix = f"case-{run}"
    if set(receipt["users"]) != {*ROLES, "publisher"} or set(receipt["targets"]) != set(MODES):
        raise ValueError()
    users = {}
    if User.objects.filter(email__startswith=prefix).count() != len(ROLES) + 1:
        raise ValueError()
    for role, user_id in receipt["users"].items():
        user = User.objects.get(pk=user_id, email=f"{prefix}-{role}@browser.example.test", is_active=True,
                                is_staff=False, is_superuser=False)
        if (user.groups.exists() or set(user.user_permissions.values_list("pk", flat=True)) != set(_permissions(role).values_list("pk", flat=True))
                or EmailAddress.objects.filter(user=user).count() != 1
                or not EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists()):
            raise ValueError()
        users[role] = user
    category = Category.objects.get(pk=receipt["category"], slug=prefix)
    revisions = []
    for mode, target in receipt["targets"].items():
        owner = users[mode + "-recipient"]
        for key in ("main", "no_action", "stale", "current"):
            revision = ListingRevision.objects.select_related("listing").get(pk=target[key], category=category,
                listing__owner=owner, status="approved")
            if key != "stale" and revision.listing.public_revision_id != revision.pk:
                raise ValueError()
            revisions.append(revision.pk)
        if str(ListingRevision.objects.get(pk=target["main"]).listing_id) != target["listing"]:
            raise ValueError()
        actual = Message.objects.filter(pk__in=target["messages"], conversation_id=target["conversation"],
            sender=users[mode + "-sender"], conversation__recipient=owner,
            conversation__initiator=users[mode + "-sender"]).count()
        if actual != len(target["messages"]):
            raise ValueError()
    if set(ListingRevision.objects.filter(category=category).values_list("pk", flat=True)) != set(revisions):
        raise ValueError()
    owned = list(receipt["users"].values())
    reports = ContentReport.objects.filter(reporter_id__in=owned, subject_user_id__in=owned)
    decisions = ReportDecision.objects.filter(report__in=reports)
    appeals = Appeal.objects.filter(decision__in=decisions)
    return {"counts": {"users": len(users), "reports": reports.count(), "decisions": decisions.count(),
        "appeals": appeals.count(), "appeal_decisions": AppealDecision.objects.filter(appeal__in=appeals).count(),
        "messaging_restrictions": MessagingRestriction.objects.filter(user_id__in=owned).count(),
        "active_messaging_restrictions": MessagingRestriction.objects.filter(user_id__in=owned, revoked_at__isnull=True).count(),
        "blocks": UserBlock.objects.filter(blocker_id__in=owned, blocked_id__in=owned).count()},
        "factors": Authenticator.objects.filter(user_id__in=owned).count(), "targets": receipt["targets"],
        "guard": {"debug": True, "developer_site": True, "database_verified": True, "media_verified": True}}


class Command(BaseCommand):
    help = "Create or inspect receipt-bound synthetic report/appeal acceptance data on developer only."

    def handle(self, *args, **options):
        try:
            data = _input()
            _guard(data)
            run = data["run"]
            with transaction.atomic():
                if data["action"] == "inspect":
                    result = _inspect(run, signing.loads(data["receipt"], salt=SALT, max_age=14400))
                else:
                    prefix = f"case-{run}"
                    if (User.objects.filter(email__startswith=prefix).exists()
                            or Category.objects.filter(slug__startswith=prefix).exists()
                            or Group.objects.filter(name__startswith=prefix).exists()):
                        raise ValueError()
                    users = {}
                    for role in (*ROLES, "publisher"):
                        user = User.objects.create_user(f"{prefix}-{role}@browser.example.test",
                            password=data["passwords"].get(role))
                        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
                        user.user_permissions.set(_permissions(role))
                        users[role] = user
                    category = Category.objects.create(name="Sentetik bildirim kabulü", slug=prefix)
                    AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
                    targets = {}
                    for mode in MODES:
                        owner, sender = users[mode + "-recipient"], users[mode + "-sender"]
                        target = {}
                        for name in ("main", "no_action", "stale"):
                            revision = create_listing_draft(actor=owner, category_id=category.pk, content={
                                "title": f"Sentetik kabul {mode} {name} " + "Uzun başlık " * 8,
                                "description": "Yalnız developer kabul verisi.", "location": "İstanbul",
                                "price": "100.00", "currency": "TRY"})
                            submit_revision(actor=owner, revision_id=revision.pk)
                            approve_revision(actor=users["publisher"], revision_id=revision.pk,
                                expected_public_revision_id=None, reason="Sentetik ilk yayın")
                            target[name] = revision.pk
                            if name == "main":
                                target["listing"] = str(revision.listing_id)
                            if name == "stale":
                                current = start_revision(actor=owner, listing_id=revision.listing_id)
                                submit_revision(actor=owner, revision_id=current.pk)
                                approve_revision(actor=users["publisher"], revision_id=current.pk,
                                    expected_public_revision_id=revision.pk, reason="Sentetik yeni sürüm")
                                target["current"] = current.pk
                        first = start_conversation(actor=sender, listing_id=target["listing"],
                            body="Sentetik kabul mesajı", client_token=uuid4())
                        target["conversation"] = str(first.conversation_id)
                        target["messages"] = [first.pk]
                        for index in range(22 if mode == "desktop" else 2):
                            target["messages"].append(send_message(actor=sender, conversation_id=first.conversation_id,
                                body=f"Sentetik kabul mesajı {index + 2}", client_token=uuid4()).pk)
                        targets[mode] = target
                    receipt = dict(run=run, users={role: user.pk for role, user in users.items()},
                        category=category.pk, targets=targets)
                    state = _inspect(run, receipt)
                    if state["factors"] or any(state["counts"][key] for key in ("reports", "decisions", "appeals", "appeal_decisions")):
                        raise ValueError()
                    result = {"receipt": signing.dumps(receipt, salt=SALT, compress=True), "state": state}
        except Exception:
            raise CommandError("Guarded case fixture operation refused.") from None
        self.stdout.write(json.dumps(result))
