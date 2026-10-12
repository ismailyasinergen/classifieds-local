"""Private drafts and explicit public snapshots; never mutate listings."""
from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.utils import timezone

from accounts.locking import lock_users
from accounts.mfa_policy import verified_current_email
from accounts.models import Storefront
from listings.policies import require_active_actor
from moderation.policies import public_visibility_restrictions


class StorefrontConflict(ValidationError):
    def __init__(self):
        super().__init__("Vitrin değişti. Güncel ekranı açıp yeniden deneyin.", code="stale_version")


def require_storefront_actor(actor):
    require_active_actor(actor=actor)
    if not verified_current_email(actor):
        raise PermissionDenied("Güncel e-posta adresinizi doğrulayın.")


def public_storefronts(*, at=None):
    verified = EmailAddress.objects.filter(user_id=OuterRef("owner_id"),
        email__iexact=OuterRef("owner__email"), verified=True)
    restricted = public_visibility_restrictions(at=at).filter(seller_id=OuterRef("owner_id"))
    return Storefront.objects.filter(is_published=True, owner__is_active=True).alias(
        current_email_verified=Exists(verified), seller_restricted=Exists(restricted),
    ).filter(current_email_verified=True, seller_restricted=False)


def validate_content(name, intro):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or "\x00" in name:
        raise ValidationError({"name": "1–80 karakterlik bir vitrin adı girin."})
    if not isinstance(intro, str) or len(intro) > 2000 or "\x00" in intro:
        raise ValidationError({"intro": "Tanıtım en fazla 2000 karakter olabilir."})
    return name.strip(), intro.strip()


@transaction.atomic
def create_storefront(*, actor, name, intro=""):
    require_storefront_actor(actor)
    name, intro = validate_content(name, intro)
    current = lock_users(user_ids=[actor.pk])[actor.pk]
    require_storefront_actor(current)
    storefront, _ = Storefront.objects.get_or_create(owner=current,
        defaults={"draft_name": name, "draft_intro": intro})
    return storefront


@transaction.atomic
def change_storefront(*, actor, storefront_id, expected_version, action, name=None, intro=None):
    require_storefront_actor(actor)
    current = lock_users(user_ids=[actor.pk])[actor.pk]
    require_storefront_actor(current)
    try:
        storefront = Storefront.objects.select_for_update().get(pk=storefront_id, owner=current)
    except Storefront.DoesNotExist:
        raise Http404() from None
    if action not in {"save", "publish", "unpublish"}:
        raise ValidationError("Geçersiz işlem.")
    # A repeated removal is a no-op; an old form cannot remove a later publication.
    if action == "unpublish" and not storefront.is_published:
        return storefront
    if type(expected_version) is not int or expected_version != storefront.edit_version:
        raise StorefrontConflict()
    if action == "save":
        storefront.draft_name, storefront.draft_intro = validate_content(name, intro)
    elif action == "publish":
        storefront.published_name, storefront.published_intro = validate_content(
            storefront.draft_name, storefront.draft_intro)
        storefront.is_published = True
        storefront.published_at = timezone.now()
    else:
        storefront.is_published = False
    storefront.edit_version += 1
    storefront.save()
    return storefront
