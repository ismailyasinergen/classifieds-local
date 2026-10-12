import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from restore_runtime import extract_media


class RestoreTests(unittest.TestCase):
    name = 'originals/' + 'a' * 32 + '.bin'

    def archive(self, name=None, duplicate=False, link=False):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w') as tar:
            for _ in range(2 if duplicate else 1):
                item = tarfile.TarInfo(name or self.name)
                item.size = 3
                if link:
                    item.type = tarfile.SYMTYPE
                    item.linkname = '/etc/passwd'
                tar.addfile(item, io.BytesIO(b'abc'))
        out.seek(0)
        return out

    def inventory(self):
        return [dict(name=self.name, bytes=3, sha256=hashlib.sha256(b'abc').hexdigest())]

    def test_exact_binary_restored(self):
        with tempfile.TemporaryDirectory() as root:
            extract_media(self.archive(), Path(root), self.inventory())
            self.assertEqual((Path(root) / self.name).read_bytes(), b'abc')

    def test_bad_members_refused(self):
        for name in ('../outside', '/outside', 'a/../outside', 'derivatives/unknown.jpg'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):
                    extract_media(self.archive(name), Path(root), self.inventory())

    def test_duplicate_and_link_refused(self):
        for kwargs in (dict(duplicate=True), dict(link=True)):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):
                    extract_media(self.archive(**kwargs), Path(root), self.inventory())

    def test_wrong_digest_refused(self):
        data = self.inventory()
        data[0]['sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
            extract_media(self.archive(), Path(root), data)
