from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404

from accounts.locking import lock_users
from accounts.mfa_policy import verified_current_email
from .models import Favorite, Listing
from .policies import require_active_actor
from .queries import public_listings

FAVORITE_LIMIT = 200


def require_private_actor(actor):
    require_active_actor(actor=actor)
    if not verified_current_email(actor):
        raise PermissionDenied("Önce güncel e-posta adresinizi doğrulayın.")


@transaction.atomic
def add_favorite(*, actor, listing_id):
    require_active_actor(actor=actor)
    try:
        listing = Listing.objects.select_for_update().get(pk=listing_id)
    except Listing.DoesNotExist:
        raise Http404 from None
    lock_users(user_ids=[actor.pk, listing.owner_id])
    require_private_actor(actor)
    if not public_listings().filter(pk=listing.pk).exists():
        raise Http404
    existing = Favorite.objects.filter(user=actor, listing=listing).first()
    if existing:
        return existing
    if Favorite.objects.filter(user=actor).count() >= FAVORITE_LIMIT:
        raise ValidationError("En fazla 200 favori saklayabilirsiniz. Önce bir favoriyi kaldırın.")
    return Favorite.objects.create(user=actor, listing=listing)


@transaction.atomic
def remove_favorite(*, actor, listing_id):
    require_active_actor(actor=actor)
    lock_users(user_ids=[actor.pk])
    require_private_actor(actor)
    Favorite.objects.filter(user=actor, listing_id=listing_id).delete()
