import unittest
from verify_original import verify_sequence


class BoundarySequenceTests(unittest.TestCase):
    def test_fixed_primary_key_is_separate_from_business_counter(self):
        row = dict(table='events_publicationboundary', column='id', max=1)
        boundary = dict(rows=1, value=88, minId=1, maxId=1, idSequence=dict(last=1, called=False))
        self.assertEqual(verify_sequence(row, 1, False, boundary), 'fixed_primary_key')
        self.assertEqual(verify_sequence(dict(table='other', column='id', max=4), 4, True, boundary), 'next_value_safe')

    def test_not_a_general_sequence_exemption(self):
        row = dict(table='events_publicationboundary', column='id', max=1)
        boundary = dict(rows=1, value=88, minId=1, maxId=1, idSequence=dict(last=1, called=False))
        for changed in [dict(row, table='other'), dict(row, column='value'), dict(row, max=2)]:
            with self.assertRaises(ValueError): verify_sequence(changed, 1, False, boundary)
        for changed in [dict(boundary, minId=2), dict(boundary, maxId=2), dict(boundary, rows=2), dict(boundary, idSequence=dict(last=2, called=False))]:
            with self.assertRaises(ValueError): verify_sequence(row, 1, False, changed)
