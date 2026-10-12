from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.locking import lock_users
from listings.policies import require_active_actor
from .models import MessagingRestriction


def messaging_restrictions(*, at=None):
    at = timezone.now() if at is None else at
    return MessagingRestriction.objects.filter(begins_at__lte=at, revoked_at__isnull=True).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gt=at))


def _require_permission(*, actor, current):
    require_active_actor(actor=actor)
    if not current.has_perm("moderation.restrict_messaging"):
        raise PermissionDenied("Mesajlaşma kısıtlama izniniz yok.")


def _actor_id(actor):
    if (not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False)
            or not getattr(actor, "pk", None)):
        raise PermissionDenied("Etkin bir hesapla giriş yapın.")
    return actor.pk


def restrict_messaging(*, actor, user_id, reason, ends_at=None):
    actor_id = _actor_id(actor)
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 2000:
        raise ValidationError({"reason": "Boş olmayan, en çok 2000 karakterlik gerekçe girin."})
    if ends_at is not None and (not isinstance(ends_at, datetime) or timezone.is_naive(ends_at)):
        raise ValidationError({"ends_at": "Saat dilimi içeren geçerli bir bitiş zamanı girin."})
    with transaction.atomic():
        users = lock_users(user_ids=[actor_id, user_id])
        _require_permission(actor=actor, current=users[actor_id])
        now = timezone.now()
        if ends_at is not None and ends_at < now:
            raise ValidationError({"ends_at": "Bitiş başlangıçtan önce olamaz."})
        return MessagingRestriction.objects.create(
            user=users[user_id], actor=users[actor_id], reason=reason.strip(),
            begins_at=now, ends_at=ends_at)


def revoke_messaging_restriction(*, actor, restriction_id):
    actor_id = _actor_id(actor)
    target_id = MessagingRestriction.objects.values_list("user_id", flat=True).get(pk=restriction_id)
    with transaction.atomic():
        users = lock_users(user_ids=[actor_id, target_id])
        restriction = MessagingRestriction.objects.select_for_update().get(pk=restriction_id)
        if restriction.user_id != target_id:
            raise ValidationError("Kısıt hedefi değişti.", code="identity_changed")
        _require_permission(actor=actor, current=users[actor_id])
        if restriction.revoked_at is None:
            restriction.revoked_at = timezone.now()
            restriction.save(update_fields=["revoked_at"])
        return restriction
