import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


class SnapshotProtocol(unittest.TestCase):
    def exercise(self, original, catalog_error=False, wrong_close=False):
        run, attempt = 'a' * 16, 'b' * 32
        state = {'closed': False, 'transaction_ended': False, 'ack_before_close': False}
        settings = types.SimpleNamespace(SECRET_KEY='PRIVATE_CANARY', SECRET_KEY_FALLBACKS=[], PRIVATE_MEDIA_ROOT='/var/lib/classifieds/media', DATABASES={'default': {'NAME': 'synthetic', 'USER': 'synthetic', 'HOST': 'db', 'PORT': '5432'}})

        class Connection:
            connection = None
            def ensure_connection(self):
                self.connection = self
            @contextlib.contextmanager
            def transaction(self):
                try:
                    yield
                finally:
                    state['transaction_ended'] = True
            def execute(self, sql):
                value = 1
                if 'pg_export_snapshot' in sql:
                    value = '00000001-00000001-1'
                elif 'transaction_timestamp' in sql:
                    value = datetime(2026, 1, 1, tzinfo=timezone.utc)
                elif 'inet_server_addr' in sql:
                    value = '192.0.2.1'
                return types.SimpleNamespace(fetchone=lambda: (value,))
            def close(self):
                state['closed'] = True

        class Output(io.TextIOWrapper):
            def write(self, text):
                if 'snapshot_closed' in text and not (state['closed'] and state['transaction_ended']):
                    state['ack_before_close'] = True
                return super().write(text)

        def catalog(_):
            if catalog_error:
                raise ValueError('PRIVATE_CANARY')
            return {'tables': [], 'assets': []}

        modules = {'django': types.SimpleNamespace(setup=lambda: None), 'django.conf': types.SimpleNamespace(settings=settings), 'django.db': types.SimpleNamespace(connection=Connection()), 'snapshot_catalog': types.SimpleNamespace(export_catalog=catalog), 'media_stream': types.SimpleNamespace(inventory=lambda *_: [], stream_media=lambda *_: None)}
        out = Output(io.BytesIO(), encoding='utf8', write_through=True)
        err = io.StringIO()
        incoming = io.TextIOWrapper(io.BytesIO((('bad' if wrong_close else 'close:' + attempt) + '\n').encode()))
        name = 'original_export.py' if original else 'source_export.py'
        binding = hashlib.sha256(b'synthetic\nsynthetic').hexdigest()
        args = [name, 'snapshot', '192.0.2.1', binding, run, attempt] if original else [name, 'snapshot', run, attempt]
        exit_code = 0
        with patch.dict(sys.modules, modules), patch.object(sys, 'argv', args), patch.object(sys, 'stdin', incoming), patch.object(sys, 'stdout', out), patch.object(sys, 'stderr', err), patch('signal.signal'), patch('signal.alarm', create=True), patch('signal.SIGALRM', 14, create=True), patch('socket.gethostbyname', return_value='192.0.2.1'):
            try:
                runpy.run_path(str(Path(__file__).resolve().parent.parent / name), run_name='__main__')
            except SystemExit as error:
                exit_code = error.code
        out.flush()
        text = out.buffer.getvalue().decode()
        self.assertNotIn('PRIVATE_CANARY', text + err.getvalue())
        frames = [json.loads(line) for line in text.splitlines()]
        self.assertEqual(frames[-1], {'type': 'snapshot_closed', 'run': run, 'attempt': attempt, 'transactionClosed': True, 'connectionClosed': True})
        self.assertFalse(state['ack_before_close'])
        self.assertEqual(exit_code, 1 if catalog_error or wrong_close else 0)
        if not catalog_error:
            self.assertEqual(frames[0]['type'], 'catalog')
        else:
            self.assertEqual(len(frames), 1)

    def test_synthetic_normal_ack_after_close(self): self.exercise(False)
    def test_original_normal_ack_after_close(self): self.exercise(True)
    def test_synthetic_catalog_failure_ack_after_rollback(self): self.exercise(False, catalog_error=True)
    def test_original_catalog_failure_ack_after_rollback(self): self.exercise(True, catalog_error=True)
    def test_synthetic_bad_control_ack_still_means_closed_not_success(self): self.exercise(False, wrong_close=True)
    def test_original_bad_control_ack_still_means_closed_not_success(self): self.exercise(True, wrong_close=True)


if __name__ == '__main__':
    unittest.main()
