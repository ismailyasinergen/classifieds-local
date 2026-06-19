def unread_moderation_notice_count(request):
    if not request.user.is_authenticated:
        return {"unread_moderation_notice_count": 0}

    from .models import ModerationNotice

    return {
        "unread_moderation_notice_count": ModerationNotice.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
    }


def seller_restriction_status(request):
    if not request.user.is_authenticated:
        return {
            "current_user_seller_profile": None,
            "current_user_is_seller_suspended": False,
            "current_user_is_messaging_blocked": False,
        }

    from .models import UserProfile

    profile = UserProfile.objects.filter(user=request.user).first()

    return {
        "current_user_seller_profile": profile,
        "current_user_is_seller_suspended": bool(profile and profile.is_seller_suspended),
        "current_user_is_messaging_blocked": bool(profile and profile.is_seller_messaging_blocked),
    }


# STAFF_PENDING_APPEALS_BADGE_V1
def staff_pending_moderation_appeal_count(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated or not request.user.is_staff:
        return {"staff_pending_moderation_appeal_count": 0}

    try:
        from .models import ModerationAppeal
        count = ModerationAppeal.objects.filter(status=ModerationAppeal.Status.PENDING).count()
    except Exception:
        count = 0

    return {"staff_pending_moderation_appeal_count": count}
