import json
import os
import sys
import unittest
sys.path.insert(0, '/ops')
sys.path.insert(0, '/ops/tests')
import psycopg
from snapshot import snapshot
from scanner_linux import ScannerTests


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = psycopg.connect(host=sys.argv[1], user='observation', dbname='observation', autocommit=True)
        cls.db.execute('CREATE TABLE media_mediaasset(id bigint PRIMARY KEY, storage_key uuid, original text, derivative text, source_bytes int, state text)')
        cls.db.execute('CREATE TABLE media_revisionimage(asset_id bigint, revision_id bigint)')
        cls.db.execute('CREATE TABLE moderation_contentreport(revision_id bigint, target_type text, evidence jsonb)')

    def setUp(self):
        self.db.execute('TRUNCATE media_mediaasset, media_revisionimage, moderation_contentreport')

    def add(self):
        self.db.execute("INSERT INTO media_mediaasset VALUES (1,'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','originals/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.bin','','3','pending')")

    def test_empty_is_measured(self):
        self.assertEqual(snapshot(self.db, sys.argv[1]), [])

    def test_producer_layout_real_db_fs(self):
        import tempfile
        from pathlib import Path
        from scanner import scan
        from audit import compare
        with tempfile.TemporaryDirectory(dir='/tmp') as temp:
            root = Path(temp); root.chmod(0o755)
            (root / 'originals').mkdir(mode=0o700)
            (root / 'originals' / ('a' * 32 + '.bin')).write_bytes(b'abc')
            folder = root / 'search-fixtures' / ('b' * 16)
            folder.parent.mkdir(mode=0o700); folder.mkdir(mode=0o700)
            file = folder / 'car.jpg'; file.write_bytes(b'abc'); file.chmod(0o600)
            self.add()
            self.db.execute("UPDATE media_mediaasset SET state='ready', derivative='search-fixtures/bbbbbbbbbbbbbbbb/car.jpg'")
            self.db.execute('INSERT INTO media_revisionimage VALUES(1,10),(1,20)')
            before = self.db.execute('SELECT * FROM media_mediaasset').fetchall()
            for _ in range(2):
                a = snapshot(self.db, sys.argv[1]); s = scan(str(root), environment='developer')
                b = snapshot(self.db, sys.argv[1]); t = scan(str(root), environment='developer')
                r = compare(a, b, s, t, environment='developer')
                self.assertTrue(r['observationComplete']); self.assertEqual(r['missingReadyDerivatives'], 0)
                self.assertEqual(r['multiRevisionAssets'], 1); self.assertEqual(r['reasons']['fixtureDerivativeReferences'], 1)
            self.assertEqual(before, self.db.execute('SELECT * FROM media_mediaasset').fetchall())
            file.unlink()
            s = scan(str(root), environment='developer')
            self.assertEqual(compare(a, b, s, s, environment='developer')['missingReadyDerivatives'], 1)

    def test_absent_children_real_db_fs_repeat_unchanged(self):
        import tempfile
        from scanner import scan
        from audit import compare
        with tempfile.TemporaryDirectory(dir='/tmp') as root:
            os.chmod(root, 0o755)
            self.add()
            self.db.execute("UPDATE media_mediaasset SET state='ready', derivative='derivatives/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg'")
            before = self.db.execute('SELECT * FROM media_mediaasset').fetchall()
            for _ in range(2):
                a = snapshot(self.db, sys.argv[1]); s = scan(root)
                b = snapshot(self.db, sys.argv[1]); t = scan(root)
                r = compare(a, b, s, t)
                self.assertTrue(r['observationComplete'])
                self.assertEqual((r['missingOriginals'], r['missingReadyDerivatives']), (1, 1))
                self.assertEqual(r['directories'], dict(root='present', originals='absent', derivatives='absent'))
                self.assertEqual(os.listdir(root), [])
            self.assertEqual(before, self.db.execute('SELECT * FROM media_mediaasset').fetchall())

    def test_all_revision_links_and_case_membership_without_payload(self):
        self.add()
        self.db.execute('INSERT INTO media_revisionimage VALUES (1,10),(1,20),(1,30)')
        self.db.execute("INSERT INTO moderation_contentreport VALUES (40,'listing','{\"asset_ids\":[1],\"description\":\"SECRET_CANARY\"}')")
        rows = snapshot(self.db, sys.argv[1])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['links'], 3)
        self.assertIs(rows[0]['retained'], True)
        self.assertNotIn('SECRET_CANARY', json.dumps(rows))

    def test_repeated_reads_preserve_rows(self):
        self.add(); before = self.db.execute('SELECT * FROM media_mediaasset').fetchall()
        self.assertEqual(len(snapshot(self.db, sys.argv[1])), 1)
        self.assertEqual(len(snapshot(self.db, sys.argv[1])), 1)
        self.assertEqual(before, self.db.execute('SELECT * FROM media_mediaasset').fetchall())

    def test_wrong_db_identity(self):
        with self.assertRaisesRegex(ValueError, '^identity_mismatch$'):
            snapshot(self.db, '127.0.0.2')

    def test_lock_timeout_not_zero(self):
        with psycopg.connect(host=sys.argv[1], user='observation', dbname='observation') as lock:
            lock.execute('LOCK media_mediaasset IN ACCESS EXCLUSIVE MODE')
            with self.assertRaises(psycopg.errors.LockNotAvailable):
                snapshot(self.db, sys.argv[1])

    def test_capacity_refused(self):
        self.db.execute("INSERT INTO media_mediaasset SELECT n, md5(n::text)::uuid, 'originals/'||md5(n::text)||'.bin','','3','pending' FROM generate_series(1,10001) n")
        with self.assertRaisesRegex(ValueError, '^limit_exceeded$'):
            snapshot(self.db, sys.argv[1])

    def test_missing_table_is_not_empty(self):
        self.db.execute('ALTER TABLE media_mediaasset RENAME TO missing')
        try:
            with self.assertRaises(psycopg.errors.UndefinedTable):
                snapshot(self.db, sys.argv[1])
        finally:
            self.db.execute('ALTER TABLE missing RENAME TO media_mediaasset')

    def proxy(self, replacement=None, on_identity=None):
        real = self.db
        class Cursor:
            def __enter__(self):
                self.cursor = real.cursor(); return self
            def __exit__(self, *args):
                self.cursor.close()
            def execute(self, sql):
                from snapshot import SQL
                self.cursor.execute(replacement if sql == SQL and replacement else sql)
            def fetchone(self):
                row = self.cursor.fetchone()
                if on_identity:
                    on_identity()
                return row
            def fetchmany(self, size):
                return self.cursor.fetchmany(size)
        class Connection:
            def transaction(self): return real.transaction()
            def cursor(self): return Cursor()
        return Connection()

    def test_actual_readonly_transaction_blocks_injected_write(self):
        self.add()
        with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
            snapshot(self.proxy('DELETE FROM media_mediaasset'), sys.argv[1])
        self.assertEqual(self.db.execute('SELECT count(*) FROM media_mediaasset').fetchone()[0], 1)

    def test_statement_timeout_is_real(self):
        with self.assertRaises(psycopg.errors.QueryCanceled):
            snapshot(self.proxy('SELECT pg_sleep(3)'), sys.argv[1])

    def test_snapshot_consistency_and_later_upload_observation(self):
        self.add()
        def commit_upload():
            with psycopg.connect(host=sys.argv[1], user='observation', dbname='observation', autocommit=True) as writer:
                writer.execute("INSERT INTO media_mediaasset VALUES(2,'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb','originals/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.bin','','3','pending')")
        first = snapshot(self.proxy(on_identity=commit_upload), sys.argv[1])
        second = snapshot(self.db, sys.argv[1])
        self.assertEqual((len(first), len(second)), (1, 2))


suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (ScannerTests, DatabaseTests)])
# Test errors stay inside the helper; only fixed counts cross the private pipe.
with open(os.devnull, 'w') as stream:
    result = unittest.TextTestRunner(stream=stream).run(suite)
print(json.dumps(dict(tests=result.testsRun, passed=result.testsRun-len(result.errors)-len(result.failures),
                     failures=len(result.failures), errors=len(result.errors), passAll=result.wasSuccessful())))
sys.exit(0 if result.wasSuccessful() else 1)
