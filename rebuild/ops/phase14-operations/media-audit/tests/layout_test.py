import copy
import unittest
import json
from audit_test import asset, scan, ORIGINAL
from audit import compare

FIXTURE = 'search-fixtures/' + 'b' * 16 + '/car.jpg'


class LayoutTests(unittest.TestCase):
    def observed(self, files=None):
        s = scan(files if files is not None else {ORIGINAL: 3, FIXTURE: 2})
        s.update(environment='developer', fixtureDirectories={'search-fixtures/' + 'b' * 16: {'state': 'present', 'identity': ['child']}})
        s['directories']['searchFixtures'] = {'state': 'present', 'identity': ['namespace']}
        return s

    def result(self, rows=None, first=None, second=None):
        a = rows if rows is not None else [asset(derivative=FIXTURE)]
        s = first or self.observed()
        return compare(a, a, s, second or copy.deepcopy(s), environment='developer')

    def test_existing_producer_reference_must_be_recognized(self):
        a = [asset(derivative=FIXTURE)]
        s = scan({ORIGINAL: 3, FIXTURE: 2})
        s['environment'] = 'developer'
        s['directories']['searchFixtures'] = {'state': 'present', 'identity': ['fixture']}
        # Explicit verified environment is passed by the production transport.
        r = compare(a, a, s, copy.deepcopy(s), environment='developer')
        self.assertEqual(r['unexpectedEntries'], 0)

    def test_fixture_missing_is_real_missing(self):
        r = self.result(first=self.observed({ORIGINAL: 3}))
        self.assertTrue(r['observationComplete']); self.assertEqual(r['missingReadyDerivatives'], 1)

    def test_pending_failed_and_empty_ready(self):
        for state in ('pending', 'failed'):
            r = self.result([asset(state=state, derivative='')], self.observed({ORIGINAL: 3}))
            self.assertEqual(r['missingReadyDerivatives'], 0)
        r = self.result([asset(derivative='')], self.observed({ORIGINAL: 3}))
        self.assertEqual((r['missingReadyDerivatives'], r['emptyReadyDerivatives']), (1, 1))

    def test_canonical_and_fixture_shared(self):
        from audit_test import DERIVATIVE
        r = self.result([asset(derivative=FIXTURE, links=25), asset(id=2, links=3)], self.observed({ORIGINAL: 3, FIXTURE: 2, DERIVATIVE: 2}))
        self.assertTrue(r['observationComplete']); self.assertEqual(r['multiRevisionAssets'], 2)
        self.assertEqual(r['reasons']['fixtureDerivativeReferences'], 1)
        self.assertEqual(r['reasons']['canonicalDerivativeReferences'], 1)

    def test_original_does_not_enable_fixture_branch(self):
        s = scan({ORIGINAL: 3, FIXTURE: 2}); r = compare([asset(derivative=FIXTURE)], [asset(derivative=FIXTURE)], s, s)
        self.assertFalse(r['observationComplete']); self.assertFalse(r['fixtureLayoutEnabled'])
        self.assertEqual(r['reasons']['invalidDerivativeReferences'], 1)
        with self.assertRaisesRegex(ValueError, '^identity_mismatch$'):
            compare([], [], self.observed(), self.observed(), environment='original')

    def test_bad_fixture_paths_are_not_missing(self):
        for p in ('search-fixtures/' + 'B' * 16 + '/car.jpg', 'search-fixtures/123/car.jpg',
                  'search-fixtures/' + 'b' * 16 + '/other.jpg', '../car.jpg', '/car.jpg'):
            r = self.result([asset(derivative=p)])
            self.assertFalse(r['observationComplete']); self.assertEqual(r['reasons']['invalidDerivativeReferences'], 1)
            self.assertEqual(r['reasons']['unmeasuredDerivativeReferences'], 1)

    def test_unreferenced_fixture_no_deletion_authority(self):
        r = self.result([], self.observed({FIXTURE: 2}))
        self.assertEqual(r['unreferencedCandidates'], 1); self.assertFalse(r['deletionAuthorized'])

    def test_fixture_directory_race_no_missing(self):
        s = self.observed({ORIGINAL: 3}); t = copy.deepcopy(s)
        t['fixtureDirectories']['search-fixtures/' + 'b' * 16]['identity'] = ['replacement']
        r = self.result(first=s, second=t)
        self.assertFalse(r['observationComplete']); self.assertIsNone(r['missingReadyDerivatives'])
        self.assertEqual(r['reasons']['unmeasuredDerivativeReferences'], 1)

    def test_changed_db_reference_not_stable_missing(self):
        s = self.observed({ORIGINAL: 3})
        r = compare([asset(derivative=FIXTURE)], [asset(derivative='search-fixtures/' + 'c' * 16 + '/car.jpg')], s, s, environment='developer')
        self.assertEqual(r['missingReadyDerivatives'], 0); self.assertEqual(r['reasons']['unmeasuredDerivativeReferences'], 1)

    def test_reason_categories_private_output(self):
        s = self.observed(); s['unsafe'] = ['PRIVATE_UNKNOWN', FIXTURE]
        s['issues'] = {'PRIVATE_UNKNOWN': 'unknown_entry', FIXTURE: 'unsafe_object'}
        r = self.result(first=s)
        self.assertFalse(r['observationComplete']); self.assertEqual(r['reasons']['unknownFilesystemEntries'], 1)
        self.assertEqual(r['reasons']['unsafeFilesystemObjects'], 1)
        self.assertEqual(r['reasons']['accessDenied'], 0); self.assertEqual(r['reasons']['unstableFilesystemEntries'], 0)
        for private in ('PRIVATE_UNKNOWN', FIXTURE, 'b' * 16):
            self.assertNotIn(private, json.dumps(r))

    def test_inaccessible_fixture_unknown_not_absent(self):
        for reason in ('access_denied', 'io_error'):
            s = self.observed({ORIGINAL: 3})
            s['fixtureDirectories']['search-fixtures/' + 'b' * 16] = {'state': 'unreadable', 'identity': None, 'reason': reason}
            r = self.result(first=s)
            self.assertFalse(r['observationComplete']); self.assertIsNone(r['missingReadyDerivatives'])
            self.assertEqual(r['reasons']['accessDenied' if reason == 'access_denied' else 'ioErrors'], 1)
