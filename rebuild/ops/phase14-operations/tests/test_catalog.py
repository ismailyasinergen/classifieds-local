import datetime
import decimal
import unittest
import uuid
from snapshot_catalog import canonical


class CatalogTests(unittest.TestCase):
    def test_typed_stable_rows(self):
        values = [None, True, False, 1, '1', decimal.Decimal('1.20'), datetime.date(2026, 1, 1),
                  datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc), uuid.UUID(int=1), b'\x00\xff', {'b': 2, 'a': 1}]
        encoded = [canonical(v) for v in values]
        self.assertEqual(len(set(encoded)), len(values))
        self.assertEqual(canonical({'a': 1, 'b': 2}), canonical({'b': 2, 'a': 1}))

    def test_nested_and_large_rows(self):
        self.assertNotEqual(canonical([None, 'x' * 100000]), canonical([False, 'x' * 100000]))

    def test_unsupported_and_nonfinite_rejected(self):
        for value in [object(), float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                canonical(value)
