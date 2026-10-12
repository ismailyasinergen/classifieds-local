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


def export_catalog(connection):
    from psycopg import sql
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
        tables = [r[0] for r in cursor.fetchall()]
        result = {'format': 1, 'tables': {}, 'sequences': []}
        for table in tables:
            cursor.execute("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,))
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
            result['tables'][table] = {'count': count, 'sha256': digest.hexdigest(), 'schema': hashlib.sha256(canonical(columns)).hexdigest()}
            for col, _, _, _ in columns:
                cursor.execute('SELECT pg_get_serial_sequence(%s,%s)', ('public.' + table, col))
                seq = cursor.fetchone()[0]
                if seq:
                    cursor.execute(sql.SQL('SELECT max({}) FROM {}.{}').format(sql.Identifier(col), sql.Identifier('public'), sql.Identifier(table)))
                    result['sequences'].append({'table': table, 'column': col, 'sequence': seq, 'max': cursor.fetchone()[0]})
        cursor.execute('SELECT app,name FROM django_migrations ORDER BY app,name')
        result['migrations'] = [list(r) for r in cursor.fetchall()]
        cursor.execute('SELECT original,derivative,state,source_bytes,storage_key FROM media_mediaasset ORDER BY id')
        result['assets'] = [{'original': r[0], 'derivative': r[1], 'state': r[2], 'source_bytes': r[3], 'key': r[4].hex} for r in cursor.fetchall()]
        return result
