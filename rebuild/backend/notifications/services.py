from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.locking import lock_users
from listings.favorites import require_private_actor
from listings.policies import require_active_actor
from listings.search.parsing import search_spec_from_dict, search_spec_to_dict, search_querystring
from .forms import SearchNameForm
from .models import SavedSearch


@transaction.atomic
def set_notifications(*, actor, search_id, enabled):
    from events.boundaries import next_publication_boundary
    current = lock_users(user_ids=[actor.pk])[actor.pk]
    require_private_actor(current)
    row = get_object_or_404(SavedSearch, pk=search_id, user=current)
    if row.notifications_enabled == enabled:
        return row
    if enabled:
        spec = search_spec_from_dict(row.spec)
        if search_spec_to_dict(spec) != row.spec:
            raise ValidationError('Kayıtlı arama geçersiz; bildirim açılamadı.')
        row.notification_boundary = next_publication_boundary()
        row.notifications_enabled_at = timezone.now()
        row.notification_error = ''
    row.notifications_enabled = enabled
    row.save(update_fields=['notifications_enabled', 'notification_boundary', 'notifications_enabled_at', 'notification_error'])
    return row


@transaction.atomic
def mark_notification(*, actor, delivery_id, archive=False):
    from .models import NotificationDelivery
    current = lock_users(user_ids=[actor.pk])[actor.pk]
    require_private_actor(current)
    row = get_object_or_404(NotificationDelivery, pk=delivery_id, recipient=current)
    field = 'archived_at' if archive else 'read_at'
    if getattr(row, field) is None:
        setattr(row, field, timezone.now())
        row.save(update_fields=[field])
    return row

SAVED_SEARCH_LIMIT = 20


def validated_name(name):
    form = SearchNameForm({"name": name})
    if not form.is_valid():
        raise ValidationError("Arama adı 1–80 karakter olmalıdır.")
    return form.cleaned_data["name"]


@transaction.atomic
def save_search(*, actor, name, payload):
    require_active_actor(actor=actor)
    lock_users(user_ids=[actor.pk])
    require_private_actor(actor)
    name = validated_name(name)
    spec = search_spec_from_dict(payload)
    search_querystring(spec)
    canonical = search_spec_to_dict(spec)
    # The bounded private list avoids a hash-only equality decision.
    rows = list(SavedSearch.objects.filter(user=actor)[:SAVED_SEARCH_LIMIT + 1])
    for row in rows:
        if row.spec == canonical:
            return row, False
    if len(rows) >= SAVED_SEARCH_LIMIT:
        raise ValidationError("En fazla 20 arama saklayabilirsiniz. Önce bir kaydı silin.")
    return SavedSearch.objects.create(user=actor, name=name, spec=canonical), True


@transaction.atomic
def rename_search(*, actor, search_id, name):
    require_active_actor(actor=actor)
    lock_users(user_ids=[actor.pk])
    require_private_actor(actor)
    row = get_object_or_404(SavedSearch, pk=search_id, user=actor)
    row.name = validated_name(name)
    row.save(update_fields=["name"])
    return row


@transaction.atomic
def delete_search(*, actor, search_id):
    require_active_actor(actor=actor)
    lock_users(user_ids=[actor.pk])
    require_private_actor(actor)
    # Ownership is checked even for a forged identifier; no other row is touched.
    row = get_object_or_404(SavedSearch, pk=search_id, user=actor)
    row.delete()
