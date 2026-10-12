import hashlib
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from media_stream import inventory, stream_media
from archive_io import stream_safe_source


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'originals').mkdir()
        (self.root / 'derivatives').mkdir()
        self.key = 'a' * 32
        self.original = 'originals/' + self.key + '.bin'
        self.derivative = 'derivatives/' + self.key + '.jpg'
        (self.root / self.original).write_bytes(b'\x00\xffbinary')
        self.asset = {'original': self.original, 'derivative': '', 'state': 'pending', 'source_bytes': 8, 'key': self.key}

    def test_pending_includes_original_and_excludes_orphans(self):
        (self.root / self.derivative).write_bytes(b'orphan')
        entries = inventory(self.root, [self.asset])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['sha256'], hashlib.sha256(b'\x00\xffbinary').hexdigest())
        output = io.BytesIO()
        stream_media(self.root, entries, output)
        with tarfile.open(fileobj=io.BytesIO(output.getvalue())) as archive:
            self.assertEqual(archive.getnames(), [self.original])
            self.assertEqual(archive.extractfile(self.original).read(), b'\x00\xffbinary')

    def test_ready_missing_derivative_refused(self):
        with self.assertRaises(ValueError):
            inventory(self.root, [{**self.asset, 'state': 'ready', 'derivative': self.derivative}])

    def test_size_mismatch_refused(self):
        with self.assertRaises(ValueError):
            inventory(self.root, [{**self.asset, 'source_bytes': 1}])

    def test_traversal_and_duplicates_refused(self):
        with self.assertRaises(ValueError):
            inventory(self.root, [{**self.asset, 'original': '../escape'}])
        with self.assertRaises(ValueError):
            inventory(self.root, [self.asset, self.asset])

    def test_symlink_and_hardlink_refused(self):
        os.link(self.root / self.original, self.root / 'copy')
        with self.assertRaises(ValueError):
            inventory(self.root, [self.asset])
        (self.root / 'copy').unlink()
        (self.root / self.original).rename(self.root / 'real')
        os.symlink(self.root / 'real', self.root / self.original)
        with self.assertRaises(ValueError):
            inventory(self.root, [self.asset])

    def test_mutation_after_catalog_refused(self):
        entries = inventory(self.root, [self.asset])
        (self.root / self.original).write_bytes(b'changed!')
        with self.assertRaises(ValueError):
            stream_media(self.root, entries, io.BytesIO())

    def test_mutation_during_read_refused(self):
        import media_stream
        from unittest.mock import patch
        entries = inventory(self.root, [self.asset])
        actual = media_stream.identity
        calls = 0

        def concurrent_writer(stream):
            nonlocal calls
            calls += 1
            if calls == 2:
                # A size change is observable even when two writes share the filesystem clock tick.
                (self.root / self.original).write_bytes(b'changed-and-longer')
            return actual(stream)

        with patch.object(media_stream, 'identity', concurrent_writer):
            with self.assertRaises(ValueError):
                stream_media(self.root, entries, io.BytesIO())
        self.assertEqual(calls, 2)

    def test_source_archive_hash_and_private_path_boundary(self):
        (self.root / 'rebuild').mkdir()
        (self.root / 'rebuild/public.txt').write_bytes(b'public')
        good = [{'path': 'rebuild/public.txt', 'sha256': hashlib.sha256(b'public').hexdigest()}]
        output = io.BytesIO()
        stream_safe_source(good, self.root, output)
        with tarfile.open(fileobj=io.BytesIO(output.getvalue())) as archive:
            self.assertEqual(archive.extractfile('rebuild/public.txt').read(), b'public')
        for entries in [[{**good[0], 'sha256': '0' * 64}], good * 2,
                        [{'path': 'rebuild/.env', 'sha256': '0' * 64}], [{'path': 'rebuild/../escape', 'sha256': '0' * 64}]]:
            with self.assertRaises(ValueError):
                stream_safe_source(entries, self.root, io.BytesIO())
