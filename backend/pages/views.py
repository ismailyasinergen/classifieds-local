from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from categories.models import Category
from listings.models import Listing


def home_view(request):
    from listings.listing_card_promotions_v343 import (
        annotate_listing_card_promotions_v343,
    )

    approved_listings = annotate_listing_card_promotions_v343(
        Listing.objects
        .select_related(
            "category",
            "owner",
            "owner__profile",
            "owner__seller_store",
        )
        .prefetch_related("images")
        .filter(status=Listing.Status.APPROVED)
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
    )

    featured_listings = (
        approved_listings
        .filter(is_featured=True)
        .filter(Q(featured_until__isnull=True) | Q(featured_until__gt=timezone.now()))
        .order_by("-featured_priority", "-created_at")[:12]
    )
    latest_listings = approved_listings[:8]

    category_sections = []

    root_categories = Category.objects.filter(parent__isnull=True).order_by("name")

    for category in root_categories:
        category_ids = category.get_descendant_ids()

        listings = approved_listings.filter(
            category_id__in=category_ids
        )[:4]

        if listings:
            category_sections.append(
                {
                    "category": category,
                    "listings": listings,
                }
            )

    return render(
        request,
        "pages/home.html",
        {
            "page_title": "Classifieds Local",
            "featured_listings": featured_listings,
            "latest_listings": latest_listings,
            "category_sections": category_sections,
        },
    )
