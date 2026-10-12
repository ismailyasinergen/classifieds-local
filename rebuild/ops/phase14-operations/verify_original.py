"""Read-only aggregate verification. Never authenticate a restored real account."""
import hashlib
import json
import os
import sys
from pathlib import Path


def compare_catalog(actual, expected):
    from snapshot_catalog import require_phase10_catalog
    require_phase10_catalog(actual)
    require_phase10_catalog(expected)
    if any(actual[key] != expected[key] for key in ('migrations', 'sequences', 'publicationBoundary', 'notificationState', 'storefrontState')) or set(actual['tables']) != set(expected['tables']):
        raise ValueError('snapshot_catalog_mismatch')
    variants = json.loads(Path(__file__).with_name('constraint-variants-v2.json').read_bytes())
    for table, source in expected['tables'].items():
        target = actual['tables'][table]
        if {k: v for k, v in source.items() if k != 'constraints'} != {k: v for k, v in target.items() if k != 'constraints'}:
            raise ValueError('snapshot_catalog_mismatch')
        if len(source['constraints']) != len(target['constraints']):
            raise ValueError('snapshot_catalog_mismatch')
        for before, after in zip(source['constraints'], target['constraints']):
            if before == after:
                continue
            pair = variants.get(table + '/' + before['name'])
            if (not pair or before['type'] != 'c' or before['validated'] is not True
                    or {k: v for k, v in before.items() if k != 'definition'} != {k: v for k, v in after.items() if k != 'definition'}
                    or before['definition'] not in pair or after['definition'] not in pair):
                raise ValueError('snapshot_catalog_mismatch')
    return True


def verify_sequence(sequence, last, called, boundary):
    if last + int(called) > (sequence['max'] or 0):
        return 'next_value_safe'
    # The pinned domain service always uses pk=1; its business counter is value.
    if (sequence['table'] == 'events_publicationboundary' and sequence['column'] == 'id'
            and sequence['max'] == 1 and boundary['rows'] == 1
            and boundary['minId'] == boundary['maxId'] == 1
            and boundary['idSequence'] == {'last': last, 'called': called}
            and last == 1 and called is False):
        return 'fixed_primary_key'
    raise ValueError('sequence_next_refused')


def decrypt_factors(factors, decrypt):
    counts = {'primary': 0, 'recovery': 0, 'coverage': 'unavailable'}
    for kind, data in factors:
        if kind not in ('totp', 'recovery_codes'):
            raise ValueError('mfa_type_unverified')
        field = 'secret' if kind == 'totp' else 'seed'
        if not isinstance(data.get(field), str) or not data[field]:
            raise ValueError('mfa_field_missing')
        if not decrypt(data[field]):
            raise ValueError('mfa_decryption_failed')
        counts['primary' if kind == 'totp' else 'recovery'] += 1
        counts['coverage'] = 'verified'
    return counts


def main():
    if os.environ.get('RECOVERY_ROLE') != 'original-target' or sys.argv[1] != os.environ.get('RECOVERY_RUN'):
        raise ValueError('target_identity_refused')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from snapshot_catalog import export_catalog
    from media_stream import inventory
    from psycopg import sql
    expected = json.loads(Path('/run/recovery-catalog.json').read_bytes())
    from deployment import validate_deployment
    validate_deployment(expected.get('deployment'))
    if settings.IN_APP_NOTIFICATIONS_ENABLED:
        raise ValueError('quarantine_consumer_enabled')
    checks = 1
    connection.ensure_connection()
    with connection.connection.transaction():
        connection.connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        actual = export_catalog(connection.connection)
        compare_catalog(actual, expected)
        checks += 3
        with connection.cursor() as cursor:
            for sequence in actual['sequences']:
                schema, name = sequence['sequence'].split('.')
                cursor.execute(sql.SQL('SELECT last_value,is_called FROM {}.{}').format(sql.Identifier(schema), sql.Identifier(name)))
                last, called = cursor.fetchone()
                verify_sequence(sequence, last, called, expected['publicationBoundary'])
                checks += 1
            cursor.execute("SELECT count(*) FROM pg_constraint WHERE contype='f' AND NOT convalidated")
            if cursor.fetchone()[0] != 0:
                raise ValueError('foreign_key_unvalidated')
            checks += 1
        from allauth.mfa.models import Authenticator
        from accounts.mfa_adapter import ClassifiedsMFAAdapter
        mfa = decrypt_factors(Authenticator.objects.values_list('type', 'data').iterator(), ClassifiedsMFAAdapter().decrypt)
        checks += mfa['primary'] + mfa['recovery']
    if inventory(settings.PRIVATE_MEDIA_ROOT, actual['assets']) != expected['media']:
        raise ValueError('media_mismatch')
    if hashlib.sha256(Path('/run/recovery-keys.json').read_bytes()).hexdigest() != expected['keySha256']:
        raise ValueError('key_binding_mismatch')
    if settings.EMAIL_BACKEND != 'django.core.mail.backends.dummy.EmailBackend' or settings.SESSION_ENGINE != 'django.contrib.sessions.backends.cache' or settings.SESSION_COOKIE_NAME != 'recovery_' + sys.argv[1]:
        raise ValueError('quarantine_refused')
    checks += 3
    from notification_coverage import receipt
    from storefront_coverage import receipt as storefront_receipt
    print(json.dumps({'pass': True, 'checks': checks, 'tables': len(actual['tables']),
                      'rows': sum(t['count'] for t in actual['tables'].values()),
                      'catalogSha256': hashlib.sha256(json.dumps(actual['tables'], sort_keys=True).encode()).hexdigest(),
                      'mediaFiles': len(expected['media']), 'mediaCoverage': 'verified' if expected['media'] else 'unavailable',
                      'mfa': mfa, 'keyBindingVerified': True, 'realAccountAuthenticationPerformed': False,
                      'favorites': actual['tables']['listings_favorite']['count'],
                      'savedSearches': actual['tables']['notifications_savedsearch']['count'],
                      'favoritesCoverage': 'aggregate_verified' if actual['tables']['listings_favorite']['count'] else 'empty',
                      'savedSearchesCoverage': 'aggregate_verified' if actual['tables']['notifications_savedsearch']['count'] else 'empty',
                      'notifications': receipt(actual), 'storefronts': storefront_receipt(actual)}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'pass': False, 'category': 'original_verification_failed'}))
        sys.exit(1)
