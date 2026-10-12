"""Networkless, read-only mounted media; private pipe only."""
import json
import os
import signal
import sys
from media_stream import inventory, stream_media

try:
    signal.signal(signal.SIGALRM, lambda *_: os._exit(70))
    signal.alarm(300)
    data = sys.stdin.buffer.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('media_capacity')
    if sys.argv[1] == 'inventory':
        encoded = json.dumps(inventory('/media', json.loads(data))).encode()
        if len(encoded) > 32 * 1024 * 1024:
            raise ValueError('media_capacity')
        sys.stdout.buffer.write(encoded)
    elif sys.argv[1] == 'stream':
        stream_media('/media', json.loads(data), sys.stdout.buffer)
    else:
        raise ValueError('media_mode_refused')
except Exception:
    sys.stderr.write('original_media_failed\n')
    sys.exit(1)
