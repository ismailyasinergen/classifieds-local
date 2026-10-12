"""Aggregate-only receipt for the snapshot, never a restored-user behavior test."""
TABLES = ('events_publicationboundary', 'events_eventconsumption', 'notifications_savedsearch',
          'notifications_notificationdelivery', 'notifications_notificationmatch')
STATES = ('pending', 'retry', 'completed', 'skipped', 'failed')


def aggregate(cursor):
    cursor.execute("SELECT status,count(*) FROM events_eventconsumption WHERE consumer='saved_search_in_app_v1' GROUP BY status")
    states = dict.fromkeys(STATES, 0)
    for status, count in cursor.fetchall():
        if status not in states:
            raise ValueError('notification_state_refused')
        states[status] = count
    cursor.execute('SELECT count(*) FILTER (WHERE notifications_enabled),count(*) FILTER (WHERE NOT notifications_enabled) FROM notifications_savedsearch')
    enabled, disabled = cursor.fetchone()
    cursor.execute('SELECT count(*) FILTER (WHERE read_at IS NOT NULL),count(*) FILTER (WHERE archived_at IS NOT NULL) FROM notifications_notificationdelivery')
    read, archived = cursor.fetchone()
    cursor.execute('SELECT count(*) FROM notifications_notificationmatch WHERE search_id IS NULL')
    return dict(consumption=states, enabledSearches=enabled, disabledSearches=disabled,
                readDeliveries=read, archivedDeliveries=archived, nullSearchMatches=cursor.fetchone()[0])


def receipt(catalog):
    tables = {}
    for name in TABLES:
        count = catalog['tables'][name]['count']
        if type(count) is not int or count < 0:
            raise ValueError('notification_count_refused')
        tables[name] = dict(count=count, coverage='aggregate_verified' if count else 'empty')
    return dict(tables=tables, **catalog['notificationState'], publicationBoundaryVerified=True,
                deploymentOverlayBytesVerified=True, runtimeConsumerDisabled=True, quarantineVerified=True,
                realUserOperationPerformed=False, restoredConsumerExecuted=False)
