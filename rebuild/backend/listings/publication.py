from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from catalog.validation import validate_attributes
from media.services import require_revision_images_ready
from .models import Listing, ListingRevision
from .policies import require_owner
from .queries import revision_listing_id
from .services import InvalidRevisionState
from .validation import CONTENT_FIELDS, normalize_draft_content


class StalePublicRevision(ValidationError):
    def __init__(self):
        super().__init__("Yayımlanan sürüm değişti; güncel ilanı yeniden yükleyin.", code="stale_public_revision")


def locked_revision(*, revision_id):
    """Internal: caller owns atomic; acquire parent before the exact child."""
    parent_id = revision_listing_id(revision_id=revision_id)
    listing = Listing.objects.select_for_update().get(pk=parent_id)
    revision = ListingRevision.objects.select_for_update().get(pk=revision_id, listing_id=listing.pk)
    revision.listing = listing
    return listing, revision


def require_publishable_content(*, revision):
    revision.full_clean()
    content = {name: getattr(revision, name) for name in CONTENT_FIELDS}
    canonical = normalize_draft_content(schema=revision.attribute_schema, content=content)
    canonical["attributes"] = validate_attributes(schema=revision.attribute_schema, values=revision.attributes)
    missing = {name: "Bu alan yayımlama için zorunludur."
               for name in ("title", "description", "currency", "location") if not canonical[name]}
    if canonical["price"] is None:
        missing["price"] = "Yayımlama için fiyat girin."
    if missing:
        raise ValidationError(missing)
    if canonical != content:
        raise ValidationError("İçerik standart biçimde kaydedilmelidir.", code="noncanonical_content")
    require_revision_images_ready(revision=revision)


def submit_revision(*, actor: User, revision_id: int) -> ListingRevision:
    with transaction.atomic():
        listing, revision = locked_revision(revision_id=revision_id)
        require_owner(actor=actor, listing=listing)
        if revision.status != ListingRevision.Status.DRAFT:
            raise InvalidRevisionState("Yalnız taslak revizyon gönderilebilir.")
        require_publishable_content(revision=revision)
        revision.status = ListingRevision.Status.SUBMITTED
        revision.save(update_fields=["status", "updated_at"])
        return revision


def withdraw_revision(*, actor: User, revision_id: int) -> ListingRevision:
    with transaction.atomic():
        listing, revision = locked_revision(revision_id=revision_id)
        require_owner(actor=actor, listing=listing)
        if revision.status != ListingRevision.Status.SUBMITTED:
            raise InvalidRevisionState("Yalnız gönderilmiş revizyon geri çekilebilir.")
        revision.status = ListingRevision.Status.WITHDRAWN
        revision.save(update_fields=["status", "updated_at"])
        return revision
