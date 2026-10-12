"""MFA is a browser boundary: unsafe requests are never retained or replayed."""
from urllib.parse import urlsplit, urlencode

from allauth.core.exceptions import ReauthenticationRequired
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import url_has_allowed_host_and_scheme
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from .mfa_adapter import MFAStorageError
from .mfa_policy import (
    RECENT_MFA_MAX_AGE, has_mfa_proof, primary_factor, requires_mfa,
    verified_current_email,
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_VIEWS = {"listings:index", "listings:detail", "listings:public_image", "storefronts:public", "health"}
REMEDIATION_VIEWS = {
    "accounts:security", "accounts:verify_email", "account_logout",
    "account_confirm_email", "account_email_verification_sent",
}
RECENT_VIEWS = {
    "mfa_deactivate_totp", "mfa_view_recovery_codes",
    "mfa_generate_recovery_codes", "mfa_download_recovery_codes",
}


def private_headers(response):
    response["Cache-Control"] = "private, no-store"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    # no-referrer makes native form POST Origin opaque/null in browsers.
    # Keep CSRF origin proof without sending referrers to other origins.
    response["Referrer-Policy"] = "same-origin"
    return response


def safe_return_path(request, candidate=None):
    candidate = candidate if candidate is not None else request.get_full_path()
    if not candidate or not url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return reverse("accounts:security")
    parsed = urlsplit(candidate)
    path = (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
    # Removing an allowed origin can expose a new //authority or /\\authority.
    # Revalidate the actual link with no permitted authority, not only its input.
    if not url_has_allowed_host_and_scheme(
        path, allowed_hosts=set(), require_https=request.is_secure(),
    ):
        return reverse("accounts:security")
    return path


def remediation(request, target, *, next_path=None):
    destination = reverse(target)
    if request.method in SAFE_METHODS:
        return private_headers(HttpResponseRedirect(
            destination + "?" + urlencode({"next": safe_return_path(request, next_path)}),
        ))
    return private_headers(render(request, "accounts/mfa_required.html", {
        "remediation_url": destination,
    }, status=403))


class MFABoundaryMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        name = request.resolver_match.view_name
        if name.startswith("mfa_"):
            # Avoid resuming a historical stock suspended mutation after MFA.
            request.session.pop("account_reauthentication_state", None)
        if not request.user.is_authenticated:
            return None
        primary = primary_factor(request.user)
        verified = verified_current_email(request.user)
        if name in RECENT_VIEWS:
            if not verified:
                return remediation(request, "accounts:verify_email")
            if not primary:
                return remediation(request, "mfa_activate_totp")
            if not has_mfa_proof(request, max_age=RECENT_MFA_MAX_AGE):
                return remediation(request, "mfa_reauthenticate")
        if name == "mfa_activate_totp" and not verified:
            return remediation(request, "accounts:verify_email")
        if not requires_mfa(request.user):
            return None
        if name in REMEDIATION_VIEWS:
            return None
        if request.method in SAFE_METHODS and (
            name in PUBLIC_VIEWS or request.path.startswith("/static/")
        ):
            return None
        if not verified:
            return remediation(request, "accounts:verify_email")
        if not primary:
            if name in {"mfa_activate_totp", "account_reauthenticate", "mfa_index"}:
                return None
            return remediation(request, "mfa_activate_totp")
        if name in {"mfa_reauthenticate", "mfa_index"}:
            return None
        if not has_mfa_proof(request):
            return remediation(request, "mfa_reauthenticate")
        return None

    def process_exception(self, request, exception):
        # This middleware follows AccountMiddleware, so this handler runs first.
        # Stock allauth otherwise serializes and later replays an original POST.
        if isinstance(exception, ReauthenticationRequired):
            target = "mfa_reauthenticate" if primary_factor(request.user) else "account_reauthenticate"
            return remediation(request, target)
        if isinstance(exception, (RedisConnectionError, RedisTimeoutError, MFAStorageError)):
            return private_headers(render(request, "accounts/security_unavailable.html", status=503))
        return None

    def process_response(self, request, response):
        if (getattr(request, "private_notification_context", False)
                or request.path.startswith(("/accounts/", "/admin/", "/private-media/", "/inceleme/",
                                            "/favorilerim/", "/kayitli-aramalarim/", "/vitrinim/", "/vitrin/"))):
            private_headers(response)
        return response
