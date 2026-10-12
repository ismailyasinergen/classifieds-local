import contextlib
import io
import sys
import unittest
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe


class Cursor:
    def __init__(self, row, ip="172.30.0.5"):
        self.row, self.ip, self.calls = row, ip, []

    def fetchall(self): return [("pending", 2), ("completed", 1)]

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql): self.calls.append(sql)
    def fetchone(self): return (self.ip,) if len(self.calls) == 5 else self.row


class Connection:
    def __init__(self, row, ip="172.30.0.5"): self.cur = Cursor(row, ip)
    def transaction(self): return contextlib.nullcontext()
    def cursor(self): return self.cur


class ProbeTests(unittest.TestCase):
    def test_outbox_backlog_distinct_consumer_progress(self):
        self.assertEqual(probe.aggregate(Connection((3, 120)), "outbox", "172.30.0.5"),
                         {"sourceUnprocessed": 3, "oldestAgeSeconds": 120.0, "consumer": "saved_search_in_app_v1", "consumption": {"pending": 2, "retry": 0, "completed": 1, "skipped": 0, "failed": 0}})

    def test_empty_is_not_query_failure(self):
        self.assertEqual(probe.aggregate(Connection((0, None)), "outbox", "172.30.0.5")["sourceUnprocessed"], 0)
        connection = Connection((0, None))
        connection.cur.execute = lambda sql: (_ for _ in ()).throw(PermissionError("SECRET"))
        with self.assertRaises(PermissionError): probe.aggregate(connection, "outbox", "172.30.0.5")

    def test_wrong_db_before_aggregate(self):
        connection = Connection((0, None), "172.30.0.99")
        with self.assertRaisesRegex(ValueError, "^identity_mismatch$"):
            probe.aggregate(connection, "outbox", "172.30.0.5")
        self.assertNotIn(probe.OUTBOX, connection.cur.calls)

    def test_media_states_attempt_limit(self):
        self.assertEqual(probe.aggregate(Connection((2, 3, 4, 1, 200)), "media", "172.30.0.5"),
                         {"pending": 2, "ready": 3, "failed": 4, "attemptLimitReached": 1, "oldestPendingAgeSeconds": 200.0})

    def test_readonly_bounded_sql_only(self):
        connection = Connection((0, None))
        probe.aggregate(connection, "outbox", "172.30.0.5")
        self.assertEqual(connection.cur.calls[:4], ["SET TRANSACTION READ ONLY", "SET LOCAL statement_timeout = '2000ms'",
                          "SET LOCAL lock_timeout = '500ms'", "SET LOCAL idle_in_transaction_session_timeout = '3000ms'"])
        self.assertTrue(all(s.startswith(("SET TRANSACTION READ ONLY", "SET LOCAL", "SELECT")) for s in connection.cur.calls))
        self.assertEqual(connection.cur.calls[4], "SELECT host(inet_server_addr())")
        self.assertNotIn("payload", probe.OUTBOX)
        self.assertNotIn("original", probe.MEDIA)

    def test_arbitrary_sql_and_task_refused(self):
        for mode in ("DELETE FROM events_outboxevent", "media.tasks.process_image"):
            with self.assertRaisesRegex(ValueError, "^input_refused$"):
                probe.aggregate(Connection((0, None)), mode, "172.30.0.5")
            with self.assertRaisesRegex(ValueError, "^input_refused$"):
                probe.run([mode, "172.30.0.5", "172.30.0.6", "celery@aaaaaaaaaaaa"])

    def test_worker_pong(self):
        self.assertEqual(probe.check_ping([{"celery@aaaaaaaaaaaa": {"ok": "pong"}}], "celery@aaaaaaaaaaaa"), {"responding": True})

    def test_worker_absent(self):
        with self.assertRaisesRegex(ValueError, "^worker_unresponsive$"):
            probe.check_ping([], "celery@aaaaaaaaaaaa")

    def test_foreign_worker_and_payload(self):
        for replies in ([{"foreign": {"ok": "pong"}}], [{"celery@aaaaaaaaaaaa": {"ok": "pong", "payload": "SECRET"}}]):
            with self.assertRaisesRegex(ValueError, "^foreign_worker$"):
                probe.check_ping(replies, "celery@aaaaaaaaaaaa")

    def test_real_worker_branch_only_targeted_control_ping(self):
        calls = []
        class App:
            conf = types.SimpleNamespace(update=lambda **kwargs: None)
            control = types.SimpleNamespace(ping=lambda **kwargs: calls.append(kwargs) or [{"celery@aaaaaaaaaaaa": {"ok": "pong"}}])
            def close(self): calls.append("closed")
        def create(name, broker):
            self.assertEqual(broker, "redis://172.30.0.6:6379/0")
            return App()
        with patch.dict(sys.modules, {"celery": types.SimpleNamespace(Celery=create)}):
            self.assertEqual(probe.run(["worker", "172.30.0.5", "172.30.0.6", "celery@aaaaaaaaaaaa"]), {"responding": True})
        self.assertEqual(calls, [{"destination": ["celery@aaaaaaaaaaaa"], "timeout": 2}, "closed"])

    def test_main_sanitizes_permission_and_timeout(self):
        for error, category in ((PermissionError("SECRET"), "access_denied"), (TimeoutError("SECRET"), "timeout"), (RuntimeError("SECRET"), "query_failed")):
            output = io.StringIO()
            with patch.object(probe, "run", side_effect=error), patch.object(probe.signal, "signal", create=True), patch.object(probe.signal, "alarm", create=True), patch.object(probe.signal, "SIGALRM", 14, create=True), contextlib.redirect_stdout(output):
                probe.main()
            self.assertNotIn("SECRET", output.getvalue())
            self.assertIn(category, output.getvalue())


if __name__ == "__main__": unittest.main()
