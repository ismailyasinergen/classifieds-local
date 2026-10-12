def unread_notifications(request):
    if not request.user.is_authenticated or not request.user.is_active:
        return {}
    from accounts.mfa_policy import verified_current_email, requires_mfa, has_mfa_proof
    if not verified_current_email(request.user):
        return {}
    if requires_mfa(request.user) and not has_mfa_proof(request):
        return {}
    from .models import NotificationDelivery
    request.private_notification_context = True
    return {'unread_notification_count': NotificationDelivery.objects.filter(
        recipient=request.user, read_at=None, archived_at=None).count()}
