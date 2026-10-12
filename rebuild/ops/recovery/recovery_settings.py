"""Only run-owned quarantined processes import this settings overlay."""
import json
import os
import re
from pathlib import Path
from config.settings import *

if not re.fullmatch('[a-f0-9]{16}', os.environ.get('RECOVERY_RUN', '')):
    raise ValueError('recovery_identity_refused')
if os.environ.get('RECOVERY_ROLE') not in ('synthetic-source', 'synthetic-target', 'original-target'):
    raise ValueError('recovery_role_refused')
if os.environ['RECOVERY_ROLE'] != 'synthetic-source':
    key_path = Path('/run/recovery-keys.json')
    if key_path.is_symlink() or key_path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('recovery_key_refused')
    keys = json.loads(key_path.read_bytes())
    SECRET_KEY = keys['secretKey']
    SECRET_KEY_FALLBACKS = keys['fallbacks']
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_COOKIE_NAME = 'recovery_' + os.environ['RECOVERY_RUN']
CACHES['default']['KEY_PREFIX'] = SESSION_COOKIE_NAME
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1', 'web']
DEBUG = False
