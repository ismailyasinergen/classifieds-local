"""Narrow local browser-test support. JSON output is captured exclusively by the driver."""
import json
import re
import sys
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from accounts.models import User


class Command(BaseCommand):
    help = "Create or inspect only run-scoped synthetic browser fixtures; no arbitrary accounts."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Local browser fixtures require DEBUG.")
        try:
            data = json.loads(sys.stdin.read(8192))
            run = data["run"]
            if not isinstance(run, str) or not re.fullmatch(r"[a-f0-9]{16}", run):
                raise ValueError()
            role = data.get("role", "seller")
            if role not in ("seller", "reviewer", "staff"):
                raise ValueError()
            email = f"task5-{run}-{role}@browser.example.test"
            action = data["action"]
            result = {}
            if action == "reviewer" and role in ("reviewer", "staff"):
                password = data["password"]
                if not isinstance(password, str) or len(password) < 24 or User.objects.filter(email=email).exists():
                    raise ValueError()
                user = User.objects.create_user(email=email, password=password, is_staff=(role == "staff"))
                EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
                if role == "reviewer":
                    user.user_permissions.add(Permission.objects.get(
                        content_type__app_label="listings", codename="review_listingrevision"))
                result = {"ok": True}
            elif action == "confirm" and role == "seller":
                address = EmailAddress.objects.get(email=email, user__email=email, verified=False)
                result = {"url": reverse("account_confirm_email", args=[EmailConfirmationHMAC(address).key])}
            elif action == "inspect" and role == "seller":
                from listings.models import Listing
                user = User.objects.get(email=email)
                listings = []
                for listing in Listing.objects.filter(owner=user).order_by("created_at", "pk"):
                    revisions = []
                    for revision in listing.revisions.order_by("pk"):
                        revisions.append({"id": revision.pk, "status": revision.status,
                                          "edit_version": revision.edit_version,
                                          "images": list(revision.images.order_by("position", "pk").values(
                                              "asset_id", "asset__state", "asset__attempts"))})
                    listings.append({"id": str(listing.pk), "public_revision_id": listing.public_revision_id,
                                     "revisions": revisions})
                result = {"listings": listings}
            else:
                raise ValueError()
        except Exception:
            # Never echo submitted JSON, credentials, confirmation URLs or account identifiers.
            raise CommandError("Synthetic browser fixture operation failed.") from None
        self.stdout.write(json.dumps(result))
