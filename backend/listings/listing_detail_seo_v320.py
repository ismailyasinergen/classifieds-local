from __future__ import annotations

import json
import re
from html import unescape

from django.core.serializers.json import (
    DjangoJSONEncoder,
)
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Listing


LISTING_DETAIL_SEO_METADATA_V320 = True

LISTING_DETAIL_SITE_NAME_V320 = (
    "Classifieds Local"
)

LISTING_DETAIL_FALLBACK_IMAGE_V320 = (
    "listings/"
    "classifieds-local-social-preview-v320.png"
)


def _absolute_url_v320(
    request,
    value,
):
    value = str(value or "").strip()

    if not value:
        return ""

    if value.startswith(
        (
            "http://",
            "https://",
        )
    ):
        return value

    value = (
        "/"
        + value.lstrip("/")
    )

    return request.build_absolute_uri(
        value
    )


def _clean_text_v320(
    value,
):
    plain = unescape(
        strip_tags(
            str(value or "")
        )
    )

    return re.sub(
        r"\s+",
        " ",
        plain,
    ).strip()


def _truncate_text_v320(
    value,
    limit,
):
    value = _clean_text_v320(
        value
    )

    if len(value) <= limit:
        return value

    return (
        value[: limit - 1].rstrip()
        + "…"
    )


def _safe_json_ld_v320(
    payload,
):
    serialized = json.dumps(
        payload,
        cls=DjangoJSONEncoder,
        ensure_ascii=True,
        separators=(
            ",",
            ":",
        ),
    )

    return (
        serialized
        .replace(
            "<",
            "\\u003C",
        )
        .replace(
            ">",
            "\\u003E",
        )
        .replace(
            "&",
            "\\u0026",
        )
    )


def _listing_is_public_v320(
    listing,
):
    if (
        listing.status
        != Listing.Status.APPROVED
    ):
        return False

    if (
        listing.expires_at
        and listing.expires_at
        <= timezone.now()
    ):
        return False

    return True


def _listing_image_url_v320(
    request,
    listing,
):
    first_image = next(
        (
            image
            for image in listing.images.all()
            if getattr(
                image,
                "image",
                None,
            )
        ),
        None,
    )

    if first_image is not None:
        try:
            image_path = (
                first_image.image.url
            )
        except ValueError:
            image_path = ""
        else:
            if image_path:
                return _absolute_url_v320(
                    request,
                    image_path,
                )

    return _absolute_url_v320(
        request,
        static(
            LISTING_DETAIL_FALLBACK_IMAGE_V320
        ),
    )


def build_listing_detail_seo_context_v320(
    *,
    request,
    listing,
):
    canonical_url = (
        request.build_absolute_uri(
            listing.get_absolute_url()
        )
    )

    clean_title = _truncate_text_v320(
        listing.title,
        120,
    )

    clean_location = _truncate_text_v320(
        listing.location,
        80,
    )

    clean_description = (
        _truncate_text_v320(
            listing.description,
            115,
        )
    )

    summary_parts = [
        (
            f"{clean_title} in "
            f"{clean_location} for "
            f"{listing.price} TL."
        ),
    ]

    if clean_description:
        summary_parts.append(
            clean_description
        )

    seo_description = (
        _truncate_text_v320(
            " ".join(summary_parts),
            160,
        )
    )

    context = {
        "seo_title": (
            _truncate_text_v320(
                (
                    f"{clean_title} | "
                    f"{LISTING_DETAIL_SITE_NAME_V320}"
                ),
                180,
            )
        ),
        "seo_description": (
            seo_description
        ),
        "seo_canonical_url": (
            canonical_url
        ),
        "seo_site_name": (
            LISTING_DETAIL_SITE_NAME_V320
        ),
        "listing_detail_seo_metadata_v320": (
            True
        ),
    }

    if not _listing_is_public_v320(
        listing
    ):
        context.update(
            {
                "seo_robots": (
                    "noindex,nofollow"
                ),
                "seo_social_metadata": (
                    False
                ),
                "seo_image_url": "",
                "seo_image_alt": "",
                "seo_json_ld": "",
            }
        )

        return context

    image_url = (
        _listing_image_url_v320(
            request,
            listing,
        )
    )

    image_alt = _truncate_text_v320(
        (
            f"{clean_title} "
            "listing preview"
        ),
        160,
    )

    json_ld_payload = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": clean_title,
        "description": seo_description,
        "sku": str(listing.pk),
        "category": (
            str(listing.category)
        ),
        "url": canonical_url,
        "image": [
            image_url,
        ],
        "offers": {
            "@type": "Offer",
            "url": canonical_url,
            "priceCurrency": "TRY",
            "price": (
                format(
                    listing.price,
                    ".2f",
                )
            ),
            "availability": (
                "https://schema.org/"
                "InStock"
            ),
        },
    }

    context.update(
        {
            "seo_robots": (
                "index,follow"
            ),
            "seo_social_metadata": (
                True
            ),
            "seo_og_type": (
                "product"
            ),
            "seo_twitter_card": (
                "summary_large_image"
            ),
            "seo_image_url": (
                image_url
            ),
            "seo_image_alt": (
                image_alt
            ),
            "seo_json_ld": (
                _safe_json_ld_v320(
                    json_ld_payload
                )
            ),
        }
    )

    return context


class ListingDetailSeoContextMixinV320:
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context.update(
            build_listing_detail_seo_context_v320(
                request=self.request,
                listing=self.object,
            )
        )

        return context
