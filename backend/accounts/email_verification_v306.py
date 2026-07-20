from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import (
    constant_time_compare,
    salted_hmac,
)

from .models import EmailVerificationState


V306_EMAIL_VERIFICATION_TOKEN_SALT = (
    "accounts.email-verification.v306"
)

V306_EMAIL_VERIFICATION_DIGEST_SALT = (
    "accounts.email-verification.digest.v306"
)


@dataclass(frozen=True)
class EmailVerificationRequestResultV306:
    status: str
    token: str = ""
    token_version: int = 0
    retry_after_seconds: int = 0


@dataclass(frozen=True)
class EmailVerificationConfirmationResultV306:
    status: str
    verified: bool = False


def _positive_setting_v306(
    name: str,
    default: int,
) -> int:
    value = getattr(
        settings,
        name,
        default,
    )

    if isinstance(value, bool):
        return default

    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default

    return normalized if normalized > 0 else default


def email_verification_token_max_age_seconds_v306() -> int:
    return _positive_setting_v306(
        "EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS",
        86400,
    )


def email_verification_resend_cooldown_seconds_v306() -> int:
    return _positive_setting_v306(
        "EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS",
        300,
    )


def normalize_email_snapshot_v306(
    value: Any,
) -> str:
    return str(value or "").strip()


