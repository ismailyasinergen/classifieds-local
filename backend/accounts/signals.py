from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .email_verification_v306 import (
    synchronize_email_verification_state_v306,
)
from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(
    sender,
    instance,
    created,
    raw=False,
    update_fields=None,
    **kwargs,
):
    if raw:
        return

    if created:
        UserProfile.objects.get_or_create(
            user=instance
        )

    if (
        created
        or update_fields is None
        or "email" in update_fields
    ):
        synchronize_email_verification_state_v306(
            instance
        )
