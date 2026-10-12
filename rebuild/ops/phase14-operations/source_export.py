"""Private stdout protocol; never invoke from a diagnostic terminal."""
import hashlib
import json
import os
import re
import signal
import sys

from snapshot_catalog import export_catalog
from media_stream import inventory, stream_media


def setup():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.conf import settings
    return settings


def key_bytes(settings):
    return json.dumps({'secretKey': settings.SECRET_KEY, 'fallbacks': list(settings.SECRET_KEY_FALLBACKS)}, sort_keys=True).encode()


def main():
    settings = setup()
    mode = sys.argv[1]
    if mode == 'keys':
        sys.stdout.buffer.write(key_bytes(settings))
        return
    if mode == 'key-identity':
        sys.stdout.write(hashlib.sha256(key_bytes(settings)).hexdigest())
        return
    if mode == 'media':
        data = sys.stdin.buffer.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('catalog_capacity')
        stream_media(settings.PRIVATE_MEDIA_ROOT, json.loads(data), sys.stdout.buffer)
        return
    if mode not in ('snapshot', 'snapshot-check'):
        raise ValueError('source_mode_refused')
    run, attempt = sys.argv[2:] if mode == 'snapshot' else ('', '')
    if mode == 'snapshot' and (not re.fullmatch(r'[a-f0-9]{16}', run) or not re.fullmatch(r'[a-f0-9]{32}', attempt)):
        raise ValueError('snapshot_binding_refused')
    # A disconnected orchestrator cannot leave a live snapshot transaction indefinitely.
    signal.signal(signal.SIGALRM, lambda *_: os._exit(70))
    signal.alarm(300)
    from django.db import connection
    connection.ensure_connection()
    conn = connection.connection
    try:
        with conn.transaction():
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            conn.execute("SET LOCAL statement_timeout='300s'")
            conn.execute("SET LOCAL lock_timeout='5s'")
            conn.execute("SET LOCAL idle_in_transaction_session_timeout='300s'")
            db_size = conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]
            if db_size > 1024 * 1024 * 1024:
                raise ValueError('database_capacity')
            snapshot = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
            catalog = export_catalog(conn)
            catalog['media'] = inventory(settings.PRIVATE_MEDIA_ROOT, catalog.pop('assets'))
            catalog['keySha256'] = hashlib.sha256(key_bytes(settings)).hexdigest()
            catalog['snapshot'] = snapshot
            catalog['databaseBytes'] = db_size
            catalog['snapshotAt'] = conn.execute('SELECT transaction_timestamp()').fetchone()[0].isoformat()
            if mode == 'snapshot-check':
                print(json.dumps({'pass': True, 'tables': len(catalog['tables']), 'media': len(catalog['media'])}))
                return
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
        signal.alarm(0)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.stderr.write('source_export_failed:' + type(error).__name__ + '\n')
        sys.exit(1)
