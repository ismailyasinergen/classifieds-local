"""Catalog acceptance precedes behavior writes; real targets cannot enter this module."""
import json
import hashlib
import os
import sys
from pathlib import Path


def require_synthetic(role, run, expected_run, mode):
    if role != 'synthetic-target' or run != expected_run or mode not in ('catalog', 'behavior'):
        raise ValueError('synthetic_target_required')


def main():
    require_synthetic(os.environ.get('RECOVERY_ROLE'), sys.argv[1], os.environ.get('RECOVERY_RUN'), sys.argv[2])
    import django
    django.setup()
    from django.db import connection
    from django.conf import settings
    from accounts.models import Storefront, User
    from accounts.storefronts import change_storefront, StorefrontConflict
    from django.test import Client
    from django.urls import reverse
    from snapshot_catalog import export_catalog
    from verify_original import compare_catalog
    from deployment import validate_deployment
    checks = 0
    def check(ok):
        nonlocal checks
        if not ok:
            raise ValueError('storefront_restore_assertion')
        checks += 1
    check(settings.IN_APP_NOTIFICATIONS_ENABLED is False)
    expected = json.loads(Path('/run/recovery-catalog.json').read_bytes())
    check(bool(validate_deployment(expected.get('deployment'))))
    if sys.argv[2] == 'catalog':
        connection.ensure_connection()
        with connection.connection.transaction():
            connection.connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            actual = export_catalog(connection.connection)
            check(compare_catalog(actual, expected))
            state = actual['storefrontState']
            check(state['count'] == 4 and state['published'] == 2 and state['unpublished'] == 2)
            check(state['neverPublished'] == 1 and state['withdrawn'] == 1)
            check(state['draftDiffersFromPublic'] == 2)
            check(not any(s['table'] == 'accounts_storefront' for s in actual['sequences']))
        Path('/run/storefront-catalog-verified.json').write_text(json.dumps({
            'run': sys.argv[1], 'catalogSha256': hashlib.sha256(Path('/run/recovery-catalog.json').read_bytes()).hexdigest()}))
        print(json.dumps({'pass': True, 'checks': checks, 'storefronts': 4, 'catalogOnly': True,
            'consumerDisabled': True, 'deploymentBytesVerified': True}))
        return
    marker = json.loads(Path('/run/storefront-catalog-verified.json').read_bytes())
    check(marker == {'run': sys.argv[1], 'catalogSha256': hashlib.sha256(Path('/run/recovery-catalog.json').read_bytes()).hexdigest()})
    from snapshot_catalog import canonical
    from listings.models import Listing, ListingRevision
    from events.models import OutboxEvent
    from notifications.models import SavedSearch
    def protected():
        return [canonical(list(model.objects.order_by('pk').values())) for model in
            (Listing, ListingRevision, OutboxEvent, SavedSearch)]
    before = protected()
    actor = User.objects.get(email='phase11-1@example.test')
    other = User.objects.get(email='phase11-2@example.test')
    row = Storefront.objects.get(owner=actor)
    identity, version = row.pk, row.edit_version
    public = reverse('storefronts:public', args=[row.pk])
    anonymous = Client()
    response = anonymous.get(public)
    check(response.status_code == 200 and 'Kurtarma vitrini 0'.encode() in response.content)
    for canary in ['P15_PRIVATE_DRAFT_CANARY', 'P15_PRIVATE_INTRO_CANARY', 'P15_PRIVATE_ACCOUNT_CANARY',
            'P15_PRIVATE_LISTING_CANARY', actor.email, other.email, 'Vitrin örnek 1']:
        check(canary.encode() not in response.content)
    check('Vitrin örnek 0'.encode() in response.content)
    response = anonymous.get(public, {'q': 'Vitrin', 'owner': str(other.pk)})
    check('Vitrin örnek 0'.encode() in response.content and 'Vitrin örnek 1'.encode() not in response.content)
    from unittest.mock import patch
    with patch('accounts.storefront_views.matching_public_listings', side_effect=AssertionError('query_forbidden')):
        check(anonymous.get(public, {'price_min': 'invalid'}).status_code == 200)
    check(b'/kayitli-aramalarim/olustur' not in response.content)
    own = Client()
    own.force_login(actor)
    preview = reverse('storefronts:preview', args=[identity])
    response = own.get(preview)
    check(response.status_code == 200 and b'P15_PRIVATE_DRAFT_CANARY' in response.content)
    check('no-store' in response['Cache-Control'])
    intruder = Client()
    intruder.force_login(other)
    check(intruder.get(preview).status_code == 404)
    for action in ['save', 'publish', 'unpublish']:
        check(intruder.post(reverse('storefronts:'+action, args=[identity]),
            {'edit_version': version, 'name': 'Foreign write', 'intro': ''}).status_code == 404)
    for email in ['phase11-2@example.test', 'p13-23@example.test', 'p13-24@example.test']:
        hidden = Storefront.objects.get(owner__email=email)
        check(anonymous.get(reverse('storefronts:public', args=[hidden.pk])).status_code == 404)
    try:
        change_storefront(actor=actor, storefront_id=identity, expected_version=version-1,
            action='save', name='stale', intro='')
    except StorefrontConflict:
        check(True)
    else:
        check(False)
    row = change_storefront(actor=actor, storefront_id=identity, expected_version=version,
        action='save', name='Yeni kurtarma vitrini', intro='Yeni public tanıtım')
    check(row.pk == identity and row.edit_version == version+1 and row.published_name == 'Kurtarma vitrini 0')
    row = change_storefront(actor=actor, storefront_id=identity, expected_version=row.edit_version, action='publish')
    check(row.pk == identity and row.edit_version == version+2 and row.published_name == 'Yeni kurtarma vitrini')
    check('Yeni kurtarma vitrini'.encode() in anonymous.get(public).content)
    row = change_storefront(actor=actor, storefront_id=identity, expected_version=row.edit_version, action='unpublish')
    check(row.pk == identity and row.edit_version == version+3 and anonymous.get(public).status_code == 404)
    check(before == protected())
    print(json.dumps({'pass': True, 'checks': checks, 'storefronts': 4, 'syntheticWritesOnly': True,
        'draftPrivacyVerified': True, 'ownerScopeVerified': True, 'beatEvidence': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'pass': False, 'category': 'storefront_restore_failed'}))
        sys.exit(1)
