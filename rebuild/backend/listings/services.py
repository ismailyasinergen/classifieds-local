from copy import deepcopy
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.locking import lock_users
from accounts.rate_limits import enforce_action_limit

from accounts.models import User
from catalog.models import AttributeSchema, Category
from .models import Listing, ListingRevision
from .policies import require_active_actor, require_owner
from .queries import revision_listing_id
from .validation import CONTENT_FIELDS, normalize_draft_content


class StaleEditVersion(ValidationError):
    def __init__(self):
        super().__init__("Taslak değişti; güncel sürümü yeniden yükleyin.", code="stale_edit_version")


class InvalidRevisionState(ValidationError):
    def __init__(self, message="Bu revizyon düzenlenebilir taslak durumunda değil."):
        super().__init__(message, code="invalid_revision_state")


def create_listing_draft(*, actor: User, category_id: int, content: dict) -> ListingRevision:
    require_active_actor(actor=actor)
    category = Category.objects.get(pk=category_id)
    schema = AttributeSchema.objects.filter(category=category).order_by("-version").first()
    if schema is None:
        raise ValidationError({"category": "Bu kategori için özellik şeması bulunamadı."})
    values = normalize_draft_content(schema=schema, content=content)
    with transaction.atomic():
        current = lock_users(user_ids=[actor.pk])[actor.pk]
        require_active_actor(actor=current)
        now = timezone.now()
        enforce_action_limit(events=Listing.objects.filter(owner=current),
                             action="new_listing", at=now)
        listing = Listing.objects.create(owner=current)
        revision = ListingRevision(
            listing=listing, category=category, attribute_schema=schema,
            schema_version=schema.version, **values)
        revision.full_clean()
        revision.save()
        return revision


def update_draft(*, actor: User, revision_id: int, expected_version: int, content: dict) -> ListingRevision:
    require_active_actor(actor=actor)
    if type(expected_version) is not int or expected_version < 1:
        raise ValidationError({"edit_version": "Pozitif tam sayı sürümü girin."})
    parent_id = revision_listing_id(revision_id=revision_id)
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=parent_id)
        require_owner(actor=actor, listing=listing)
        revision = ListingRevision.objects.select_for_update().get(pk=revision_id, listing=listing)
        if revision.status != ListingRevision.Status.DRAFT:
            raise InvalidRevisionState()
        if revision.edit_version != expected_version:
            raise StaleEditVersion()
        values = normalize_draft_content(schema=revision.attribute_schema, content=content)
        for name, value in values.items():
            setattr(revision, name, value)
        revision.edit_version += 1
        revision.full_clean()
        revision.save(update_fields=[*values, "edit_version", "updated_at"])
        return revision


def start_revision(*, actor: User, listing_id: UUID | str) -> ListingRevision:
    require_active_actor(actor=actor)
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=listing_id)
        require_owner(actor=actor, listing=listing)
        open_revision = (
            listing.revisions.select_for_update()
            .filter(status__in=[ListingRevision.Status.DRAFT, ListingRevision.Status.SUBMITTED])
            .order_by("-pk").first())
        if open_revision is not None:
            if open_revision.status == ListingRevision.Status.SUBMITTED:
                raise InvalidRevisionState("Gönderilmiş revizyonu geri çekmeden yeni taslak başlatamazsınız.")
            return open_revision
        source = (
            listing.revisions.select_for_update()
            .filter(status__in=[ListingRevision.Status.APPROVED, ListingRevision.Status.REJECTED,
                               ListingRevision.Status.WITHDRAWN])
            .order_by("-created_at", "-pk").first())
        if source is None:
            raise InvalidRevisionState("Önce kategori seçerek bir ilan taslağı oluşturun.")
        revision = ListingRevision(
            listing=listing, category=source.category, attribute_schema=source.attribute_schema,
            schema_version=source.schema_version,
            **{name: deepcopy(getattr(source, name)) for name in CONTENT_FIELDS})
        revision.full_clean()
        revision.save()
        from media.services import copy_ready_images
        copy_ready_images(source=source, target=revision)
        return revision
