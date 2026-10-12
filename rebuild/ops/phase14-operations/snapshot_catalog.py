import base64
import datetime
import decimal
import hashlib
import json
import math
import uuid


def canonical(value):
    def typed(v):
        if v is None or isinstance(v, (bool, int, str)):
            return [type(v).__name__, v]
        if isinstance(v, float):
            if not math.isfinite(v):
                raise ValueError('catalog_nonfinite')
            return ['float', v.hex()]
        if isinstance(v, decimal.Decimal):
            if not v.is_finite():
                raise ValueError('catalog_nonfinite')
            return ['decimal', str(v)]
        if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
            return [type(v).__name__, v.isoformat()]
        if isinstance(v, uuid.UUID):
            return ['uuid', v.hex]
        if isinstance(v, (bytes, bytearray, memoryview)):
            return ['bytes', base64.b64encode(v).decode('ascii')]
        if isinstance(v, (list, tuple)):
            return ['array', [typed(item) for item in v]]
        if isinstance(v, dict) and all(isinstance(k, str) for k in v):
            return ['object', [[k, typed(v[k])] for k in sorted(v)]]
        raise ValueError('catalog_type_refused')
    encoded = json.dumps(typed(value), ensure_ascii=False, separators=(',', ':')).encode('utf8')
    if len(encoded) > 32 * 1024 * 1024:
        raise ValueError('catalog_row_capacity')
    return encoded


def require_phase10_catalog(catalog):
    for table, migration in (('listings_favorite', ['listings', '0006_favorite']),
                             ('notifications_savedsearch', ['notifications', '0001_initial'])):
        if (table not in catalog.get('tables', {}) or migration not in catalog.get('migrations', [])
                or not any(s.get('table') == table and s.get('column') == 'id' for s in catalog.get('sequences', []))):
            raise ValueError('phase10_schema_missing')
    required = {
        'events_publicationboundary': {'id', 'value'},
        'events_eventconsumption': {'id', 'event_id', 'consumer', 'status', 'recipient_cursor', 'attempts', 'next_attempt_at', 'reason', 'updated_at'},
        'notifications_savedsearch': {'id', 'user_id', 'name', 'spec', 'notifications_enabled', 'notification_boundary', 'notifications_enabled_at', 'notification_error'},
        'notifications_notificationdelivery': {'id', 'event_id', 'recipient_id', 'channel', 'listing_id', 'read_at', 'archived_at', 'created_at'},
        'notifications_notificationmatch': {'id', 'delivery_id', 'search_id', 'boundary'},
    }
    for table, columns in required.items():
        entry = catalog.get('tables', {}).get(table, {})
        if not columns.issubset(entry.get('columns', [])) or not entry.get('constraints'):
            raise ValueError('notification_schema_missing')
        if not any(s.get('table') == table and s.get('column') == 'id' for s in catalog.get('sequences', [])):
            raise ValueError('notification_sequence_missing')
    for migration in [['events', '0002_publicationboundary_eventconsumption'], ['notifications', '0002_in_app_notifications']]:
        if migration not in catalog.get('migrations', []):
            raise ValueError('notification_migration_missing')
    constraints = [c for t in required for c in catalog['tables'][t]['constraints']]
    for name in ['events_consumer_event_unique', 'notification_event_recipient_channel', 'notification_in_app_only', 'notification_match_unique']:
        if not any(c['name'] == name and c['validated'] for c in constraints):
            raise ValueError('notification_constraint_missing')
    for table, targets in {
        'events_eventconsumption': ['events_outboxevent'],
        'notifications_savedsearch': ['accounts_user'],
        'notifications_notificationdelivery': ['events_outboxevent', 'accounts_user', 'listings_listing'],
        'notifications_notificationmatch': ['notifications_notificationdelivery', 'notifications_savedsearch'],
    }.items():
        for target in targets:
            if not any(c['type'] == 'f' and c['validated'] and ('REFERENCES ' + target + '(') in c['definition'] for c in catalog['tables'][table]['constraints']):
                raise ValueError('notification_relation_missing')
    boundary = catalog.get('publicationBoundary')
    if not isinstance(boundary, dict) or boundary.get('rows') not in (0, 1) or (boundary['rows'] == 1 and type(boundary.get('value')) is not int):
        raise ValueError('publication_boundary_missing')
    if (not isinstance(boundary.get('idSequence'), dict) or type(boundary['idSequence'].get('last')) is not int
            or type(boundary['idSequence'].get('called')) is not bool
            or (boundary['rows'] == 1 and (boundary.get('minId') != 1 or boundary.get('maxId') != 1))):
        raise ValueError('publication_boundary_sequence_missing')
    from storefront_coverage import validate
    validate(catalog)
    if (catalog.get('format') != 3 or catalog.get('constraintProfile') != 'pg17.11-public-enum-v2'
            or catalog.get('serverVersion') != 170011):
        raise ValueError('catalog_version_refused')
    return True


