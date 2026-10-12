from django.db.models import Prefetch
from .models import ListingRevision


def public_listings(*, at=None):
    from moderation.policies import visible_listings
    from media.models import RevisionImage
    return visible_listings(at=at).select_related(
        "public_revision", "public_revision__category", "public_revision__attribute_schema").prefetch_related(
        Prefetch("public_revision__images", queryset=RevisionImage.objects.select_related("asset").order_by("position", "pk")))



def revision_listing_id(*, revision_id):
    """Resolve parent identity only; callers must recheck membership after locking."""
    return ListingRevision.objects.values_list("listing_id", flat=True).get(pk=revision_id)
