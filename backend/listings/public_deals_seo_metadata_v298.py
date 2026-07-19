"""
PUBLIC_DEALS_SEO_METADATA_V298

Request-aware SEO metadata for the public Deals landing page.

The helper is intentionally presentation-only. It adds no database query,
model field, route, sitemap, robots endpoint, or persisted state.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.parse import urlencode

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest
from django.urls import reverse
from django.core.paginator import Page

from .models import Listing


PUBLIC_DEALS_SEO_METADATA_V298 = True

PUBLIC_DEALS_SITE_NAME_V298 = "Classifieds Local"

PUBLIC_DEALS_META_DESCRIPTION_V298 = (
    "Browse genuine current price reductions on active listings, "
    "ranked by the biggest percentage savings on Classifieds Local."
)


def _safe_json_ld_v298(payload: dict) -> str:
    """
    Serialize JSON-LD while preventing an embedded value from closing its
    script element.

    ``ensure_ascii=True`` also gives deterministic handling for line-separator
    characters that are unsafe in some JavaScript parsing contexts.
    """

    serialized = json.dumps(
        payload,
        cls=DjangoJSONEncoder,
        ensure_ascii=True,
        separators=(",", ":"),
    )

    return (
        serialized
        .replace("<", "\\u003C")
        .replace(">", "\\u003E")
        .replace("&", "\\u0026")
    )


def _canonical_deals_query_v298(
    page_number: int,
) -> str:
    if page_number <= 1:
        return ""

    return urlencode(
        {
            "page": page_number,
        }
    )


def build_public_deals_seo_context_v298(
    *,
    request: HttpRequest,
    page_obj: Page,
    listings: Sequence[Listing],
) -> dict:
    """
    Build deterministic SEO metadata for the rendered Deals page.

    Page one canonically resolves to ``/deals/``. Later valid pages canonically
    retain only their normalized ``page`` parameter. Requests containing
    tracking, unknown, duplicate, or redundant parameters remain usable but
    receive ``noindex,follow``.
    """

    page_number = int(page_obj.number)
    canonical_query = _canonical_deals_query_v298(
        page_number
    )

    deals_path = reverse(
        "listings:public_deals_v296"
    )

    canonical_path = deals_path

    if canonical_query:
        canonical_path = (
            f"{canonical_path}?{canonical_query}"
        )

    canonical_url = request.build_absolute_uri(
        canonical_path
    )

    requested_query = request.META.get(
        "QUERY_STRING",
        "",
    )

    is_canonical_request = (
        requested_query == canonical_query
    )

    if page_number == 1:
        seo_title = (
            "Deals | Classifieds Local"
        )
        seo_description = (
            PUBLIC_DEALS_META_DESCRIPTION_V298
        )
        collection_name = "Deals"
    else:
        seo_title = (
            f"Deals – Page {page_number} "
            "| Classifieds Local"
        )
        seo_description = (
            f"{PUBLIC_DEALS_META_DESCRIPTION_V298} "
            f"Page {page_number}."
        )
        collection_name = (
            f"Deals – Page {page_number}"
        )

    page_listings = list(
        listings
    )

    if page_obj.paginator.count:
        start_position = (
            page_obj.start_index()
        )
    else:
        start_position = 0

    item_list_elements = [
        {
            "@type": "ListItem",
            "position": (
                start_position + offset
            ),
            "url": request.build_absolute_uri(
                listing.get_absolute_url()
            ),
            "name": listing.title,
        }
        for offset, listing in enumerate(
            page_listings
        )
    ]

    site_root_url = request.build_absolute_uri(
        "/"
    )

    json_ld_payload = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": collection_name,
        "description": seo_description,
        "url": canonical_url,
        "inLanguage": "en",
        "isPartOf": {
            "@type": "WebSite",
            "name": PUBLIC_DEALS_SITE_NAME_V298,
            "url": site_root_url,
        },
        "mainEntity": {
            "@type": "ItemList",
            "itemListOrder": (
                "https://schema.org/"
                "ItemListOrderDescending"
            ),
            "numberOfItems": (
                page_obj.paginator.count
            ),
            "itemListElement": (
                item_list_elements
            ),
        },
    }

    return {
        "seo_title": seo_title,
        "seo_description": seo_description,
        "seo_canonical_url": canonical_url,
        "seo_robots": (
            "index,follow"
            if is_canonical_request
            else "noindex,follow"
        ),
        "seo_social_metadata": True,
        "seo_site_name": (
            PUBLIC_DEALS_SITE_NAME_V298
        ),
        "seo_og_type": "website",
        "seo_twitter_card": "summary",
        "seo_json_ld": _safe_json_ld_v298(
            json_ld_payload
        ),
        "public_deals_seo_metadata_v298": True,
    }
