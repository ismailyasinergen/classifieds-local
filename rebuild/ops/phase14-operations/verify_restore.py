"""Aggregate verification; no decrypted values or private rows leave this process."""
import hashlib
import json
import os
import sys
from pathlib import Path

checks = []


def check(ok, name):
    if not ok:
        raise ValueError(name)
    checks.append(name)


def main():
    check(os.environ.get('RECOVERY_ROLE') == 'synthetic-target' and sys.argv[1] == os.environ.get('RECOVERY_RUN'), 'target_identity')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from snapshot_catalog import export_catalog
    from media_stream import inventory
    expected = json.loads(Path('/run/recovery-catalog.json').read_bytes())
    from deployment import validate_deployment
    validate_deployment(expected.get('deployment'))
    if settings.IN_APP_NOTIFICATIONS_ENABLED:
        raise ValueError('quarantine_consumer_enabled')
    connection.ensure_connection()
    with connection.connection.transaction():
        connection.connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        actual = export_catalog(connection.connection)
    from verify_original import compare_catalog
    check(compare_catalog(actual, expected), 'all_table_counts_digests_schema')
    check(actual['migrations'] == expected['migrations'], 'migration_catalog')
    check(actual['publicationBoundary'] == expected['publicationBoundary'], 'publication_boundary_preserved')
    check(actual['sequences'] == expected['sequences'], 'sequence_columns_maxima')
    from psycopg import sql
    with connection.cursor() as cursor:
        for sequence in actual['sequences']:
            schema, name = sequence['sequence'].split('.')
            cursor.execute(sql.SQL('SELECT last_value,is_called FROM {}.{}').format(sql.Identifier(schema), sql.Identifier(name)))
            last, called = cursor.fetchone()
            from verify_original import verify_sequence
            check(bool(verify_sequence(sequence, last, called, expected['publicationBoundary'])), 'sequence_contract_preserved')
        cursor.execute('SELECT count(*) FROM pg_constraint WHERE contype=\'f\' AND NOT convalidated')
        check(cursor.fetchone()[0] == 0, 'foreign_keys_validated')
    check(inventory(settings.PRIVATE_MEDIA_ROOT, actual['assets']) == expected['media'], 'media_bytes_digests')
    check(hashlib.sha256(Path('/run/recovery-keys.json').read_bytes()).hexdigest() == expected['keySha256'], 'backup_key_binding')
    from accounts.models import User
    check(not User.objects.filter(first_name='after-snapshot').exists(), 'concurrent_later_mutation_excluded')
    from allauth.mfa.models import Authenticator
    from accounts.mfa_adapter import ClassifiedsMFAAdapter, MFAStorageError
    from django.test import Client, override_settings
    from accounts.mfa_policy import PROOF_SESSION_KEY, has_mfa_proof
    from types import SimpleNamespace
    from django.urls import reverse
    from django.core.cache import cache
    check(cache.get('phase7-source-canary') is None, 'source_cache_not_cloned')
    from django.contrib.sessions.models import Session
    old_session = Session.objects.get()
    old_client = Client()
    old_client.cookies[settings.SESSION_COOKIE_NAME] = old_session.session_key
    check(old_client.get(reverse('listings:dashboard')).status_code == 302, 'source_session_credential_refused')
    factors = list(Authenticator.objects.filter(type='totp'))
    check(len(factors) == 3, 'nonempty_mfa')
    adapter = ClassifiedsMFAAdapter()
    for factor in factors:
        check(bool(adapter.decrypt(factor.data['secret'])), 'mfa_ciphertext_decrypted')
        with override_settings(SECRET_KEY='synthetic-wrong-key', SECRET_KEY_FALLBACKS=[]):
            try:
                adapter.decrypt(factor.data['secret'])
            except MFAStorageError:
                check(True, 'wrong_key_refused')
            else:
                check(False, 'wrong_key_refused')
    owner = User.objects.get(email='owner@example.test')
    recovery = Authenticator.objects.get(user=owner, type='recovery_codes').wrap()
    check(len(recovery.get_unused_codes()) == 9, 'used_recovery_state_preserved')
    from moderation.models import ReportDecision, AppealDecision, Restriction
    from conversations.models import UserBlock
    decision = ReportDecision.objects.get()
    check(AppealDecision.objects.get().actor_id != decision.actor_id, 'independent_reviewers_preserved')
    check(Restriction.objects.filter(revoked_at=None, listing__isnull=False).count() == 1 and Restriction.objects.filter(revoked_at=None, seller__email='p13-24@example.test').count() == 1 and Restriction.objects.filter(revoked_at=None).count() == 2 and UserBlock.objects.count() == 1, 'restrictions_preserved')
    reviewer = decision.actor
    password_only = Client(enforce_csrf_checks=True)
    password_only.force_login(reviewer)
    check(password_only.get(reverse('moderation:report_queue')).status_code == 302 and PROOF_SESSION_KEY not in password_only.session, 'password_only_role_refused')
    client = Client(enforce_csrf_checks=True)
    check(client.get(reverse('account_login')).status_code == 200, 'login_form')

    def post(url, data):
        data = dict(data, csrfmiddlewaretoken=client.cookies['csrftoken'].value)
        return client.post(url, data)

    response = post(reverse('account_login'), {'login': owner.email, 'password': 'password'})
    check(response.status_code == 302 and '_auth_user_id' not in client.session, 'normal_login_requires_mfa')
    code = recovery.get_unused_codes()[0]
    check(post(reverse('mfa_authenticate'), {'code': code}).status_code == 302, 'real_recovery_http_success')
    check(has_mfa_proof(SimpleNamespace(user=owner, session=client.session)), 'bound_proof_created')
    replay = Client(enforce_csrf_checks=True)
    replay.force_login(owner)
    replay.get(reverse('mfa_reauthenticate'))
    response = replay.post(reverse('mfa_reauthenticate'), {'code': code, 'csrfmiddlewaretoken': replay.cookies['csrftoken'].value})
    check(response.status_code == 200 and PROOF_SESSION_KEY not in replay.session, 'recovery_replay_refused')
    from media.models import MediaAsset
    ready = MediaAsset.objects.get(state='ready')
    for route in ('original', 'derivative'):
        response = client.get(reverse('media:' + route, args=[ready.pk]))
        check(response.status_code == 200 and 'no-store' in response['Cache-Control'], 'private_media_authorized')
        response.close()
        outsider = Client()
        check(outsider.get(reverse('media:' + route, args=[ready.pk])).status_code in (302, 403), 'private_media_anonymous_refused')
    check(Client().get(reverse('listings:detail', args=[decision.report.revision.listing_id])).status_code == 404, 'hidden_listing_stays_hidden')
    from listings.models import Listing
    public = Listing.objects.filter(lifecycle='live', public_revision__title='Public recovery fixture').exclude(pk=decision.report.revision.listing_id).get()
    check(Client().get(reverse('listings:detail', args=[public.pk])).status_code == 200, 'public_listing_survives')
    from conversations.services import send_message
    from conversations.models import Conversation
    from django.core.exceptions import PermissionDenied
    from uuid import uuid4
    conversation = Conversation.objects.get()
    try:
        send_message(actor=conversation.initiator, conversation_id=conversation.pk, body='Synthetic blocked attempt', client_token=uuid4())
    except PermissionDenied:
        check(True, 'blocked_participant_send_refused')
    else:
        check(False, 'blocked_participant_send_refused')
    from allauth.mfa.totp.internal import auth
    from unittest.mock import patch
    primary = Authenticator.objects.get(user=owner, type='totp')
    secret = adapter.decrypt(primary.data['secret'])
    clock = SimpleNamespace(time=lambda: 1700000010)
    code = auth.format_hotp_value(auth.hotp_value(secret, int(clock.time()) // 30))
    totp_client = Client(enforce_csrf_checks=True)
    totp_client.get(reverse('account_login'))
    check(totp_client.post(reverse('account_login'), {'login': owner.email, 'password': 'password',
        'csrfmiddlewaretoken': totp_client.cookies['csrftoken'].value}).status_code == 302, 'totp_login_stage')
    with patch.object(auth, 'time', clock):
        response = totp_client.post(reverse('mfa_authenticate'), {'code': code,
            'csrfmiddlewaretoken': totp_client.cookies['csrftoken'].value})
    check(response.status_code == 302 and has_mfa_proof(SimpleNamespace(user=owner, session=totp_client.session)), 'restored_totp_source_cache_not_cloned')
    second = Client(enforce_csrf_checks=True)
    second.force_login(owner)
    second.get(reverse('mfa_reauthenticate'))
    with patch.object(auth, 'time', clock):
        response = second.post(reverse('mfa_reauthenticate'), {'code': code,
            'csrfmiddlewaretoken': second.cookies['csrftoken'].value})
    check(response.status_code == 200 and PROOF_SESSION_KEY not in second.session, 'target_totp_replay_refused')
    check(settings.EMAIL_BACKEND == 'django.core.mail.backends.dummy.EmailBackend' and settings.SESSION_ENGINE == 'django.contrib.sessions.backends.cache', 'quarantine_settings')
    print(json.dumps({'pass': True, 'checks': len(checks), 'tables': len(actual['tables']), 'mediaFiles': len(expected['media']), 'mfaPrimaryFactors': len(factors), 'checkNames': checks}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'pass': False, 'checks': len(checks), 'lastCheck': checks[-1] if checks else None,
                          'category': 'restore_verification_failed', 'type': type(error).__name__}))
        sys.exit(1)
