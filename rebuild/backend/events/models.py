from django.db import models


class PublicationBoundary(models.Model):
    """Commit-serialized publication/subscription boundary; never a wall-clock cursor."""
    value = models.PositiveBigIntegerField(default=0)


class EventConsumption(models.Model):
    event = models.ForeignKey('OutboxEvent', on_delete=models.PROTECT, related_name='consumptions')
    consumer = models.CharField(max_length=40)
    status = models.CharField(max_length=12, default='pending', db_index=True)
    recipient_cursor = models.PositiveBigIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=40, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'consumer'], name='events_consumer_event_unique')]


class OutboxEvent(models.Model):
    class Type(models.TextChoices):
        REVISION_PUBLISHED = "listing.revision_published", "Revizyon yayımlandı"
        PRICE_CHANGED = "listing.price_changed", "Fiyat değişti"

    event_type = models.CharField(max_length=40, choices=Type.choices)
    revision = models.ForeignKey("listings.ListingRevision", on_delete=models.PROTECT, related_name="outbox_events")
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["event_type", "revision"], name="events_unique_type_revision"),
            models.CheckConstraint(condition=models.Q(event_type__in=["listing.revision_published", "listing.price_changed"]),
                                   name="events_valid_publication_type"),
        ]
