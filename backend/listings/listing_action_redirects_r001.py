"""Safe return targets for authenticated listing actions."""

from __future__ import annotations

from django.utils.http import url_has_allowed_host_and_scheme


SAFE_LISTING_ACTION_REDIRECTS_R001 = True


def get_safe_listing_action_redirect_r001(request, fallback_url: str) -> str:
    """Return a same-origin POST target or the supplied local fallback."""

    next_url = str(request.POST.get("next", "") or "").strip()
    if not next_url:
        return fallback_url

    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return fallback_url
