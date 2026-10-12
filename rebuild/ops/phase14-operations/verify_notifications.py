"""Read-only snapshot acceptance first; controlled resume writes only in synthetic-target."""
import json
import os
import sys
from pathlib import Path

progress = {'stage': 'identity', 'checks': 0}


def main():
    if os.environ.get('RECOVERY_ROLE') != 'synthetic-target' or os.environ.get('RECOVERY_RUN') != sys.argv[1] or sys.argv[2] not in ('catalog', 'resume'):
        raise ValueError('synthetic_target_required')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection, transaction
    from django.test import override_settings, Client
    from events.models import EventConsumption, OutboxEvent, PublicationBoundary
    from notifications.models import NotificationDelivery, NotificationMatch, SavedSearch
    from notifications.consumer import consume_pending, CONSUMER
    from snapshot_catalog import export_catalog
    from verify_original import compare_catalog
    from deployment import validate_deployment
    checks = 0
    def check(ok):
        nonlocal checks
        if not ok:
            raise ValueError('notification_restore_assertion')
        checks += 1
        progress['checks'] = checks
    check(settings.IN_APP_NOTIFICATIONS_ENABLED is False)
    expected = json.loads(Path('/run/recovery-catalog.json').read_bytes())
    check(bool(validate_deployment(expected.get('deployment'))))
    if sys.argv[2] == 'catalog':
        progress['stage'] = 'snapshot_catalog'
        connection.ensure_connection()
        with connection.connection.transaction():
            connection.connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            actual = export_catalog(connection.connection)
            progress['mismatchCounts'] = {field: sum(actual['tables'].get(t, {}).get(field) != row.get(field) for t, row in expected['tables'].items()) for field in ['count', 'sha256', 'schema', 'columns', 'constraints']}
            progress['otherCatalogMismatch'] = {field: actual.get(field) != expected.get(field) for field in ['migrations', 'sequences', 'publicationBoundary']}
            progress['constraintDifferences'] = []
            for table, row in expected['tables'].items():
                before = row['constraints']
                after = actual['tables'].get(table, {}).get('constraints', [])
                if before != after:
                    progress['constraintDifferences'].append({
                        'beforeCount': len(before), 'afterCount': len(after),
                        'sortedByNameEqual': sorted(before, key=lambda c: c['name']) == sorted(after, key=lambda c: c['name']),
                        'withoutNamesEqual': sorted((c['type'], c['definition'], c['validated']) for c in before) == sorted((c['type'], c['definition'], c['validated']) for c in after),
                        'changedTypes': sorted(set(c['type'] for c in before if c not in after)),
                    })
            compare_catalog(actual, expected)
            check(True)
            progress['stage'] = 'nonempty_notification_tables'
            for table in ['events_publicationboundary', 'events_eventconsumption', 'notifications_savedsearch', 'notifications_notificationdelivery', 'notifications_notificationmatch']:
                check(expected['tables'][table]['count'] > 0)
            progress['stage'] = 'consumer_states'
            check(set(EventConsumption.objects.values_list('status', flat=True)) == {'pending', 'retry', 'completed', 'skipped', 'failed'})
            progress['stage'] = 'read_archive_null_match'
            check(NotificationDelivery.objects.filter(read_at__isnull=False).exists())
            check(NotificationDelivery.objects.filter(archived_at__isnull=False).exists())
            check(NotificationMatch.objects.filter(search=None).exists())
        print(json.dumps({'pass': True, 'checks': checks, 'catalogOnly': True, 'consumerDisabled': True, 'deploymentBytesVerified': True}))
        return
    partial = OutboxEvent.objects.get(revision__title='Recovery notice partial')
    job = EventConsumption.objects.get(event=partial, consumer=CONSUMER)
    check(job.status == 'pending' and job.recipient_cursor > 0)
    check(NotificationDelivery.objects.filter(event=partial).count() == 20)
    old = list(NotificationDelivery.objects.order_by('pk').values_list('pk', 'read_at', 'archived_at'))
    protected = list(EventConsumption.objects.filter(status__in=['retry', 'failed', 'skipped']).order_by('pk').values_list('pk', 'status', 'attempts', 'next_attempt_at', 'reason', 'recipient_cursor'))
    from unittest.mock import patch
    from datetime import timedelta
    retry_deadline = EventConsumption.objects.get(status='retry').next_attempt_at
    # Test clock only; preserved DB retry time and attempts are never rewritten.
    with override_settings(IN_APP_NOTIFICATIONS_ENABLED=True), patch('notifications.consumer.timezone.now', return_value=retry_deadline - timedelta(microseconds=1)):
        consume_pending()
    job.refresh_from_db()
    check(job.status == 'completed')
    check(NotificationDelivery.objects.filter(event=partial).count() == 21)
    check(old == list(NotificationDelivery.objects.filter(pk__in=[r[0] for r in old]).order_by('pk').values_list('pk', 'read_at', 'archived_at')))
    check(protected == list(EventConsumption.objects.filter(pk__in=[r[0] for r in protected]).order_by('pk').values_list('pk', 'status', 'attempts', 'next_attempt_at', 'reason', 'recipient_cursor')))
    check(not NotificationDelivery.objects.filter(event=partial, recipient__email__in=['p13-21@example.test', 'p13-22@example.test', 'p13-23@example.test', 'p13-24@example.test']).exists())
    check(SavedSearch.objects.get(user__email='p13-21@example.test').notification_error == 'invalid_spec')
    count = NotificationDelivery.objects.count()
    with override_settings(IN_APP_NOTIFICATIONS_ENABLED=True), patch('notifications.consumer.timezone.now', return_value=retry_deadline - timedelta(microseconds=1)):
        consume_pending()
    check(NotificationDelivery.objects.count() == count)
    from accounts.models import User
    own = User.objects.get(email='p13-00@example.test')
    other = User.objects.get(email='p13-01@example.test')
    client = Client()
    client.force_login(other)
    own_delivery = NotificationDelivery.objects.filter(recipient=own).first()
    from notifications.services import mark_notification
    from django.http import Http404
    try:
        mark_notification(actor=other, delivery_id=own_delivery.pk)
    except Http404:
        check(True)
    else:
        check(False)
    from events.boundaries import next_publication_boundary
    before = PublicationBoundary.objects.get(pk=1).value
    with transaction.atomic():
        check(next_publication_boundary() == before + 1)
    check(PublicationBoundary.objects.get(pk=1).value > expected['publicationBoundary']['value'])
    print(json.dumps({'pass': True, 'checks': checks, 'syntheticWritesOnly': True, 'partialContinued': True, 'duplicateDelivery': False, 'readArchivePreserved': True, 'retryStatePreserved': True, 'beatEvidence': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        category = str(error) if type(error) is ValueError and str(error) in {'snapshot_catalog_mismatch', 'notification_schema_missing', 'notification_constraint_missing', 'notification_relation_missing', 'notification_restore_assertion', 'synthetic_target_required'} else 'notification_restore_failed'
        print(json.dumps({'pass': False, 'category': category, **progress}))
        sys.exit(1)
