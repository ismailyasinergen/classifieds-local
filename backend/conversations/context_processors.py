from .models import ListingMessage


def unread_message_count(request):
    if not request.user.is_authenticated:
        return {
            "unread_message_count": 0,
        }

    return {
        "unread_message_count": ListingMessage.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count(),
    }
