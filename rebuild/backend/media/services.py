import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from listings.models import Listing, ListingRevision
from listings.policies import require_active_actor, require_owner
from listings.queries import revision_listing_id
from listings.services import InvalidRevisionState
from .models import MediaAsset, RevisionImage
from .tasks import process_image
from .validation import validate_upload

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


def enqueue_processing(asset_id):
    """Best effort broker delivery; PostgreSQL pending rows remain the durable source."""
    try:
        process_image.delay(asset_id)
        MediaAsset.objects.filter(pk=asset_id, state=MediaAsset.State.PENDING).update(
            last_enqueued_at=timezone.now())
    except Exception:
        logger.warning("Media enqueue unavailable for asset %s; pending scan will retry.", asset_id)
        return False
    return True


def _locked_draft(*, actor, revision_id):
    parent_id = revision_listing_id(revision_id=revision_id)
    listing = Listing.objects.select_for_update().get(pk=parent_id)
    require_owner(actor=actor, listing=listing)
    revision = ListingRevision.objects.select_for_update().get(pk=revision_id, listing=listing)
    if revision.status != ListingRevision.Status.DRAFT:
        raise InvalidRevisionState()
    return revision


def _require_capacity(revision):
    if revision.images.count() >= settings.MEDIA_MAX_IMAGES_PER_REVISION:
        raise ValidationError("Bu revizyon için görsel sayısı sınırına ulaşıldı.")


def _require_asset_owner(*, actor, asset):
    if asset.owner_id != actor.pk:
        raise PermissionDenied("Bu görseli kullanma yetkiniz yok.")


def attach_image(*, actor: User, revision_id: int, uploaded_file) -> MediaAsset:
    require_active_actor(actor=actor)
    data, mime, width, height = validate_upload(uploaded_file)
    asset = None
    try:
        with transaction.atomic():
            revision = _locked_draft(actor=actor, revision_id=revision_id)
            _require_capacity(revision)
            positions = list(revision.images.values_list("position", flat=True))
            position = next(number for number in range(settings.MEDIA_MAX_IMAGES_PER_REVISION)
                            if number not in positions)
            asset = MediaAsset(owner=actor, source_mime=mime, source_bytes=len(data),
                               width=width, height=height)
            asset.original.save("ignored", ContentFile(data), save=False)
            asset.save()
            RevisionImage.objects.create(revision=revision, asset=asset, position=position)
            transaction.on_commit(lambda: enqueue_processing(asset.pk))
            return asset
    except Exception:
        if asset is not None and asset.original.name:
            asset.original.storage.delete(asset.original.name)
        raise


def link_image(*, actor: User, revision_id: int, asset_id: int, position: int) -> RevisionImage:
    require_active_actor(actor=actor)
    if type(position) is not int or not 0 <= position < settings.MEDIA_MAX_IMAGES_PER_REVISION:
        raise ValidationError("Geçerli bir görsel sırası girin.")
    with transaction.atomic():
        revision = _locked_draft(actor=actor, revision_id=revision_id)
        asset = MediaAsset.objects.select_for_update().get(pk=asset_id)
        _require_asset_owner(actor=actor, asset=asset)
        _require_capacity(revision)
        if revision.images.filter(asset=asset).exists() or revision.images.filter(position=position).exists():
            raise ValidationError("Görsel veya sırası bu revizyonda zaten kullanılıyor.")
        return RevisionImage.objects.create(revision=revision, asset=asset, position=position)


def retry_image(*, actor: User, revision_id: int, asset_id: int) -> MediaAsset:
    require_active_actor(actor=actor)
    with transaction.atomic():
        revision = _locked_draft(actor=actor, revision_id=revision_id)
        asset = MediaAsset.objects.select_for_update().get(pk=asset_id)
        _require_asset_owner(actor=actor, asset=asset)
        if not revision.images.filter(asset=asset).exists():
            raise ValidationError("Görsel bu revizyona ait değil.")
        if asset.state != MediaAsset.State.FAILED or asset.attempts >= MAX_ATTEMPTS:
            raise ValidationError("Bu görsel şu anda yeniden işlenemez.")
        asset.state = MediaAsset.State.PENDING
        asset.error_code = ""
        asset.last_enqueued_at = None
        asset.save(update_fields=["state", "error_code", "last_enqueued_at", "updated_at"])
        transaction.on_commit(lambda: enqueue_processing(asset.pk))
        return asset


def remove_image(*, actor: User, revision_id: int, asset_id: int) -> None:
    """Unlink only a draft relation; shared asset rows and private files survive."""
    require_active_actor(actor=actor)
    with transaction.atomic():
        revision = _locked_draft(actor=actor, revision_id=revision_id)
        asset = MediaAsset.objects.select_for_update().get(pk=asset_id)
        _require_asset_owner(actor=actor, asset=asset)
        link = revision.images.filter(asset=asset).first()
        if link is None:
            raise ValidationError("Görsel bu revizyona ait değil.")
        link.delete()


def require_revision_images_ready(*, revision) -> None:
    """Publication caller holds Listing then revision locks; we lock only linked assets."""
    links = list(revision.images.order_by("position", "pk"))
    assets = {asset.pk: asset for asset in MediaAsset.objects.select_for_update()
              .filter(pk__in=[link.asset_id for link in links]).order_by("pk")}
    if len(links) > settings.MEDIA_MAX_IMAGES_PER_REVISION:
        raise ValidationError("Görsel sayısı sınırı aşıldı.")
    for link in links:
        asset = assets[link.asset_id]
        if (asset.owner_id != revision.listing.owner_id or asset.state != MediaAsset.State.READY
                or not asset.derivative.name or not asset.derivative.storage.exists(asset.derivative.name)):
            raise ValidationError("Tüm görseller ilan sahibine ait ve işlenmiş olmalıdır.")


def copy_ready_images(*, source, target) -> None:
    """Internal start_revision hook; caller already holds same Listing/source/target locks."""
    if source.listing_id != target.listing_id or target.status != ListingRevision.Status.DRAFT:
        raise InvalidRevisionState()
    links = list(source.images.order_by("position", "pk"))
    assets = {asset.pk: asset for asset in MediaAsset.objects.select_for_update()
              .filter(pk__in=[link.asset_id for link in links]).order_by("pk")}
    for link in links:
        asset = assets[link.asset_id]
        if asset.state == MediaAsset.State.READY and asset.owner_id == target.listing.owner_id:
            RevisionImage.objects.create(revision=target, asset=asset, position=link.position)
