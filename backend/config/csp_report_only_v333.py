"""Environment-controlled CSP Report-Only policy rollout for v333."""

from __future__ import annotations

from urllib.parse import urlsplit

from django.http import HttpRequest, HttpResponse

from config.csp_nonce_v332 import (
    CSP_NONCE_PATTERN_V332,
    ensure_request_csp_nonce_v332,
)


CSP_REPORT_ONLY_HEADER_V333 = "Content-Security-Policy-Report-Only"
CSP_ENFORCEMENT_HEADER_V333 = "Content-Security-Policy"
CSP_REPORT_ONLY_HEADER_ROLLOUT_V333 = True


def normalize_csp_report_uri_v333(value: str | None) -> str:
    """
    Accept a same-origin absolute path or credential-free HTTPS collector URI.

    Header delimiters, control characters, protocol-relative URLs, fragments,
    credentials, and cleartext external collectors are rejected.
    """

    normalized = (value or "").strip()

    if not normalized:
        return ""

    if any(
        character.isspace()
        or ord(character) < 0x20
        or ord(character) > 0x7E
        or ord(character) == 0x7F
        or character in {";", ",", "\\", '"', "'"}
        for character in normalized
    ):
        raise ValueError("CSP report URI contains an unsafe header character.")

    parsed = urlsplit(normalized)

    if normalized.startswith("/") and not normalized.startswith("//"):
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise ValueError("Same-origin CSP report URI must be a path.")
        return normalized

    if (
        parsed.scheme == "https"
        and parsed.netloc
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    ):
        return normalized

    raise ValueError(
        "CSP report URI must be a same-origin path or an HTTPS URI."
    )


def build_csp_report_only_policy_v333(
    *,
    nonce: str,
    report_uri: str = "",
) -> str:
    """Build the deterministic v333 policy using the request's v332 nonce."""

    if not CSP_NONCE_PATTERN_V332.fullmatch(nonce):
        raise ValueError("V333 requires a valid request-scoped CSP nonce.")

    normalized_report_uri = normalize_csp_report_uri_v333(report_uri)
    directives = [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        f"script-src 'self' 'nonce-{nonce}'",
        "script-src-attr 'none'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "media-src 'self' blob:",
        "frame-src 'none'",
        "worker-src 'self' blob:",
        "manifest-src 'self'",
    ]

    if normalized_report_uri:
        directives.append(f"report-uri {normalized_report_uri}")

    return "; ".join(directives)


class CspReportOnlyMiddlewareV333:
    """
    Add the v333 observation policy when enabled without enforcing it.

    A pre-existing Report-Only header is preserved so an upstream deployment
    layer remains authoritative.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        from django.conf import settings

        if not getattr(settings, "CSP_REPORT_ONLY_ENABLED", False):
            return response

        if response.has_header(CSP_REPORT_ONLY_HEADER_V333):
            return response

        nonce = ensure_request_csp_nonce_v332(request)
        response[CSP_REPORT_ONLY_HEADER_V333] = (
            build_csp_report_only_policy_v333(
                nonce=nonce,
                report_uri=getattr(
                    settings,
                    "CSP_REPORT_ONLY_REPORT_URI",
                    "",
                ),
            )
        )

        return response
