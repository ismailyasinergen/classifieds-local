"""Executed from reviewed public source in memory; stdout is a private pipe."""
import hashlib
import json
import os
import re
import signal
import socket
import sys
from snapshot_catalog import export_catalog


def main():
    mode, expected_ip, binding = sys.argv[1:4]
    if mode not in ('snapshot', 'keys', 'key-identity'):
        raise ValueError('mode_refused')
    signal.signal(signal.SIGALRM, lambda *_: os._exit(70))
    signal.alarm(300)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings
    db = settings.DATABASES['default']
    actual = hashlib.sha256((str(db['NAME']) + '\n' + str(db['USER'])).encode()).hexdigest()
    if actual != binding or db['HOST'] != 'db' or str(db['PORT']) != '5432':
        raise ValueError('database_binding_refused')
    if socket.gethostbyname(db['HOST']) != expected_ip:
        raise ValueError('database_network_refused')
    if str(settings.PRIVATE_MEDIA_ROOT) != '/var/lib/classifieds/media':
        raise ValueError('media_root_refused')
    import django
    django.setup()
    keys = json.dumps({'secretKey': settings.SECRET_KEY, 'fallbacks': list(settings.SECRET_KEY_FALLBACKS)}, sort_keys=True).encode()
    if mode == 'keys':
        sys.stdout.buffer.write(keys)
        return
    if mode == 'key-identity':
        sys.stdout.write(hashlib.sha256(keys).hexdigest())
        return
    run, attempt = sys.argv[4:]
    if not re.fullmatch(r'[a-f0-9]{16}', run) or not re.fullmatch(r'[a-f0-9]{32}', attempt):
        raise ValueError('snapshot_binding_refused')
    from django.db import connection
    try:
        connection.ensure_connection()
        conn = connection.connection
        with conn.transaction():
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            conn.execute("SET LOCAL statement_timeout='300s'")
            conn.execute("SET LOCAL lock_timeout='5s'")
            conn.execute("SET LOCAL idle_in_transaction_session_timeout='300s'")
            if str(conn.execute('SELECT inet_server_addr()').fetchone()[0]) != expected_ip:
                raise ValueError('database_server_refused')
            size = conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]
            if size > 1024 * 1024 * 1024:
                raise ValueError('database_capacity')
            snapshot = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
            catalog = export_catalog(conn)
            catalog.update(snapshot=snapshot, databaseBytes=size, keySha256=hashlib.sha256(keys).hexdigest(),
                           snapshotAt=conn.execute('SELECT transaction_timestamp()').fetchone()[0].isoformat())
            encoded = json.dumps({'type': 'catalog', 'run': run, 'attempt': attempt, 'catalog': catalog}, separators=(',', ':')).encode()
            if len(encoded) > 32 * 1024 * 1024:
                raise ValueError('catalog_capacity')
            sys.stdout.buffer.write(encoded + b'\n')
            sys.stdout.buffer.flush()
            if sys.stdin.buffer.readline(80) != ('close:' + attempt + '\n').encode():
                raise ValueError('snapshot_disconnected')
    finally:
        connection.close()
        if mode == 'snapshot':
            sys.stdout.write(json.dumps({'type': 'snapshot_closed', 'run': run, 'attempt': attempt, 'transactionClosed': True, 'connectionClosed': True}) + '\n')
            sys.stdout.flush()


try:
    main()
except Exception:
    sys.stderr.write('original_export_failed\n')
    sys.exit(1)
