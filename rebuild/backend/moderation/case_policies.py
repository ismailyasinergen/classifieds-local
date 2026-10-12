from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied

from accounts.models import User


def require_case_actor(*, actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        raise PermissionDenied("Etkin ve e-postası doğrulanmış bir hesapla giriş yapın.")
    current = User.objects.filter(pk=actor.pk, is_active=True).first()
    if current is None or not EmailAddress.objects.filter(
            user_id=current.pk, email__iexact=current.email, verified=True).exists():
        raise PermissionDenied("Etkin ve e-postası doğrulanmış bir hesapla giriş yapın.")
    return current


def require_report_reviewer(*, actor, report=None):
    current = require_case_actor(actor=actor)
    if not current.has_perm("moderation.review_reports"):
        raise PermissionDenied("Bildirim inceleme izniniz yok.")
    if report is not None and current.pk in (report.reporter_id, report.subject_user_id):
        raise PermissionDenied("Tarafı olduğunuz dosyayı sonuçlandıramazsınız.")
    return current


def require_appeal_reviewer(*, actor, decision=None):
    current = require_case_actor(actor=actor)
    if not current.has_perm("moderation.review_appeals"):
        raise PermissionDenied("İtiraz inceleme izniniz yok.")
    if decision is not None and current.pk in (
            decision.actor_id, decision.report.reporter_id, decision.report.subject_user_id):
        raise PermissionDenied("İtirazı farklı ve taraf olmayan bir yetkili incelemelidir.")
    return current
