"""Request-scoped CSP nonce groundwork for v332."""

from __future__ import annotations

import re
import secrets

from django.http import HttpRequest, HttpResponse


CSP_NONCE_ATTRIBUTE_V332 = "csp_nonce_v332"
CSP_NONCE_BYTES_V332 = 32
CSP_NONCE_PATTERN_V332 = re.compile(r"^[A-Za-z0-9_-]{43}$")


def generate_csp_nonce_v332() -> str:
    """Return a URL-safe, 256-bit nonce suitable for a CSP nonce-source."""

    nonce = secrets.token_urlsafe(CSP_NONCE_BYTES_V332)

    if not CSP_NONCE_PATTERN_V332.fullmatch(nonce):
        raise RuntimeError("Generated v332 CSP nonce has an invalid shape.")

    return nonce


def ensure_request_csp_nonce_v332(request: HttpRequest) -> str:
    """Return one stable nonce for the lifetime of ``request``."""

    existing = getattr(request, CSP_NONCE_ATTRIBUTE_V332, None)

    if (
        isinstance(existing, str)
        and CSP_NONCE_PATTERN_V332.fullmatch(existing)
    ):
        return existing

    nonce = generate_csp_nonce_v332()
    setattr(request, CSP_NONCE_ATTRIBUTE_V332, nonce)

    return nonce


class CspNonceMiddlewareV332:
    """
    Attach a nonce before view/template processing without emitting CSP headers.

    Header rollout is intentionally outside v332. This middleware only creates
    the request-scoped value needed by nonce-aware dynamic template content.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        ensure_request_csp_nonce_v332(request)
        return self.get_response(request)
