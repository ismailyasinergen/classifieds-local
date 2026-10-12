import copy
import unittest
from audit_test import asset, scan, ORIGINAL, DERIVATIVE
from audit import compare


def observed(states=None):
    s = scan({ORIGINAL: 3})
    s['directories'] = {k: {'state': v, 'identity': [k] if v == 'present' else None}
                        for k, v in dict(root='present', originals='present', derivatives='absent', **(states or {})).items()}
    return s


class AbsenceTests(unittest.TestCase):
    def test_absent_derivative_ready(self):
        s = observed(); r = compare([asset()], [asset()], s, s)
        self.assertEqual(r.get('directories'), dict(root='present', originals='present', derivatives='absent'))
        self.assertTrue(r['observationComplete']); self.assertEqual(r['missingReadyDerivatives'], 1)

    def test_pending_no_artificial_missing(self):
        s = observed(); a = [asset(state='pending', derivative='')]
        r = compare(a, a, s, s)
        self.assertEqual(r.get('directories', {}).get('derivatives'), 'absent')
        self.assertEqual(r['missingReadyDerivatives'], 0)

    def test_changed_directory_no_missing_inference(self):
        s = observed(); t = copy.deepcopy(s)
        t['directories']['derivatives'] = {'state': 'present', 'identity': ['new']}
        r = compare([asset()], [asset()], s, t)
        self.assertFalse(r['observationComplete']); self.assertIsNone(r['missingReadyDerivatives'])

    def test_unreadable_not_absent(self):
        s = observed(); s['directories']['derivatives']['state'] = 'unreadable'
        r = compare([asset()], [asset()], s, s)
        self.assertFalse(r['observationComplete']); self.assertIsNone(r['missingReadyDerivatives'])

    def test_absent_original_with_reference(self):
        s = observed(); s['files'] = {}; s['directories']['originals'] = {'state': 'absent', 'identity': None}
        r = compare([asset()], [asset()], s, s)
        self.assertEqual(r.get('directories', {}).get('originals'), 'absent')
        self.assertEqual(r['missingOriginals'], 1)

    def test_empty_database_absent_dirs(self):
        s = observed(); s['files'] = {}; s['directories']['originals'] = {'state': 'absent', 'identity': None}
        r = compare([], [], s, s)
        self.assertEqual(r.get('directories', {}).get('derivatives'), 'absent')
        self.assertTrue(r['observationComplete']); self.assertEqual(r['missingOriginals'], 0)
