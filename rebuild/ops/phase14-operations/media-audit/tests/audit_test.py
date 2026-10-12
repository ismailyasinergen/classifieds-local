import copy
import json
import sys
import unittest
import subprocess
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit import compare
from scanner import signature

KEY = 'a' * 32
ORIGINAL = 'originals/' + KEY + '.bin'
DERIVATIVE = 'derivatives/' + KEY + '.jpg'


def asset(**changes):
    return dict(dict(id=1, key=KEY, original=ORIGINAL, derivative=DERIVATIVE,
                     source_bytes=3, state='ready', links=1, retained=False), **changes)


def scan(files=None, unsafe=None):
    return dict(files={k: [1, i + 1, 32768, 1, 0, 0, v, 1, 1]
                       for i, (k, v) in enumerate((files or {}).items())}, unsafe=unsafe or [],
                environment='original', fixtureDirectories={}, issues={}, directoryChanged=False, entries=len(files or {}) + len(unsafe or []),
                directories={k: {'state': 'present', 'identity': [k]} for k in ('root', 'originals', 'derivatives')})


class CompareTests(unittest.TestCase):
    def result(self, assets=None, files=None):
        a = assets if assets is not None else [asset()]
        s = scan(files if files is not None else {ORIGINAL: 3, DERIVATIVE: 2})
        return compare(a, copy.deepcopy(a), s, copy.deepcopy(s))

    def test_healthy(self):
        r = self.result()
        self.assertTrue(r.get('observationComplete'))
        self.assertEqual(r.get('scannedAssets'), 1)
        self.assertEqual(r.get('scannedFiles'), 2)
        self.assertFalse(r.get('findingsPresent'))

    def test_missing_original_and_ready(self):
        r = self.result(files={})
        self.assertEqual((r.get('missingOriginals'), r.get('missingReadyDerivatives')), (1, 1))

    def test_empty_ready_derivative_separate(self):
        r = self.result([asset(derivative='')], {ORIGINAL: 3})
        self.assertEqual((r.get('missingReadyDerivatives'), r.get('emptyReadyDerivatives')), (1, 1))

    def test_size_mismatch(self):
        self.assertEqual(self.result(files={ORIGINAL: 4, DERIVATIVE: 2}).get('originalSizeMismatches'), 1)

    def test_pending_failed_not_missing_derivative(self):
        for state in ('pending', 'failed'):
            r = self.result([asset(state=state, derivative='')], {ORIGINAL: 3})
            self.assertEqual(r.get('missingReadyDerivatives'), 0)
            self.assertEqual(r.get('unreferencedCandidates'), 0)

    def test_shared_and_unlinked_and_evidence_retained(self):
        r = self.result([asset(links=4, retained=True)])
        self.assertEqual((r.get('multiRevisionAssets'), r.get('evidenceRetainedAssets')), (1, 1))
        r = self.result([asset(links=0, retained=True)])
        self.assertEqual((r.get('unlinkedButRetainedAssets'), r.get('unreferencedCandidates')), (1, 0))

    def test_known_uncommitted_derivative_and_tmp_are_inflight(self):
        r = self.result([asset(state='pending', derivative='')], {ORIGINAL: 3, DERIVATIVE: 2, 'derivatives/tmpCanary.tmp': 9})
        self.assertEqual((r.get('temporaryOrInflight'), r.get('unreferencedCandidates')), (2, 0))

    def test_candidate_does_not_grant_deletion(self):
        r = self.result([], {ORIGINAL: 3})
        self.assertEqual(r.get('unreferencedCandidates'), 1)
        self.assertEqual(r.get('candidateMeaning'), 'unreferenced_at_observation')
        self.assertIs(r.get('deletionAuthorized'), False)

    def test_upload_and_derivative_commit_race(self):
        s = scan({ORIGINAL: 3, DERIVATIVE: 2})
        r = compare([], [asset()], s, s)
        self.assertEqual(r.get('unreferencedCandidates'), 0)
        self.assertGreater(r.get('temporaryOrInflight', 0), 0)
        r = compare([asset(state='pending', derivative='')], [asset()], s, s)
        self.assertGreater(r.get('unreadableOrUnstable', 0), 0)

    def test_file_mutation_not_stable_size_error(self):
        s = scan({ORIGINAL: 3, DERIVATIVE: 2}); t = copy.deepcopy(s); t['files'][ORIGINAL][6] = 8
        r = compare([asset()], [asset()], s, t)
        self.assertEqual(r.get('originalSizeMismatches'), 0)
        self.assertEqual(r.get('unreadableOrUnstable'), 1)

    def test_unsafe_and_invalid_paths_never_count_missing(self):
        s = scan({DERIVATIVE: 2}, [ORIGINAL])
        r = compare([asset()], [asset()], s, s)
        self.assertEqual((r.get('missingOriginals'), r.get('unexpectedEntries')), (0, 1))
        for name in ('../secret', '/etc/passwd', 'originals/sub/x.bin'):
            r = self.result([asset(original=name)])
            self.assertGreater(r.get('unexpectedEntries', 0), 0)

    def test_sensitive_canary_absent(self):
        r = self.result([], {'originals/PRIVATE_CANARY.bin': 4})
        self.assertNotIn('PRIVATE_CANARY', json.dumps(r))

    def test_directory_race_cannot_prove_missing_files(self):
        s = scan(); s['directoryChanged'] = True
        r = compare([asset()], [asset()], s, s)
        self.assertFalse(r['observationComplete'])
        self.assertIsNone(r['missingOriginals'])
        self.assertIsNone(r['missingReadyDerivatives'])

    def test_metadata_nanoseconds_survive_node_pipe(self):
        value = SimpleNamespace(st_dev=1, st_ino=2, st_mode=32768, st_nlink=1, st_uid=0,
                                st_gid=0, st_size=3, st_mtime_ns=1800000000000000001, st_ctime_ns=1800000000000000002)
        raw = json.dumps(signature(value))
        result = subprocess.run(['node', '-e', 'let s="";process.stdin.on("data",b=>s+=b);process.stdin.on("end",()=>process.stdout.write(JSON.stringify(JSON.parse(s))));'], input=raw, text=True, capture_output=True, check=True)
        self.assertEqual(int(json.loads(result.stdout)[7]), value.st_mtime_ns)


if __name__ == '__main__':
    unittest.main()
