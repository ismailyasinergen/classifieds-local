"""Bounded PostgreSQL consumer. Broker messages are wakeups, never completion records."""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Value, When
from django.utils import timezone

from accounts.locking import lock_users
from accounts.mfa_policy import verified_current_email
from events.models import EventConsumption, OutboxEvent
from listings.models import Listing
from listings.queries import public_listings
from listings.search.parsing import search_spec_from_dict, search_spec_to_dict
from listings.search.queries import matching_public_listings
from .models import NotificationDelivery, NotificationMatch, SavedSearch

CONSUMER = 'saved_search_in_app_v1'
RECIPIENT_BATCH = 20
JOB_BATCH = 10
MAX_ATTEMPTS = 5


def _limits():
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout = '3s'")
        cursor.execute("SET LOCAL statement_timeout = '5s'")


def discover():
    with transaction.atomic():
        _limits()
        existing = EventConsumption.objects.filter(event_id=OuterRef('pk'), consumer=CONSUMER)
        ids = list(OutboxEvent.objects.alias(seen=Exists(existing), priority=Case(
            When(payload__notification_version=1, then=Value(0)), default=Value(1), output_field=IntegerField()
        )).filter(seen=False).order_by('priority', 'pk').values_list('pk', flat=True)[:JOB_BATCH])
        EventConsumption.objects.bulk_create([EventConsumption(event_id=pk, consumer=CONSUMER) for pk in ids], ignore_conflicts=True)
    return len(ids)


def _event_boundary(event):
    payload = event.payload
    if event.event_type != OutboxEvent.Type.REVISION_PUBLISHED:
        return None, 'skipped', 'event_type_out_of_scope'
    if not isinstance(payload, dict) or 'notification_version' not in payload:
        return None, 'skipped', 'legacy_event'
    if type(payload.get('notification_version')) is not int or payload['notification_version'] != 1:
        return None, 'failed', 'unsupported_event'
    if payload.get('first_publication') is False:
        return None, 'skipped', 'not_first_publication'
    boundary = payload.get('publication_boundary')
    if (payload.get('first_publication') is not True or type(boundary) is not int or not 0 < boundary < 2**63
            or payload.get('revision_id') != event.revision_id or payload.get('listing_id') != str(event.revision.listing_id)):
        return None, 'failed', 'invalid_event'
    return boundary, None, None


def _finish(job, status, reason=''):
    job.status, job.reason = status, reason
    job.next_attempt_at = None
    job.save(update_fields=['status', 'reason', 'recipient_cursor', 'next_attempt_at', 'updated_at'])


def _deliver(job, event, listing, user, boundary):
    if user.pk == listing.owner_id or not user.is_active or not verified_current_email(user):
        return
    searches = SavedSearch.objects.filter(user=user, notifications_enabled=True, notification_boundary__lt=boundary).order_by('pk')
    for search in searches[:20]:
        try:
            spec = search_spec_from_dict(search.spec)
            if search_spec_to_dict(spec) != search.spec:
                raise ValidationError('invalid_spec')
        except (ValidationError, TypeError, ValueError):
            SavedSearch.objects.filter(pk=search.pk).update(notification_error='invalid_spec')
            continue
        if not matching_public_listings(spec=spec).filter(pk=listing.pk, public_revision_id=event.revision_id).exists():
            continue
        delivery, _ = NotificationDelivery.objects.get_or_create(event=event, recipient=user, channel='in_app', defaults={'listing': listing})
        NotificationMatch.objects.get_or_create(delivery=delivery, search=search, boundary=search.notification_boundary)


def _chunk(selected):
    with transaction.atomic():
        _limits()
        job = EventConsumption.objects.select_for_update(skip_locked=True).filter(
            consumer=CONSUMER, status__in=['pending', 'retry']).filter(
            Q(next_attempt_at=None) | Q(next_attempt_at__lte=timezone.now())).order_by('updated_at', 'pk').first()
        if job is None:
            return False
        selected[:] = [job.pk, job.recipient_cursor]
        event = OutboxEvent.objects.select_related('revision').get(pk=job.event_id)
        boundary, status, reason = _event_boundary(event)
        if status:
            _finish(job, status, reason)
            return True
        listing = Listing.objects.select_for_update().get(pk=event.revision.listing_id)
        if listing.public_revision_id != event.revision_id:
            _finish(job, 'skipped', 'superseded')
            return True
        ids = list(SavedSearch.objects.filter(notifications_enabled=True, notification_boundary__lt=boundary,
            user_id__gt=job.recipient_cursor).order_by('user_id').values_list('user_id', flat=True).distinct()[:RECIPIENT_BATCH])
        users = lock_users(user_ids=[listing.owner_id, *ids])
        if not public_listings().filter(pk=listing.pk, public_revision_id=event.revision_id).exists():
            _finish(job, 'skipped', 'not_public')
            return True
        for pk in ids:
            _deliver(job, event, listing, users[pk], boundary)
        if ids:
            job.recipient_cursor = ids[-1]
        _finish(job, 'pending' if len(ids) == RECIPIENT_BATCH else 'completed')
        return True


def _retry(selected, category):
    if not selected:
        raise RuntimeError('notification_consumer_unavailable') from None
    with transaction.atomic():
        _limits()
        job = EventConsumption.objects.select_for_update(skip_locked=True).filter(
            pk=selected[0], recipient_cursor=selected[1], status__in=['pending', 'retry']).first()
        if job is None:
            return
        job.attempts += 1
        job.status = 'failed' if job.attempts >= MAX_ATTEMPTS else 'retry'
        job.reason = category
        job.next_attempt_at = timezone.now() + timedelta(seconds=30 * 2**(job.attempts - 1)) if job.status == 'retry' else None
        job.save(update_fields=['attempts', 'status', 'reason', 'next_attempt_at', 'updated_at'])


def consume_pending():
    if not getattr(settings, 'IN_APP_NOTIFICATIONS_ENABLED', False):
        return {'status': 'disabled', 'chunks': 0}
    discover()
    chunks = 0
    for _ in range(JOB_BATCH):
        selected = []
        try:
            if not _chunk(selected):
                break
            chunks += 1
        except DatabaseError:
            _retry(selected, 'database_transient')
        except Exception:
            _retry(selected, 'processing_error')
    return {'status': 'processed', 'chunks': chunks}
