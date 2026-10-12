from datetime import timedelta
from math import ceil

from django.conf import settings
from django.core.checks import Error, register
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.db.transaction import TransactionManagementError


# The caller holds the actor's no-key User anchor throughout this transaction.
# These event reads never acquire locks on historical domain rows.
_ACTIONS = {
    "new_contact": ("PILOT_NEW_CONTACTS_PER_HOUR", 3600),
    "message": ("PILOT_MESSAGES_PER_HOUR", 3600),
    "new_listing": ("PILOT_NEW_LISTINGS_PER_DAY", 86400),
    "report": ("PILOT_REPORTS_PER_DAY", 86400),
    "appeal": ("PILOT_APPEALS_PER_DAY", 86400),
}
_MESSAGES = {
    "report": "Bildirim sınırına ulaştınız. %(seconds)s saniye sonra yeniden deneyin.",
    "appeal": "İtiraz sınırına ulaştınız. %(seconds)s saniye sonra yeniden deneyin.",
    "new_contact": "Yeni görüşme sınırına ulaştınız. %(seconds)s saniye sonra yeniden deneyin.",
    "message": "Mesaj gönderme sınırına ulaştınız. %(seconds)s saniye sonra yeniden deneyin.",
    "new_listing": (
        "Yeni ilan sınırına ulaştınız. %(seconds)s saniye sonra yeniden deneyin. "
        "Mevcut taslaklarınızı düzenlemeye devam edebilirsiniz."
    ),
}


class ActionRateLimited(ValidationError):
    def __init__(self, *, action, retry_after):
        if type(retry_after) is not int or retry_after < 1:
            raise ValueError("retry_after must be a positive integer.")
        self.action = action
        self.retry_after = retry_after
        super().__init__(_MESSAGES[action], code="action_rate_limited",
                         params={"seconds": retry_after})


def _invalid_settings():
    return [
        name for name, window in _ACTIONS.values()
        if type(getattr(settings, name, None)) is not int
        or not 1 <= getattr(settings, name) <= 10000
    ]


@register()
def check_activity_limits(app_configs, **kwargs):
    return [
        Error(f"{name} must be an integer from 1 through 10000.", id="accounts.E001")
        for name in _invalid_settings()
    ]


def enforce_action_limit(*, events, action, at) -> None:
    if not transaction.get_connection(using=events.db).in_atomic_block:
        raise TransactionManagementError("Activity limits require an active transaction.")
    invalid = _invalid_settings()
    if invalid:
        raise ImproperlyConfigured(
            "Invalid pilot activity capacity: " + ", ".join(invalid) +
            "; each must be an integer from 1 through 10000.")
    name, seconds = _ACTIONS[action]
    capacity = getattr(settings, name)
    window = timedelta(seconds=seconds)
    recent = list(
        events.filter(created_at__gt=at - window).order_by("-created_at", "-pk")
        .values_list("created_at", flat=True)[:capacity]
    )
    if len(recent) == capacity:
        retry_after = max(1, ceil((recent[-1] + window - at).total_seconds()))
        raise ActionRateLimited(action=action, retry_after=retry_after)
