from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Q, F
from django.utils import timezone

from accounts.models import User
from listings.models import Listing
from listings.policies import require_active_actor
from .models import Restriction


def require_reviewer(*, actor):
    require_active_actor(actor=actor)
    # Re-read permissions so a cached user object cannot retain revoked authority.
    current = User.objects.get(pk=actor.pk)
    if not current.has_perm("listings.review_listingrevision"):
        raise PermissionDenied("İlan inceleme izniniz yok.")


def public_visibility_restrictions(*, at=None):
    at = timezone.now() if at is None else at
    return Restriction.objects.filter(begins_at__lte=at).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gt=at)).filter(
        revoked_at__isnull=True)


def visible_listings(*, at=None):
    """Shared current-public visibility for later list/detail/media callers."""
    at = timezone.now() if at is None else at
    restrictions = public_visibility_restrictions(at=at).filter(
        Q(listing_id=OuterRef("pk")) | Q(seller_id=OuterRef("owner_id")))
    return Listing.objects.filter(
        lifecycle=Listing.Lifecycle.LIVE, public_revision__status="approved",
        public_revision__listing_id=F("pk")).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=at)).alias(
        hidden_by_restriction=Exists(restrictions)).filter(hidden_by_restriction=False)
