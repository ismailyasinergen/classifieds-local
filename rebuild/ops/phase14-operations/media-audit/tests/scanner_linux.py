import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, '/ops')
from scanner import scan


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/tmp')
        self.root = Path(self.temp.name)
        self.root.chmod(0o755)
        for part in ('originals', 'derivatives'):
            (self.root / part).mkdir(mode=0o700)
        self.file = self.root / 'originals' / ('a' * 32 + '.bin')
        self.file.write_bytes(b'PRIVATE_FILE_CANARY')

    def tearDown(self):
        self.temp.cleanup()

    def test_real_metadata_no_regular_file_open_and_no_mutation(self):
        before = hashlib.sha256(self.file.read_bytes()).hexdigest()
        original = os.open
        def only_directory(p, flags, *args, **kwargs):
            if not flags & os.O_DIRECTORY:
                raise AssertionError('regular_open_forbidden')
            return original(p, flags, *args, **kwargs)
        with patch('os.open', side_effect=only_directory):
            first = scan(str(self.root)); second = scan(str(self.root))
        self.assertEqual(len(first['files']), 1)
        self.assertEqual(first, second)
        self.assertEqual(before, hashlib.sha256(self.file.read_bytes()).hexdigest())

    def test_symlink_hardlink_fifo_nested_directory_not_followed(self):
        os.symlink('/etc', self.root / 'originals' / 'outside')
        os.link(self.file, self.root / 'originals' / 'hardlink')
        os.mkfifo(self.root / 'derivatives' / 'fifo')
        (self.root / 'derivatives' / 'nested').mkdir()
        r = scan(str(self.root))
        self.assertEqual(len(r['unsafe']), 5)
        self.assertEqual(len(r['files']), 0)

    def test_root_symlink_refused(self):
        os.symlink(self.root, self.root / 'link')
        with self.assertRaises(ValueError):
            scan(str(self.root / 'link'))

    def test_producer_layout_currently_excluded(self):
        folder = self.root / 'search-fixtures' / ('b' * 16)
        folder.parent.mkdir(mode=0o700); folder.mkdir(mode=0o700)
        (folder / 'car.jpg').write_bytes(b'SYNTHETIC_ONLY')
        (folder / 'car.jpg').chmod(0o600)
        r = scan(str(self.root), environment='developer')
        self.assertIn('search-fixtures/' + 'b' * 16 + '/car.jpg', r['files'])

    def fixture_file(self):
        folder = self.root / 'search-fixtures' / ('b' * 16)
        folder.parent.mkdir(mode=0o700); folder.mkdir(mode=0o700)
        file = folder / 'car.jpg'; file.write_bytes(b'SYNTHETIC_ONLY'); file.chmod(0o600)
        return file

    def test_fixture_original_disabled_and_repeated_developer_readonly(self):
        file = self.fixture_file(); before = hashlib.sha256(file.read_bytes()).hexdigest()
        original = scan(str(self.root))
        self.assertIn('search-fixtures', original['unsafe'])
        self.assertNotIn(str(file.relative_to(self.root)), original['files'])
        a = scan(str(self.root), environment='developer'); b = scan(str(self.root), environment='developer')
        self.assertEqual(a, b); self.assertEqual(before, hashlib.sha256(file.read_bytes()).hexdigest())

    def test_fixture_unknown_paths_not_recursive(self):
        file = self.fixture_file()
        (file.parent / 'nested').mkdir(); (file.parent / 'other.jpg').write_bytes(b'CANARY')
        (file.parent.parent / 'invalid-run').mkdir()
        r = scan(str(self.root), environment='developer')
        self.assertEqual(list(r['issues'].values()).count('unknown_entry'), 3)
        self.assertEqual(len(r['files']), 2)

    def test_fixture_symlink_hardlink_refused(self):
        file = self.fixture_file(); file.unlink(); os.symlink('/etc/passwd', file)
        r = scan(str(self.root), environment='developer')
        self.assertEqual(list(r['issues'].values()).count('unsafe_object'), 1)
        file.unlink(); os.link(self.file, file)
        r = scan(str(self.root), environment='developer')
        self.assertNotIn(str(file.relative_to(self.root)), r['files'])

    def test_fixture_directory_symlink_refused(self):
        file = self.fixture_file(); file.unlink(); file.parent.rmdir()
        os.symlink('/etc', file.parent)
        r = scan(str(self.root), environment='developer')
        self.assertEqual(r['fixtureDirectories'][str(file.parent.relative_to(self.root))]['state'], 'unsafe')

    def test_fixture_io_and_permission_distinguished(self):
        import errno
        file = self.fixture_file(); real = os.stat
        for error, reason in ((PermissionError(errno.EACCES, 'CANARY'), 'access_denied'), (OSError(errno.EIO, 'CANARY'), 'io_error')):
            def fail(p, *args, **kwargs):
                if p == 'car.jpg':
                    raise error
                return real(p, *args, **kwargs)
            with patch('os.stat', side_effect=fail):
                r = scan(str(self.root), environment='developer')
            self.assertEqual(r['issues'][str(file.relative_to(self.root))], reason)

    def test_fixture_file_swap_not_followed(self):
        file = self.fixture_file(); real = os.stat; fired = False
        def swap(p, *args, **kwargs):
            nonlocal fired
            info = real(p, *args, **kwargs)
            if not fired and p == 'car.jpg':
                fired = True; file.unlink(); os.symlink('/etc/passwd', file)
            return info
        with patch('os.stat', side_effect=swap):
            r = scan(str(self.root), environment='developer')
        self.assertEqual(r['issues'][str(file.relative_to(self.root))], 'unstable')

    def test_fixture_directory_replacement_race(self):
        file = self.fixture_file(); real = os.scandir; fired = False
        def swap(fd):
            nonlocal fired
            entries = real(fd)
            if not fired and os.fstat(fd).st_ino == os.stat(file.parent).st_ino:
                fired = True; file.parent.rename(file.parent.parent / 'moved')
                file.parent.mkdir(mode=0o700)
            return entries
        with patch('os.scandir', side_effect=swap):
            r = scan(str(self.root), environment='developer')
        self.assertTrue(r['directoryChanged'])

    def test_fixture_limit_and_no_regular_open(self):
        self.fixture_file(); real = os.open
        def only_dir(p, flags, *args, **kwargs):
            self.assertTrue(flags & os.O_DIRECTORY)
            return real(p, flags, *args, **kwargs)
        with patch('os.open', side_effect=only_dir):
            self.assertEqual(len(scan(str(self.root), environment='developer')['files']), 2)
        with self.assertRaisesRegex(ValueError, '^limit_exceeded$'):
            scan(str(self.root), limit=3, environment='developer')

    def test_fixture_timeout_not_swallowed_as_io_error(self):
        self.fixture_file(); real = os.stat
        def timeout(p, *args, **kwargs):
            if p == 'car.jpg':
                raise TimeoutError()
            return real(p, *args, **kwargs)
        with patch('os.stat', side_effect=timeout):
            with self.assertRaises(TimeoutError):
                scan(str(self.root), environment='developer')

    def test_canonical_access_denied_reason_preserved(self):
        real = os.scandir; inode = os.stat(self.root / 'originals').st_ino
        def denied(fd):
            if os.fstat(fd).st_ino == inode:
                raise PermissionError()
            return real(fd)
        with patch('os.scandir', side_effect=denied):
            r = scan(str(self.root))
        self.assertEqual(r['issues']['originals'], 'access_denied')

    def test_absent_derivatives_reaches_comparison(self):
        from audit import compare
        (self.root / 'derivatives').rmdir()
        result = None
        try:
            result = scan(str(self.root))
        except FileNotFoundError:
            pass
        self.assertIsNotNone(result, 'verified child absence must reach comparison')
        r = compare([], [], result, scan(str(self.root)))
        self.assertTrue(r['observationComplete'])
        self.assertEqual(r['directories']['derivatives'], 'absent')

    def test_child_errors_are_not_absence(self):
        import errno
        real = os.stat
        for error in (PermissionError(errno.EACCES, 'private'), OSError(errno.EIO, 'private')):
            def fail(p, *args, **kwargs):
                if p == 'derivatives':
                    raise error
                return real(p, *args, **kwargs)
            with patch('os.stat', side_effect=fail):
                r = scan(str(self.root))
            self.assertEqual(r['directories']['derivatives']['state'], 'unreadable')

    def test_missing_root_refused(self):
        with self.assertRaises(FileNotFoundError):
            scan(str(self.root / 'missing'))

    def test_child_creation_during_scan_is_unstable(self):
        (self.root / 'derivatives').rmdir()
        real = os.stat; calls = 0
        def create(p, *args, **kwargs):
            nonlocal calls
            if p == 'derivatives':
                calls += 1
                if calls == 2:
                    (self.root / 'derivatives').mkdir(mode=0o700)
            return real(p, *args, **kwargs)
        with patch('os.stat', side_effect=create):
            r = scan(str(self.root))
        self.assertEqual(r['directories']['derivatives']['state'], 'unstable')

    def test_child_deletion_during_scan_is_unstable(self):
        real = os.scandir
        def remove(fd):
            entries = real(fd)
            if os.fstat(fd).st_ino == os.stat(self.root / 'derivatives').st_ino:
                (self.root / 'derivatives').rmdir()
            return entries
        with patch('os.scandir', side_effect=remove):
            r = scan(str(self.root))
        self.assertEqual(r['directories']['derivatives']['state'], 'unstable')

    def test_replacement_between_scans_suppresses_missing(self):
        from audit import compare
        a = scan(str(self.root))
        (self.root / 'derivatives').rename(self.root / 'old')
        (self.root / 'derivatives').mkdir(mode=0o700)
        b = scan(str(self.root))
        r = compare([], [], a, b)
        self.assertFalse(r['observationComplete'])
        self.assertIsNone(r['missingReadyDerivatives'])

    def test_child_wrong_owner_and_symlink_are_unsafe(self):
        from types import SimpleNamespace
        real = os.stat
        def owner(p, *args, **kwargs):
            s = real(p, *args, **kwargs)
            return SimpleNamespace(st_mode=s.st_mode, st_uid=99999) if p == 'derivatives' else s
        with patch('os.stat', side_effect=owner):
            self.assertEqual(scan(str(self.root))['directories']['derivatives']['state'], 'unsafe')
        (self.root / 'derivatives').rmdir()
        os.symlink('/etc', self.root / 'derivatives')
        self.assertEqual(scan(str(self.root))['directories']['derivatives']['state'], 'unsafe')

    def test_limit_and_deadline_not_empty(self):
        with self.assertRaisesRegex(ValueError, '^limit_exceeded$'):
            scan(str(self.root), limit=1)
        with self.assertRaisesRegex(TimeoutError, ''):
            scan(str(self.root), seconds=0)

    def test_permission_denied_not_missing(self):
        original = os.scandir
        with patch('os.scandir', side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                scan(str(self.root))

    def test_directory_swap_to_symlink_is_detected(self):
        original = os.scandir; fired = False
        def swap(fd):
            nonlocal fired
            result = original(fd)
            if not fired and os.fstat(fd).st_ino == os.stat(self.root / 'originals').st_ino:
                fired = True
                os.rename(self.root / 'originals', self.root / 'moved')
                os.symlink('/etc', self.root / 'originals')
            return result
        with patch('os.scandir', side_effect=swap):
            r = scan(str(self.root))
        self.assertTrue(r['directoryChanged'])

    def test_file_swap_to_symlink_is_never_followed(self):
        original = os.stat; fired = False
        def swap(p, *args, **kwargs):
            nonlocal fired
            info = original(p, *args, **kwargs)
            if not fired and p == self.file.name:
                fired = True
                self.file.unlink(); os.symlink('/etc/passwd', self.file)
            return info
        with patch('os.stat', side_effect=swap):
            r = scan(str(self.root))
        self.assertEqual(len(r['unsafe']), 1)
        self.assertEqual(len(r['files']), 0)


if __name__ == '__main__':
    unittest.main()
