"""Disposable synthetic search records, restricted to the separate developer runtime."""
import json
import re
import sys
from io import BytesIO

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.test import override_settings
from PIL import Image, ImageDraw

from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.models import Listing
from listings.publication import submit_revision
from listings.services import create_listing_draft
from media.models import MediaAsset
from media.services import link_image
from moderation.services import approve_revision


class Command(BaseCommand):
    help = "Create fresh reserved search fixtures only on DEBUG localhost:8089; no login credentials."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Search browser fixtures require DEBUG.")
        if not Site.objects.filter(pk=settings.SITE_ID, domain="localhost:8089").exists():
            raise CommandError("Search browser fixtures require the isolated developer Site.")
        try:
            data = json.loads(sys.stdin.read(1024))
            if set(data) != {"run"} or not isinstance(data["run"], str) or not re.fullmatch(r"[a-f0-9]{16}", data["run"]):
                raise ValueError()
            run = data["run"]
            prefix = f"search-{run}"
            emails = [f"{prefix}-{role}@browser.example.test" for role in ("owner", "reviewer")]
            if User.objects.filter(email__in=emails).exists() or Category.objects.filter(slug__startswith=prefix).exists():
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise CommandError("Invalid or previously used synthetic search run.") from None
        # Scoped solely to this fresh reserved 25-listing search setup.
        with transaction.atomic(), override_settings(PILOT_NEW_LISTINGS_PER_DAY=25):
            owner, reviewer = [User.objects.create_user(email=email, password=None) for email in emails]
            reviewer.user_permissions.add(Permission.objects.get(
                content_type__app_label="listings", codename="review_listingrevision"))
            parent = Category.objects.create(name="Deneme koleksiyonu", slug=f"{prefix}-root")
            category = Category.objects.create(name="Otomobil denemesi", slug=f"{prefix}-auto", parent=parent)
            other = Category.objects.create(name="Emlak denemesi", slug=f"{prefix}-home")
            fields = {
                "model_year": {"type": "integer", "label": "Model yılı", "min": 1900},
                "area": {"type": "decimal", "label": "Motor hacmi", "unit": "L"},
                "electric": {"type": "boolean", "label": "Elektrikli"},
                "brand": {"type": "string", "label": "Renk", "options": ["Mavi"]},
                "note": {"type": "string", "label": "Donanım"},
                "internal": {"type": "string", "filterable": False},
            }
            original = AttributeSchema.objects.create(category=category, version=1, definition={"fields": fields})
            fields = {**fields, "brand": {**fields["brand"], "options": ["Beyaz"]}}
            latest = AttributeSchema.objects.create(category=category, version=2, definition={"fields": fields})
            AttributeSchema.objects.create(category=other, version=1, definition={"fields": {
                "area_m2": {"type": "decimal", "label": "Alan", "unit": "m²"}}})
            image = Image.new("RGB", (720, 440), "#e5eee6")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 325, 720, 440), fill="#bdcbbb")
            draw.rounded_rectangle((100, 220, 620, 320), radius=24, fill="#146b58")
            draw.polygon([(220, 225), (275, 145), (480, 145), (550, 225)], fill="#146b58")
            draw.polygon([(260, 208), (295, 162), (380, 162), (380, 208)], fill="#b2d2d5")
            draw.polygon([(395, 162), (467, 162), (510, 208), (395, 208)], fill="#b2d2d5")
            for x in (230, 515):
                draw.ellipse((x - 36, 285, x + 36, 357), fill="#172c32")
                draw.ellipse((x - 17, 304, x + 17, 338), fill="#d9e2dc")
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            picture = buffer.getvalue()
            asset = MediaAsset.objects.create(owner=owner, source_mime="image/jpeg",
                                              source_bytes=len(picture), width=720, height=440,
                                              state="ready", processed_at=timezone.now())
            asset.original.save("synthetic.jpg", ContentFile(picture), save=False)
            asset.derivative.save(f"search-fixtures/{run}/car.jpg", ContentFile(picture), save=False)
            asset.save()
            published_ids = []
            for number in range(1, 26):
                revision = create_listing_draft(actor=owner, category_id=category.pk, content={
                    "title": f"BMW X5 · Bakımlı otomobil {number:02}",
                    "description": "Sentetik tarayıcı arama denemesi. Gerçek bir satış ilanı değildir.",
                    "price": "245000.00", "currency": "TRY", "location": "İstanbul · Şişli",
                    "attributes": {"model_year": 2022, "area": "2", "electric": False,
                                   "brand": "Beyaz", "note": "Bakımlı"},
                })
                link_image(actor=owner, revision_id=revision.pk, asset_id=asset.pk, position=0)
                submit_revision(actor=owner, revision_id=revision.pk)
                approve_revision(actor=reviewer, revision_id=revision.pk,
                                 expected_public_revision_id=None, reason="Sentetik arama kabul denemesi")
                published_ids.append(revision.listing_id)
            # Only this command's freshly created rows are tied; no existing row is altered.
            Listing.objects.filter(pk__in=published_ids).update(first_published_at=timezone.now())
        self.stdout.write(json.dumps({
            "run": run, "category": category.pk, "parent": parent.pk, "other": other.pk,
            "source": {"id": latest.pk, "version": latest.version},
            "older": {"id": original.pk, "version": original.version},
            "order": sorted((str(value) for value in published_ids), reverse=True),
            "count": len(published_ids),
        }))
