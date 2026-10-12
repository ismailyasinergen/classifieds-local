"""Fixed bounded diagnostics. No arbitrary SQL, task or destination input from CLI users."""
import ipaddress
import json
import os
import signal
import sys

OUTBOX = """SELECT count(*), EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - min(created_at)))
FROM events_outboxevent WHERE processed_at IS NULL"""
MEDIA = """SELECT count(*) FILTER (WHERE state='pending'), count(*) FILTER (WHERE state='ready'),
count(*) FILTER (WHERE state='failed'), count(*) FILTER (WHERE attempts>=3),
EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - min(created_at) FILTER (WHERE state='pending')))
FROM media_mediaasset"""


def aggregate(connection, mode, expected_ip):
    if mode not in ("outbox", "media"):
        raise ValueError("input_refused")
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '2000ms'")
            cursor.execute("SET LOCAL lock_timeout = '500ms'")
            cursor.execute("SET LOCAL idle_in_transaction_session_timeout = '3000ms'")
            cursor.execute("SELECT host(inet_server_addr())")
            if cursor.fetchone()[0] != expected_ip:
                raise ValueError("identity_mismatch")
            cursor.execute(OUTBOX if mode == "outbox" else MEDIA)
            row = cursor.fetchone()
            if mode == "outbox":
                cursor.execute("SELECT status,count(*) FROM events_eventconsumption WHERE consumer='saved_search_in_app_v1' GROUP BY status")
                states = cursor.fetchall()
    if mode == "outbox":
        counts = {status: 0 for status in ['pending', 'retry', 'completed', 'skipped', 'failed']}
        for status, total in states:
            if status not in counts or type(total) is not int or total < 0:
                raise ValueError('invalid_response')
            counts[status] = total
        return {"sourceUnprocessed": row[0], "oldestAgeSeconds": None if row[1] is None else max(0, float(row[1])), "consumer": "saved_search_in_app_v1", "consumption": counts}
    return dict(zip(("pending", "ready", "failed", "attemptLimitReached", "oldestPendingAgeSeconds"),
                    (*row[:4], None if row[4] is None else max(0, float(row[4])))))


def check_ping(replies, destination):
    if not replies:
        raise ValueError("worker_unresponsive")
    if replies != [{destination: {"ok": "pong"}}]:
        raise ValueError("foreign_worker")
    return {"responding": True}


def run(args):
    if len(args) != 4 or args[0] not in ("outbox", "media", "worker"):
        raise ValueError("input_refused")
    mode, db_ip, redis_ip, destination = args
    ipaddress.IPv4Address(db_ip)
    ipaddress.IPv4Address(redis_ip)
    import re
    if not re.fullmatch(r"celery@[a-f0-9]{12}", destination):
        raise ValueError("input_refused")
    if mode == "worker":
        from celery import Celery
        app = Celery("bounded_observation", broker=f"redis://{redis_ip}:6379/0")
        app.conf.update(broker_connection_timeout=2, broker_connection_retry=False,
                        broker_transport_options={"socket_timeout": 2, "socket_connect_timeout": 2, "max_retries": 0})
        try:
            return check_ping(app.control.ping(destination=[destination], timeout=2), destination)
        finally:
            app.close()
    import psycopg
    with psycopg.connect(host="db", hostaddr=db_ip, port=5432, dbname=os.environ["POSTGRES_DB"],
                          user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
                          connect_timeout=2, autocommit=True,
                          options="-c default_transaction_read_only=on -c statement_timeout=2000 -c lock_timeout=500 -c idle_in_transaction_session_timeout=3000") as connection:
        return aggregate(connection, mode, db_ip)


def main():
    def deadline(signum, frame):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(8)
    try:
        result = {"ok": True, "data": run(sys.argv[1:])}
    except Exception as error:
        state = getattr(error, "sqlstate", None)
        category = ("timeout" if isinstance(error, TimeoutError) or state in ("57014", "55P03") else
                    "access_denied" if isinstance(error, PermissionError) or state in ("42501", "28000", "28P01") else
                    str(error) if isinstance(error, ValueError) and str(error) in ("input_refused", "identity_mismatch", "worker_unresponsive", "foreign_worker") else "query_failed")
        result = {"ok": False, "error": category}
    finally:
        signal.alarm(0)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
