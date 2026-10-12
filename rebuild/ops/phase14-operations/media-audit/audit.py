"""Metadata-only comparison. Private names never leave this function's aggregate result."""
import re

COUNTS = ('scannedAssets', 'scannedFiles', 'missingOriginals', 'missingReadyDerivatives',
          'emptyReadyDerivatives', 'originalSizeMismatches', 'unlinkedButRetainedAssets',
          'unreferencedCandidates', 'temporaryOrInflight', 'unreadableOrUnstable',
          'unexpectedEntries', 'multiRevisionAssets', 'evidenceRetainedAssets', 'observedFileBytes')


def fixture_name(name):
    return isinstance(name, str) and re.fullmatch(r'search-fixtures/[a-f0-9]{16}/car\.jpg', name) is not None


def valid_name(name, prefix, environment='original'):
    if prefix == 'derivatives' and environment == 'developer' and fixture_name(name):
        return True
    return isinstance(name, str) and len(name) <= 200 and re.fullmatch(
        prefix + r'/[a-f0-9]{32}(?:_[A-Za-z0-9]{7})?\.' + ('bin' if prefix == 'originals' else 'jpg'), name) is not None


def compare(first_assets, second_assets, first_scan, second_scan, environment='original'):
    if environment not in ('developer', 'original') or any(s['environment'] != environment for s in (first_scan, second_scan)):
        raise ValueError('identity_mismatch')
    if len(first_assets) > 10000 or len(second_assets) > 10000:
        raise ValueError('limit_exceeded')
    first = {a['id']: a for a in first_assets}; second = {a['id']: a for a in second_assets}
    if len(first) != len(first_assets) or len(second) != len(second_assets):
        raise ValueError('invalid_response')
    r = dict.fromkeys(COUNTS, 0)
    r.update(observationComplete=True, findingsPresent=False, deletionAuthorized=False, fixtureLayoutEnabled=environment == 'developer',
             candidateMeaning='unreferenced_at_observation')
    r['scannedAssets'] = len(second)
    directories = {}
    for part in ('root', 'originals', 'derivatives') + (('searchFixtures',) if environment == 'developer' else ()):
        a, b = first_scan['directories'][part], second_scan['directories'][part]
        directories[part] = b['state'] if a == b else 'unstable'
    r['directories'] = directories
    fixture_dirs = {}
    for key in first_scan['fixtureDirectories'].keys() | second_scan['fixtureDirectories'].keys():
        a, b = first_scan['fixtureDirectories'].get(key), second_scan['fixtureDirectories'].get(key)
        fixture_dirs[key] = b['state'] if a == b else 'unstable'
    reasons = dict.fromkeys(('canonicalDerivativeReferences', 'fixtureDerivativeReferences', 'invalidOriginalReferences',
                            'invalidDerivativeReferences', 'unknownFilesystemEntries', 'unsafeFilesystemObjects',
                            'accessDenied', 'ioErrors', 'unstableFilesystemEntries', 'unmeasuredDerivativeReferences'), 0)
    issue_sets = {k: set() for k in ('unknown_entry', 'unsafe_object', 'access_denied', 'io_error', 'unstable')}
    for s in (first_scan, second_scan):
        for name, reason in s['issues'].items():
            issue_sets[reason].add(name)
        for name, record in {**s['directories'], **s['fixtureDirectories']}.items():
            if record['state'] in ('unreadable', 'unsafe', 'unstable'):
                issue_sets[record.get('reason', {'unreadable': 'io_error', 'unsafe': 'unsafe_object', 'unstable': 'unstable'}[record['state']])].add(name)
    for reason, field in [('unknown_entry', 'unknownFilesystemEntries'), ('unsafe_object', 'unsafeFilesystemObjects'),
                          ('access_denied', 'accessDenied'), ('io_error', 'ioErrors'), ('unstable', 'unstableFilesystemEntries')]:
        reasons[field] = len(issue_sets[reason])
    r['reasons'] = reasons
    f, g = first_scan['files'], second_scan['files']
    unsafe = set(first_scan['unsafe']) | set(second_scan['unsafe'])
    changed = {p for p in f.keys() | g.keys() if f.get(p) != g.get(p)}
    reasons['unstableFilesystemEntries'] = len(issue_sets['unstable'] | changed |
        {k for k, v in fixture_dirs.items() if v == 'unstable'} | {k for k, v in directories.items() if v == 'unstable'})
    changed_assets = {i for i in first.keys() | second.keys() if first.get(i) != second.get(i)}
    touched = {a[k] for i in changed_assets for a in (first.get(i), second.get(i)) if a
               for k in ('original', 'derivative') if a[k]}
    unstable = changed | touched
    inflight = set(unstable)
    referenced = {a[k] for a in list(first.values()) + list(second.values()) for k in ('original', 'derivative') if a[k]}
    known_derivatives = {'derivatives/' + a['key'] + '.jpg' for a in list(first.values()) + list(second.values())}
    invalid = set(unsafe)
    for a in second.values():
        p = a['derivative']
        if p:
            if valid_name(p, 'derivatives'):
                reasons['canonicalDerivativeReferences'] += 1
            elif environment == 'developer' and fixture_name(p):
                reasons['fixtureDerivativeReferences'] += 1
            else:
                reasons['invalidDerivativeReferences'] += 1
        reasons['invalidOriginalReferences'] += not valid_name(a['original'], 'originals')
        r['unlinkedButRetainedAssets'] += a['links'] == 0
        r['multiRevisionAssets'] += a['links'] > 1
        r['evidenceRetainedAssets'] += a['retained']
        if a['id'] in changed_assets:
            continue
        p = a['original']
        if not valid_name(p, 'originals'):
            invalid.add(p)
        elif p not in unstable | unsafe:
            if p not in g:
                r['missingOriginals'] += 1
            elif g[p][6] != a['source_bytes']:
                r['originalSizeMismatches'] += 1
        p = a['derivative']
        if p and not valid_name(p, 'derivatives', environment):
            invalid.add(p)
        elif a['state'] == 'ready' and p not in unstable | unsafe:
            if not p:
                r['emptyReadyDerivatives'] += 1
                r['missingReadyDerivatives'] += 1
            elif p not in g:
                r['missingReadyDerivatives'] += 1
    for p in g:
        if p in unstable | unsafe:
            continue
        if p.startswith('derivatives/') and p.endswith('.tmp'):
            inflight.add(p)
        elif p not in referenced:
            if p in known_derivatives:
                inflight.add(p)
            elif valid_name(p, 'originals') or valid_name(p, 'derivatives', environment):
                r['unreferencedCandidates'] += 1
            else:
                invalid.add(p)
    r['scannedFiles'] = len(g)
    r['observedFileBytes'] = sum(s[6] for s in g.values())
    r['temporaryOrInflight'] = len(inflight)
    r['unreadableOrUnstable'] = len(unstable | unsafe)
    r['unexpectedEntries'] = len(invalid)
    if unsafe or first_scan['directoryChanged'] or second_scan['directoryChanged']:
        r['observationComplete'] = False
        r['unreadableOrUnstable'] += int(first_scan['directoryChanged'] or second_scan['directoryChanged'])
    uncertain = {k for k, v in directories.items() if v not in ('present', 'absent')}
    uncertain_fixture_dirs = {k for k, v in fixture_dirs.items() if v not in ('present', 'absent')}
    if uncertain_fixture_dirs or 'searchFixtures' in uncertain:
        r['observationComplete'] = False
        r['missingReadyDerivatives'] = r['unreferencedCandidates'] = None
        r['unreadableOrUnstable'] += len(uncertain_fixture_dirs)
    if reasons['invalidOriginalReferences'] or reasons['invalidDerivativeReferences'] or reasons['unknownFilesystemEntries']:
        r['observationComplete'] = False
    if uncertain:
        r['observationComplete'] = False
        r['unreadableOrUnstable'] += len(uncertain)
        r['temporaryOrInflight'] += sum(v == 'unstable' for v in directories.values())
        r['unreferencedCandidates'] = None
        if 'originals' in uncertain:
            r['missingOriginals'] = r['originalSizeMismatches'] = None
        if 'derivatives' in uncertain:
            r['missingReadyDerivatives'] = None
    if first_scan['directoryChanged'] or second_scan['directoryChanged'] or 'root' in uncertain:
        for k in ('missingOriginals', 'missingReadyDerivatives', 'originalSizeMismatches', 'unreferencedCandidates'):
            r[k] = None
    for a in second.values():
        p = a['derivative']
        if p and (not valid_name(p, 'derivatives', environment) or p in unstable | unsafe or a['id'] in changed_assets
                  or r['missingReadyDerivatives'] is None):
            reasons['unmeasuredDerivativeReferences'] += 1
    r['findingsPresent'] = any(r[k] for k in ('missingOriginals', 'missingReadyDerivatives', 'originalSizeMismatches',
        'unreferencedCandidates', 'temporaryOrInflight', 'unreadableOrUnstable', 'unexpectedEntries'))
    return r
