from django.conf import settings
from django.db import models


class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=80)
    spec = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    notifications_enabled = models.BooleanField(default=False)
    notification_boundary = models.PositiveBigIntegerField(null=True, blank=True)
    notifications_enabled_at = models.DateTimeField(null=True, blank=True)
    notification_error = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["user", "-created_at", "-id"], name="saved_search_user_recent_idx")]


class NotificationDelivery(models.Model):
    event = models.ForeignKey('events.OutboxEvent', on_delete=models.PROTECT)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    channel = models.CharField(max_length=12, default='in_app', editable=False)
    listing = models.ForeignKey('listings.Listing', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['event', 'recipient', 'channel'], name='notification_event_recipient_channel'),
            models.CheckConstraint(condition=models.Q(channel='in_app'), name='notification_in_app_only'),
        ]
        indexes = [models.Index(fields=['recipient', '-created_at', '-id'], name='notification_recipient_recent')]


class NotificationMatch(models.Model):
    delivery = models.ForeignKey(NotificationDelivery, on_delete=models.CASCADE, related_name='matches')
    search = models.ForeignKey(SavedSearch, null=True, on_delete=models.SET_NULL)
    boundary = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['delivery', 'search', 'boundary'], name='notification_match_unique')]