def _email_digest_v306(
    email_snapshot: str,
) -> str:
    return salted_hmac(
        V306_EMAIL_VERIFICATION_DIGEST_SALT,
        email_snapshot,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def _synchronize_state_instance_v306(
    *,
    state: EmailVerificationState,
    user,
) -> EmailVerificationState:
    current_email = normalize_email_snapshot_v306(
        getattr(user, "email", "")
    )

    if state.email_snapshot == current_email:
        return state

    state.email_snapshot = current_email
    state.verified_at = None
    state.verification_method = ""
    state.last_requested_at = None
    state.token_version = int(
        state.token_version
        or 0
    ) + 1

    state.save(
        update_fields=[
            "email_snapshot",
            "verified_at",
            "verification_method",
            "last_requested_at",
            "token_version",
            "updated_at",
        ]
    )

    return state


@transaction.atomic
def synchronize_email_verification_state_v306(
    user,
) -> EmailVerificationState:
    current_email = normalize_email_snapshot_v306(
        getattr(user, "email", "")
    )

    state, _created = (
        EmailVerificationState.objects
        .select_for_update()
        .get_or_create(
            user=user,
            defaults={
                "email_snapshot": current_email,
            },
        )
    )

    return _synchronize_state_instance_v306(
        state=state,
        user=user,
    )


def email_is_verified_for_user_v306(
    user,
) -> bool:
    state = synchronize_email_verification_state_v306(
        user
    )

    return state.is_verified_for_current_email


def _build_email_verification_token_v306(
    *,
    user_id: int,
    token_version: int,
    email_snapshot: str,
) -> str:
    return signing.dumps(
        {
            "uid": int(user_id),
            "version": int(token_version),
            "email_digest": _email_digest_v306(
                email_snapshot
            ),
        },
        salt=V306_EMAIL_VERIFICATION_TOKEN_SALT,
        compress=True,
    )


@transaction.atomic
def prepare_email_verification_request_v306(
    user,
    *,
    now=None,
) -> EmailVerificationRequestResultV306:
    now = now or timezone.now()

    User = get_user_model()

    locked_user = (
        User._default_manager
        .select_for_update()
        .get(pk=user.pk)
    )

    state, _created = (
        EmailVerificationState.objects
        .select_for_update()
        .get_or_create(
            user=locked_user,
            defaults={
                "email_snapshot": (
                    normalize_email_snapshot_v306(
                        locked_user.email
                    )
                ),
            },
        )
    )

    state = _synchronize_state_instance_v306(
        state=state,
        user=locked_user,
    )

    if not state.email_snapshot:
        return EmailVerificationRequestResultV306(
            status="missing_email",
        )

    if state.is_verified_for_current_email:
        return EmailVerificationRequestResultV306(
            status="already_verified",
        )

    cooldown_seconds = (
        email_verification_resend_cooldown_seconds_v306()
    )

    if state.last_requested_at is not None:
        elapsed_seconds = max(
            (
                now
                - state.last_requested_at
            ).total_seconds(),
            0,
        )

        remaining_seconds = max(
            cooldown_seconds
            - elapsed_seconds,
            0,
        )

        if remaining_seconds > 0:
            return EmailVerificationRequestResultV306(
                status="cooldown",
                retry_after_seconds=max(
                    int(
                        math.ceil(
                            remaining_seconds
                        )
                    ),
                    1,
                ),
            )

    state.token_version = int(
        state.token_version
        or 0
    ) + 1
    state.last_requested_at = now

    state.save(
        update_fields=[
            "token_version",
            "last_requested_at",
            "updated_at",
        ]
    )

    token = _build_email_verification_token_v306(
        user_id=locked_user.pk,
        token_version=state.token_version,
        email_snapshot=state.email_snapshot,
    )

    return EmailVerificationRequestResultV306(
        status="sent",
        token=token,
        token_version=state.token_version,
    )


@transaction.atomic
def release_email_verification_request_after_delivery_failure_v306(
    user,
    *,
    token_version: int,
) -> bool:
    if (
        type(token_version) is not int
        or token_version <= 0
    ):
        return False

    User = get_user_model()

    locked_user = (
        User._default_manager
        .select_for_update()
        .get(pk=user.pk)
    )

    state = (
        EmailVerificationState.objects
        .select_for_update()
        .filter(user=locked_user)
        .first()
    )

    if state is None:
        return False

    state = _synchronize_state_instance_v306(
        state=state,
        user=locked_user,
    )

    if (
        state.is_verified_for_current_email
        or state.token_version != token_version
        or state.last_requested_at is None
    ):
        return False

    state.last_requested_at = None

    state.save(
        update_fields=[
            "last_requested_at",
            "updated_at",
        ]
    )

    return True


def _load_verification_payload_v306(
    token: str,
) -> dict[str, Any] | None:
    try:
        payload = signing.loads(
            token,
            salt=V306_EMAIL_VERIFICATION_TOKEN_SALT,
            max_age=(
                email_verification_token_max_age_seconds_v306()
            ),
        )
    except (
        signing.BadSignature,
        signing.SignatureExpired,
        TypeError,
        ValueError,
    ):
        return None

    if not isinstance(payload, dict):
        return None

    uid = payload.get("uid")
    version = payload.get("version")
    email_digest = payload.get("email_digest")

    if (
        type(uid) is not int
        or type(version) is not int
        or not isinstance(email_digest, str)
        or not email_digest
    ):
        return None

    return {
        "uid": uid,
        "version": version,
        "email_digest": email_digest,
    }


@transaction.atomic
def confirm_email_verification_v306(
    *,
    user,
    token: str,
    now=None,
) -> EmailVerificationConfirmationResultV306:
    payload = _load_verification_payload_v306(
        token
    )

    if payload is None:
        return EmailVerificationConfirmationResultV306(
            status="invalid_or_expired",
        )

    if payload["uid"] != user.pk:
        return EmailVerificationConfirmationResultV306(
            status="invalid_or_expired",
        )

    User = get_user_model()

    locked_user = (
        User._default_manager
        .select_for_update()
        .get(pk=user.pk)
    )

    state, _created = (
        EmailVerificationState.objects
        .select_for_update()
        .get_or_create(
            user=locked_user,
            defaults={
                "email_snapshot": (
                    normalize_email_snapshot_v306(
                        locked_user.email
                    )
                ),
            },
        )
    )

    state = _synchronize_state_instance_v306(
        state=state,
        user=locked_user,
    )

    expected_digest = _email_digest_v306(
        state.email_snapshot
    )

    if (
        not state.email_snapshot
        or payload["version"] != state.token_version
        or not constant_time_compare(
            payload["email_digest"],
            expected_digest,
        )
    ):
        return EmailVerificationConfirmationResultV306(
            status="invalid_or_expired",
        )

    state.verified_at = now or timezone.now()
    state.verification_method = (
        EmailVerificationState.METHOD_SIGNED_LINK_V306
    )
    state.token_version = int(
        state.token_version
        or 0
    ) + 1

    state.save(
        update_fields=[
            "verified_at",
            "verification_method",
            "token_version",
            "updated_at",
        ]
    )

    return EmailVerificationConfirmationResultV306(
        status="verified",
        verified=True,
    )


__all__ = [
    "EmailVerificationConfirmationResultV306",
    "EmailVerificationRequestResultV306",
    "V306_EMAIL_VERIFICATION_TOKEN_SALT",
    "confirm_email_verification_v306",
    "email_is_verified_for_user_v306",
    "email_verification_resend_cooldown_seconds_v306",
    "email_verification_token_max_age_seconds_v306",
    "normalize_email_snapshot_v306",
    "prepare_email_verification_request_v306",
    "release_email_verification_request_after_delivery_failure_v306",
    "synchronize_email_verification_state_v306",
]