def export_catalog(connection):
    from psycopg import sql
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
        tables = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT current_setting('server_version_num')::int")
        result = {'format': 3, 'constraintProfile': 'pg17.11-public-enum-v2', 'serverVersion': cursor.fetchone()[0], 'tables': {}, 'sequences': []}
        for table in tables:
            cursor.execute("SELECT column_name, data_type, is_nullable, column_default, udt_schema, udt_name, character_maximum_length, collation_schema, collation_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,))
            columns = cursor.fetchall()
            cursor.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) WHERE i.indrelid=%s::regclass AND i.indisprimary ORDER BY a.attnum", ('public.' + table,))
            pk = [r[0] for r in cursor.fetchall()]
            if not pk:
                raise ValueError('catalog_primary_key_required')
            digest, count = hashlib.sha256(), 0
            with connection.cursor(name='phase7_catalog_rows') as rows:
                rows.execute(sql.SQL('SELECT * FROM {}.{} ORDER BY {}').format(sql.Identifier('public'), sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, pk))))
                for row in rows:
                    data = canonical(row)
                    digest.update(len(data).to_bytes(8, 'big'))
                    digest.update(data)
                    count += 1
            cursor.execute('SELECT conname,contype,pg_get_constraintdef(oid),convalidated,condeferrable,condeferred,conislocal,coninhcount,connoinherit FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname', ('public.' + table,))
            constraints = [dict(zip(('name', 'type', 'definition', 'validated', 'deferrable', 'deferred', 'islocal', 'inhcount', 'noinherit'), r)) for r in cursor.fetchall()]
            result['tables'][table] = {'count': count, 'sha256': digest.hexdigest(), 'schema': hashlib.sha256(canonical(columns)).hexdigest(), 'columns': [c[0] for c in columns], 'constraints': constraints}
            if table == 'accounts_storefront':
                result['tables'][table]['columnMetadata'] = [list(c) for c in columns]
            for column in columns:
                col = column[0]
                cursor.execute('SELECT pg_get_serial_sequence(%s,%s)', ('public.' + table, col))
                seq = cursor.fetchone()[0]
                if seq:
                    cursor.execute(sql.SQL('SELECT max({}) FROM {}.{}').format(sql.Identifier(col), sql.Identifier('public'), sql.Identifier(table)))
                    result['sequences'].append({'table': table, 'column': col, 'sequence': seq, 'max': cursor.fetchone()[0]})
        cursor.execute('SELECT app,name FROM django_migrations ORDER BY app,name')
        result['migrations'] = [list(r) for r in cursor.fetchall()]
        cursor.execute('SELECT original,derivative,state,source_bytes,storage_key FROM media_mediaasset ORDER BY id')
        result['assets'] = [{'original': r[0], 'derivative': r[1], 'state': r[2], 'source_bytes': r[3], 'key': r[4].hex} for r in cursor.fetchall()]
        cursor.execute('SELECT count(*),max(value),min(id),max(id) FROM events_publicationboundary')
        boundary = cursor.fetchone()
        cursor.execute('SELECT last_value,is_called FROM public.events_publicationboundary_id_seq')
        boundary_sequence = cursor.fetchone()
        result['publicationBoundary'] = {'rows': boundary[0], 'value': boundary[1], 'minId': boundary[2], 'maxId': boundary[3], 'idSequence': {'last': boundary_sequence[0], 'called': boundary_sequence[1]}}
        from notification_coverage import aggregate
        result['notificationState'] = aggregate(cursor)
        from storefront_coverage import aggregate as storefront_aggregate
        result['storefrontState'] = storefront_aggregate(cursor)
        require_phase10_catalog(result)
        return result
