"""Project-wide template context processors."""

from config.csp_nonce_v332 import ensure_request_csp_nonce_v332


def csp_nonce_v332(request):
    """Expose the request-scoped nonce to nonce-aware template blocks."""

    return {
        "csp_nonce_v332": ensure_request_csp_nonce_v332(request),
    }
