"""Writes only a new guarded synthetic source; stdout is aggregate status."""
import io
import json
import os
import re
import sys
import unittest
from pathlib import Path
from uuid import uuid4


def augment():
    from accounts.models import User
    from catalog.models import Category
    from listings.services import create_listing_draft
    from listings.publication import submit_revision
    from moderation.services import approve_revision
    from allauth.mfa.models import Authenticator
    from accounts.mfa_adapter import ClassifiedsMFAAdapter
    from allauth.mfa.totp.internal import auth
    from django.test import Client
    from django.urls import reverse
    from django.contrib.sessions.models import Session
    from django.contrib.sessions.backends.db import SessionStore
    from django.utils import timezone
    from datetime import timedelta
    from types import SimpleNamespace
    from unittest.mock import patch
    owner = User.objects.get(email='owner@example.test')
    if Session.objects.exists():
        raise ValueError('fixture_already_augmented')
    revision = create_listing_draft(actor=owner, category_id=Category.objects.get().pk,
        content={'title': 'Public recovery fixture', 'description': 'Synthetic recovery fixture', 'price': '10',
                 'currency': 'EUR', 'location': 'Berlin', 'attributes': {'model_year': 2020, 'area': '82.5', 'electric': False}})
    submit_revision(actor=owner, revision_id=revision.pk)
    approve_revision(actor=User.objects.get(email='other@example.test'), revision_id=revision.pk,
                     expected_public_revision_id=None, reason='Synthetic fixture')
    primary = Authenticator.objects.get(user=owner, type='totp')
    secret = ClassifiedsMFAAdapter().decrypt(primary.data['secret'])
    clock = SimpleNamespace(time=lambda: 1700000010)
    code = auth.format_hotp_value(auth.hotp_value(secret, int(clock.time()) // 30))
    client = Client(enforce_csrf_checks=True)
    client.get(reverse('account_login'))
    if client.post(reverse('account_login'), {'login': owner.email, 'password': 'password',
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value}).status_code != 302:
        raise ValueError('fixture_login_failed')
    with patch.object(auth, 'time', clock):
        response = client.post(reverse('mfa_authenticate'), {'code': code,
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value})
    if response.status_code != 302 or 'classifieds_mfa_proof' not in client.session:
        raise ValueError('fixture_totp_failed')
    Session.objects.create(session_key=client.session.session_key,
        session_data=SessionStore().encode(dict(client.session)), expire_date=timezone.now() + timedelta(hours=1))
    User.objects.filter(pk=owner.pk).update(first_name='')
    print(json.dumps({'augmented': True, 'publicListing': True, 'sourceTotpConsumed': True, 'sourceSessionRecordedInBackupData': True}))


def main():
    if (os.environ.get('RECOVERY_ROLE') != 'synthetic-source'
            or not re.fullmatch('[a-f0-9]{16}', os.environ.get('RECOVERY_RUN', ''))
            or sys.argv[1] != os.environ['RECOVERY_RUN']):
        raise ValueError('fixture_identity_refused')
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    if connection.settings_dict['NAME'] != 'recovery' or connection.settings_dict['HOST'] != 'db':
        raise ValueError('fixture_database_refused')
    if len(sys.argv) == 3 and sys.argv[2] in ('hold-media', 'return-media'):
        from media.models import MediaAsset
        asset = MediaAsset.objects.get(state='ready')
        original = settings.PRIVATE_MEDIA_ROOT / asset.original.name
        held = original.with_suffix('.held')
        if original.is_symlink() or held.is_symlink():
            raise ValueError('fixture_link_refused')
        before, after = (original, held) if sys.argv[2] == 'hold-media' else (held, original)
        if not before.is_file() or after.exists():
            raise ValueError('fixture_media_state_refused')
        before.rename(after)
        print(json.dumps({'mediaMoved': True}))
        return
    if len(sys.argv) == 3 and sys.argv[2] == 'augment':
        augment()
        return
    if connection.introspection.table_names():
        raise ValueError('fixture_nonempty_refused')
    call_command('migrate', interactive=False, stdout=io.StringIO(), stderr=io.StringIO())
    from moderation.tests.case_helpers import CaseFixtures
    from moderation.tests.test_appeals import AppealCalls
    from accounts.tests.mfa_support import add_factors, authenticate_client
    from accounts.models import User
    from allauth.mfa.models import Authenticator
    from django.test import Client
    from media.models import MediaAsset, RevisionImage
    from conversations.models import UserBlock
    from PIL import Image

    class Fixture(AppealCalls, CaseFixtures, unittest.TestCase):
        pass

    fixture = Fixture()
    fixture.setUp()
    fixture.grant(fixture.case_reviewer, 'review_reports')
    fixture.grant(fixture.appeal_reviewer, 'review_appeals')
    fixture.report = fixture.report_listing().record
    fixture.decision = fixture.decide(fixture.report, action='hide_listing', expected_public_revision_id=fixture.public.pk)
    appeal = fixture.appeal().record
    fixture.resolve(appeal, outcome='uphold')
    draft = fixture.draft()
    for index, state in enumerate(('ready', 'pending')):
        key = uuid4()
        raw = io.BytesIO()
        Image.new('RGB', (8, 8), (20, 30, 40)).save(raw, format='JPEG')
        data = raw.getvalue()
        original = f'originals/{key.hex}.bin'
        derivative = f'derivatives/{key.hex}.jpg' if state == 'ready' else ''
        for name in [original] + ([derivative] if derivative else []):
            file = settings.PRIVATE_MEDIA_ROOT / name
            file.parent.mkdir(mode=0o700, exist_ok=True)
            file.write_bytes(data)
        asset = MediaAsset.objects.create(owner=fixture.owner, storage_key=key, original=original,
            derivative=derivative, source_mime='image/jpeg', source_bytes=len(data), width=8, height=8, state=state)
        RevisionImage.objects.create(revision=draft, asset=asset, position=index)
    UserBlock.objects.create(blocker=fixture.owner, blocked=fixture.reporter)
    for user in (fixture.owner, fixture.case_reviewer, fixture.appeal_reviewer):
        add_factors(user)
    client = Client()
    authenticate_client(client, fixture.owner)
    recovery = Authenticator.objects.get(user=fixture.owner, type='recovery_codes').wrap()
    if len(recovery.get_unused_codes()) != 9:
        raise ValueError('fixture_recovery_state_refused')
    # Source-only cache/session canaries are not a backup component.
    from django.core.cache import cache
    cache.set('phase7-source-canary', True, 3600)
    print(json.dumps({'seeded': True, 'users': User.objects.count(), 'media': MediaAsset.objects.count(),
                      'authenticators': Authenticator.objects.count(), 'sourceSessionPresent': bool(client.session.session_key)}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'seeded': False, 'category': 'synthetic_fixture_failed', 'type': type(error).__name__}))
        sys.exit(1)
