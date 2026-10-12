"""Synthetic-only tests, executed in a fresh network without live data mounts."""
import json
import sys
import time
import psycopg

sys.path.insert(0, "/ops")
from probe import aggregate

checks = 0
diagnostic = {}


def verify(condition):
    global checks
    assert condition
    checks += 1


def connect(readonly=False):
    return psycopg.connect(host="db", port=5432, user="observation", dbname="observation", connect_timeout=2,
                           autocommit=True, options="-c default_transaction_read_only=on -c statement_timeout=2000 -c lock_timeout=500" if readonly else "")


def main():
    ip = sys.argv[1]
    with connect() as setup:
        diagnostic["hostAddressMatches"] = setup.execute("SELECT host(inet_server_addr()) = %s", (ip,)).fetchone()[0]
        diagnostic["textAddressMatches"] = setup.execute("SELECT inet_server_addr()::text = %s", (ip,)).fetchone()[0]
        setup.execute("CREATE TABLE events_outboxevent (id integer, created_at timestamptz, processed_at timestamptz, payload jsonb)")
        setup.execute("CREATE TABLE events_eventconsumption (id integer, consumer text, status text)")
        setup.execute("CREATE TABLE media_mediaasset (id integer, created_at timestamptz, state text, attempts integer, original text)")
        with connect(True) as reader:
            verify(aggregate(reader, "outbox", ip) == {"sourceUnprocessed": 0, "oldestAgeSeconds": None, "consumer": "saved_search_in_app_v1", "consumption": {k: 0 for k in ("pending", "retry", "completed", "skipped", "failed")}})
            verify(aggregate(reader, "media", ip) == {"pending": 0, "ready": 0, "failed": 0, "attemptLimitReached": 0, "oldestPendingAgeSeconds": None})
            setup.execute("INSERT INTO events_outboxevent VALUES (1,now()-interval '10 minutes',NULL,'{\"private\":\"canary\"}'),(2,now(),NULL,'{}'),(3,now(),now(),'{}')")
            setup.execute("INSERT INTO media_mediaasset VALUES (1,now()-interval '5 minutes','pending',0,'private-canary'),(2,now(),'pending',3,'private-canary'),(3,now(),'ready',1,'private-canary'),(4,now(),'failed',3,'private-canary')")
            setup.execute("INSERT INTO events_eventconsumption VALUES (1,'saved_search_in_app_v1','completed'),(2,'foreign','failed')")
            outbox = aggregate(reader, "outbox", ip)
            verify(outbox["sourceUnprocessed"] == 2 and outbox["oldestAgeSeconds"] >= 600 and outbox["consumer"] == "saved_search_in_app_v1" and outbox["consumption"] == {"pending": 0, "retry": 0, "completed": 1, "skipped": 0, "failed": 0})
            media = aggregate(reader, "media", ip)
            verify([media[k] for k in ("pending", "ready", "failed", "attemptLimitReached")] == [2, 1, 1, 2] and media["oldestPendingAgeSeconds"] >= 300)
            try:
                aggregate(reader, "outbox", "192.0.2.1")
                raise AssertionError()
            except ValueError as error:
                verify(str(error) == "identity_mismatch")
            before = setup.execute("SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) FROM events_outboxevent t").fetchone()
            media_before = setup.execute("SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) FROM media_mediaasset t").fetchone()
            for _ in range(2):
                aggregate(reader, "outbox", ip)
                aggregate(reader, "media", ip)
            verify(before == setup.execute("SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) FROM events_outboxevent t").fetchone())
            verify(media_before == setup.execute("SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) FROM media_mediaasset t").fetchone())
            try:
                reader.execute("DELETE FROM events_outboxevent")
                raise AssertionError()
            except psycopg.errors.ReadOnlySqlTransaction:
                verify(True)
            start = time.monotonic()
            try:
                reader.execute("SELECT pg_sleep(3)")
                raise AssertionError()
            except psycopg.errors.QueryCanceled:
                verify(time.monotonic() - start < 2.8)
            with setup.transaction():
                setup.execute("LOCK TABLE events_outboxevent IN ACCESS EXCLUSIVE MODE")
                try:
                    aggregate(reader, "outbox", ip)
                    raise AssertionError()
                except psycopg.errors.LockNotAvailable:
                    verify(True)
            setup.execute("ALTER TABLE events_outboxevent RENAME TO absent_test")
            try:
                aggregate(reader, "outbox", ip)
                raise AssertionError()
            except psycopg.errors.UndefinedTable:
                verify(True)
            setup.execute("ALTER TABLE absent_test RENAME TO events_outboxevent")
            verify(aggregate(reader, "outbox", ip)["sourceUnprocessed"] == 2)
    print(json.dumps({"pass": True, "checks": checks, "privateValuesEmitted": False, "repeatedReadsUnchanged": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"pass": False, "checks": checks, "error": "synthetic_db_test_failed",
                          "errorType": type(error).__name__, "diagnostic": diagnostic,
                          "category": str(error) if isinstance(error, ValueError) and str(error) in ("identity_mismatch", "input_refused") else "test_failure",
                          "sqlstate": getattr(error, "sqlstate", None)}))
        sys.exit(1)
