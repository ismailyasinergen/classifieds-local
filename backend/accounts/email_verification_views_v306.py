from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from .email_verification_v306 import (
    confirm_email_verification_v306,
    email_verification_resend_cooldown_seconds_v306,
    prepare_email_verification_request_v306,
    release_email_verification_request_after_delivery_failure_v306,
    synchronize_email_verification_state_v306,
)


@login_required
@require_GET
def email_verification_status_v306(
    request,
):
    state = synchronize_email_verification_state_v306(
        request.user
    )

    return render(
        request,
        "accounts/email_verification_status_v306.html",
        {
            "page_title": "Email verification",
            "verification_state": state,
            "current_email": state.email_snapshot,
            "is_email_verified": (
                state.is_verified_for_current_email
            ),
            "resend_cooldown_seconds": (
                email_verification_resend_cooldown_seconds_v306()
            ),
        },
    )


@login_required
@require_POST
def email_verification_resend_v306(
    request,
):
    result = prepare_email_verification_request_v306(
        request.user
    )

    if result.status == "missing_email":
        messages.error(
            request,
            "Add an email address before requesting verification.",
        )

    elif result.status == "already_verified":
        messages.info(
            request,
            "Your current email address is already verified.",
        )

    elif result.status == "cooldown":
        messages.info(
            request,
            (
                "A verification email was sent recently. "
                "Please try again later."
            ),
        )

    elif result.status == "sent":
        confirmation_url = request.build_absolute_uri(
            reverse(
                "accounts:email_verification_confirm_v306",
                kwargs={
                    "token": result.token,
                },
            )
        )

        try:
            delivered_count = send_mail(
                subject="Verify your email address",
                message=(
                    "Confirm that this email address belongs to your "
                    "account by opening the link below:\n\n"
                    f"{confirmation_url}\n\n"
                    "If you did not request this email, you can ignore it."
                ),
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    "webmaster@localhost",
                ),
                recipient_list=[
                    request.user.email,
                ],
                fail_silently=False,
            )

            if delivered_count != 1:
                raise RuntimeError(
                    "verification email was not accepted"
                )

        except Exception:
            release_email_verification_request_after_delivery_failure_v306(
                request.user,
                token_version=result.token_version,
            )

            messages.error(
                request,
                (
                    "The verification email could not be sent. "
                    "Please try again later."
                ),
            )
        else:
            messages.success(
                request,
                "A verification link was sent to your current email address.",
            )

    else:
        messages.error(
            request,
            "The verification request could not be completed.",
        )

    return redirect(
        "accounts:email_verification_status_v306"
    )


@login_required
@require_GET
def email_verification_confirm_v306(
    request,
    token,
):
    result = confirm_email_verification_v306(
        user=request.user,
        token=token,
    )

    if result.verified:
        messages.success(
            request,
            "Your current email address is now verified.",
        )
    else:
        messages.error(
            request,
            "This verification link is invalid or has expired.",
        )

    return redirect(
        "accounts:email_verification_status_v306"
    )
