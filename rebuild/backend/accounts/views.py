from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification import send_verification_email_to_address
from allauth.core import ratelimit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .mfa_middleware import safe_return_path
from .mfa_policy import has_mfa_proof, primary_factor, requires_mfa, verified_current_email
from .models import User


@login_required
@require_GET
def security(request):
    return render(request, "accounts/security.html", {
        "mfa_required": requires_mfa(request.user),
        "primary": primary_factor(request.user),
        "email_verified": verified_current_email(request.user),
        "has_proof": has_mfa_proof(request),
        "return_path": safe_return_path(request, request.GET.get("next", "/")),
    })


@login_required
@require_http_methods(["GET", "POST"])
def verify_email(request):
    if verified_current_email(request.user):
        return redirect("accounts:security")
    if request.method == "POST":
        # Only the current address is eligible here; account/email management is
        # still protected. No address is automatically marked verified.
        limited = ratelimit.consume_or_429(request, action="manage_email", user=request.user)
        if limited:
            return limited
        user = User.objects.get(pk=request.user.pk, is_active=True)
        address, _ = EmailAddress.objects.get_or_create(user=user, email=user.email)
        # Pinned allauth 65.19.7 integration preserves confirm_email throttling
        # and email_confirmation_sent; direct model.send_confirmation bypasses it.
        if send_verification_email_to_address(request, address, signup=False):
            return redirect("account_email_verification_sent")
        messages.warning(request, "Biraz bekleyip tekrar deneyin. Yeni doğrulama bağlantısı gönderilmedi.")
    return render(request, "accounts/verify_email.html")
