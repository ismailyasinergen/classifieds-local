from django.db import transaction
from django.db.transaction import TransactionManagementError

from .models import User


def lock_users(*, user_ids):
    """Lock stable account anchors in one global order, inside an existing transaction."""
    if not transaction.get_connection().in_atomic_block:
        raise TransactionManagementError("Account locks require an active transaction.")
    ids = sorted(set(user_ids))
    users = {
        user.pk: user
        for user in User.objects.select_for_update(no_key=True).filter(pk__in=ids).order_by("pk")
    }
    if len(users) != len(ids):
        raise User.DoesNotExist("An account anchor no longer exists.")
    return users
