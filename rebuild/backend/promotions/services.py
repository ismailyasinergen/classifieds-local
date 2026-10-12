from datetime import timedelta
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from accounts.locking import lock_users
from accounts.mfa_policy import has_mfa_proof, requires_mfa, verified_current_email
from listings.models import Listing
from listings.policies import require_active_actor, require_owner
from listings.queries import public_listings
from listings.search.queries import matching_public_listings
from .models import Activation, DemoEvidence, PromotionProduct, Purchase


class PromotionConflict(ValidationError):
    pass


def require_demo():
    if (not settings.PROMOTIONS_DEMO_ENABLED
            or settings.DEPLOYMENT_ENVIRONMENT != "developer"
            or connection.vendor != "postgresql"
            or not Site.objects.filter(pk=settings.SITE_ID, domain="localhost:8089").exists()):
        raise PermissionDenied("Demo bu ortamda etkin değil.")
    try:
        developer_mount = "/volumes/classifieds-rebuild-dev_rebuild_media/_data /var/lib/classifieds/media " in Path("/proc/self/mountinfo").read_text()
    except OSError:
        developer_mount = False
    if not developer_mount:
        raise PermissionDenied("Geliştirici ortamı doğrulanamadı.")


def require_actor(actor, listing, request=None):
    require_owner(actor=actor, listing=listing)
    if not verified_current_email(actor):
        raise PermissionDenied("Güncel e-posta adresinizi doğrulayın.")
    if requires_mfa(actor) and (request is None or request.user.pk != actor.pk or not has_mfa_proof(request)):
        raise PermissionDenied("İki aşamalı doğrulama gerekli.")


def require_eligible(listing, at):
    if not public_listings(at=at).filter(pk=listing.pk).exists():
        raise PromotionConflict("Yalnız güncel, yayımdaki kendi ilanınız öne çıkarılabilir.")


def overlapping(listing, at):
    return Activation.objects.filter(listing=listing, placement="search", starts_at__lte=at, ends_at__gt=at).exists()


@transaction.atomic
def purchase_demo(*, actor, listing_id, product_id, key, request=None):
    require_demo()
    require_active_actor(actor=actor)
    try:
        key = UUID(str(key))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("Geçersiz işlem anahtarı.") from None
    listing = Listing.objects.select_for_update().get(pk=listing_id)
    current = lock_users(user_ids=[actor.pk])[actor.pk]
    require_actor(current, listing, request)
    now = timezone.now()
    require_eligible(listing, now)
    existing = Purchase.objects.filter(owner=current, key=key).first()
    if existing:
        if existing.listing_id != listing.pk or existing.product_id != product_id:
            raise PromotionConflict("Bu işlem anahtarı farklı bir seçim için kullanıldı.")
        return existing
    if overlapping(listing, now):
        raise PromotionConflict("Bu ilanın etkin öne çıkarma hakkı zaten var.")
    product = PromotionProduct.objects.select_for_update().get(pk=product_id, enabled=True)
    product.full_clean()
    return Purchase.objects.create(owner=current, listing=listing, product=product, key=key,
        product_name=product.name, amount=product.amount, currency=product.currency,
        duration_seconds=product.duration_seconds, placement=product.placement, terms_version=product.terms_version)


@transaction.atomic
def complete_demo(*, actor, purchase_id, request=None):
    require_demo()
    require_active_actor(actor=actor)
    parent_id = Purchase.objects.values_list("listing_id", flat=True).get(pk=purchase_id, owner_id=actor.pk)
    listing = Listing.objects.select_for_update().get(pk=parent_id)
    current = lock_users(user_ids=[actor.pk])[actor.pk]
    require_actor(current, listing, request)
    purchase = Purchase.objects.select_for_update().get(pk=purchase_id, owner=current, listing=listing)
    now = timezone.now()
    require_eligible(listing, now)
    existing = Activation.objects.filter(purchase=purchase).first()
    if existing:
        return existing
    if overlapping(listing, now):
        raise PromotionConflict("Bu ilanın etkin öne çıkarma hakkı zaten var.")
    DemoEvidence.objects.create(purchase=purchase)
    return Activation.objects.create(purchase=purchase, listing=listing, placement=purchase.placement,
        starts_at=now, ends_at=now + timedelta(seconds=purchase.duration_seconds))


def sponsored_listings(*, spec, at=None):
    at = timezone.now() if at is None else at
    queryset = matching_public_listings(spec=spec, at=at)
    available = Activation.objects.filter(placement="search", starts_at__lte=at, ends_at__gt=at)
    # Preserve the organic listing query budget when no promotion is active.
    if not available.exists():
        return queryset.none()
    active = available.filter(listing_id=OuterRef("pk")).order_by("-starts_at", "-pk")
    return queryset.annotate(
        promotion_start=Subquery(active.values("starts_at")[:1]),
        promotion_id=Subquery(active.values("pk")[:1]),
    ).filter(promotion_id__isnull=False, owner__is_active=True).order_by("-promotion_start", "-promotion_id", "-pk")[:3]