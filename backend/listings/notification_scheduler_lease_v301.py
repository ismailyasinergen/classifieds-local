"""
PostgreSQL session-level notification scheduler leases for v301.

These leases coordinate expensive scheduler runs. Durable v287 logical-event
claims remain the notification-delivery correctness boundary.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import re

from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import DatabaseError, NotSupportedError


NOTIFICATION_SCHEDULER_LEASE_V301 = True

LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301 = (
    "listing-price-alert-notifications"
)
SAVED_SEARCH_SCHEDULER_LEASE_NAME_V301 = (
    "saved-search-notifications"
)

_LEASE_NAME_PATTERN_V301 = re.compile(
    r"^[a-z0-9][a-z0-9._:-]{0,127}$"
)
_LEASE_NAMESPACE_V301 = (
    "classifieds-local:notification-scheduler:v301:"
)


@dataclass(frozen=True)
class NotificationSchedulerLeaseV301:
    lease_name: str
    lock_key: tuple[int, int]
    connection_alias: str
    acquired: bool


def normalize_notification_scheduler_lease_name_v301(
    lease_name,
):
    normalized = str(lease_name or "").strip().lower()

    if not _LEASE_NAME_PATTERN_V301.fullmatch(normalized):
        raise ValueError(
            "Scheduler lease names must contain only lowercase "
            "letters, digits, dots, underscores, colons or hyphens "
            "and be at most 128 characters."
        )

    return normalized


def build_notification_scheduler_lock_key_v301(
    lease_name,
):
    normalized = (
        normalize_notification_scheduler_lease_name_v301(
            lease_name
        )
    )
    digest = hashlib.sha256(
        (
            _LEASE_NAMESPACE_V301
            + normalized
        ).encode("utf-8")
    ).digest()

    return (
        int.from_bytes(
            digest[:4],
            byteorder="big",
            signed=True,
        ),
        int.from_bytes(
            digest[4:8],
            byteorder="big",
            signed=True,
        ),
    )


def try_acquire_notification_scheduler_lease_v301(
    lease_name,
    *,
    using=DEFAULT_DB_ALIAS,
):
    normalized = (
        normalize_notification_scheduler_lease_name_v301(
            lease_name
        )
    )
    lock_key = (
        build_notification_scheduler_lock_key_v301(
            normalized
        )
    )
    database_connection = connections[using]

    if database_connection.vendor != "postgresql":
        raise NotSupportedError(
            "Notification scheduler leases require PostgreSQL."
        )

    with database_connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_try_advisory_lock(%s, %s)",
            list(lock_key),
        )
        acquired = bool(cursor.fetchone()[0])

    return NotificationSchedulerLeaseV301(
        lease_name=normalized,
        lock_key=lock_key,
        connection_alias=using,
        acquired=acquired,
    )


def release_notification_scheduler_lease_v301(
    lease,
):
    if not lease.acquired:
        return False

    database_connection = connections[
        lease.connection_alias
    ]

    try:
        with database_connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_unlock(%s, %s)",
                list(lease.lock_key),
            )
            return bool(cursor.fetchone()[0])
    except DatabaseError:
        # A dead/closed PostgreSQL session already releases its
        # session advisory locks. Do not hide the command's original
        # exception with a cleanup exception.
        database_connection.close()
        return False


@contextmanager
def notification_scheduler_lease_v301(
    lease_name,
    *,
    using=DEFAULT_DB_ALIAS,
):
    lease = (
        try_acquire_notification_scheduler_lease_v301(
            lease_name,
            using=using,
        )
    )

    try:
        yield lease
    finally:
        if lease.acquired:
            release_notification_scheduler_lease_v301(
                lease
            )
