"""Two bounded reference observations; no private payload leaves PostgreSQL."""
import ipaddress
import json
import os
import signal
import sys

SQL = """SELECT a.id, a.storage_key::text, a.original, a.derivative, a.source_bytes, a.state,
 (SELECT count(*) FROM media_revisionimage i WHERE i.asset_id=a.id),
 EXISTS (SELECT 1 FROM moderation_contentreport r WHERE r.target_type='listing' AND
   (r.evidence @> jsonb_build_object('asset_ids', jsonb_build_array(a.id)) OR
    EXISTS (SELECT 1 FROM media_revisionimage i WHERE i.asset_id=a.id AND i.revision_id=r.revision_id)))
 FROM media_mediaasset a ORDER BY a.id LIMIT 10001"""


def snapshot(connection, expected_ip):
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            cursor.execute("SET LOCAL statement_timeout='2000ms'")
            cursor.execute("SET LOCAL lock_timeout='500ms'")
            cursor.execute("SET LOCAL idle_in_transaction_session_timeout='3000ms'")
            cursor.execute('SELECT host(inet_server_addr())')
            if cursor.fetchone()[0] != expected_ip:
                raise ValueError('identity_mismatch')
            cursor.execute(SQL)
            rows = cursor.fetchmany(10001)
    if len(rows) > 10000:
        raise ValueError('limit_exceeded')
    return [dict(id=r[0], key=r[1].replace('-', ''), original=r[2], derivative=r[3],
                 source_bytes=r[4], state=r[5], links=r[6], retained=r[7]) for r in rows]


def main():
    def deadline(*_):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, deadline); signal.alarm(8)
    try:
        if len(sys.argv) != 2:
            raise ValueError('input_refused')
        address = str(ipaddress.IPv4Address(sys.argv[1]))
        import psycopg
        with psycopg.connect(host='db', hostaddr=address, port=5432, user=os.environ['POSTGRES_USER'],
            dbname=os.environ['POSTGRES_DB'], password=os.environ['POSTGRES_PASSWORD'], autocommit=True,
            connect_timeout=2, options='-c default_transaction_read_only=on -c statement_timeout=2000 -c lock_timeout=500 -c idle_in_transaction_session_timeout=3000') as connection:
            result = dict(ok=True, assets=snapshot(connection, address))
    except Exception as error:
        category = ('timeout' if isinstance(error, TimeoutError) or getattr(error, 'sqlstate', None) in ('57014', '55P03') else
                    'access_denied' if isinstance(error, PermissionError) or getattr(error, 'sqlstate', None) in ('42501', '28000', '28P01') else
                    str(error) if isinstance(error, ValueError) and str(error) in ('limit_exceeded', 'identity_mismatch', 'input_refused') else 'query_failed')
        result = dict(ok=False, error=category)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
