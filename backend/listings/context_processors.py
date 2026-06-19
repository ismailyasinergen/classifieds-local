from .models import ListingFavorite


def favorite_listing_ids(request):
    if not request.user.is_authenticated:
        return {
            "favorite_listing_ids": set(),
        }

    ids = ListingFavorite.objects.filter(
        user=request.user,
    ).values_list("listing_id", flat=True)

    return {
        "favorite_listing_ids": set(ids),
    }
