from django.core.exceptions import PermissionDenied
from accounts.models import User


def require_active_actor(*, actor):
    if (not getattr(actor, "is_authenticated", False)
            or not getattr(actor, "is_active", False)
            or not getattr(actor, "pk", None)
            or not User.objects.filter(pk=actor.pk, is_active=True).exists()):
        raise PermissionDenied("Etkin bir hesapla giriş yapın.")


def require_owner(*, actor, listing):
    require_active_actor(actor=actor)
    if listing.owner_id != actor.pk:
        raise PermissionDenied("Bu ilanı düzenleme yetkiniz yok.")
