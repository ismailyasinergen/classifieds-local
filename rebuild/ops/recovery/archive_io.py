import hashlib
import json
import os
import re
from pathlib import Path
import stat
import sys
import tarfile


def stream_safe_source(manifest, root, output):
    seen = set()
    with tarfile.open(fileobj=output, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
        for entry in manifest:
            name = entry['path']
            if (not (name.startswith('rebuild/') or name == '.github/workflows/rebuild-ci.yml') or
                    any(part in ('', '.', '..') for part in name.split('/')) or '\\' in name or name in seen or
                    (re.search(r'(^|/)\.env($|\.)', name) and not name.endswith('.example'))):
                raise ValueError('source_path_refused')
            seen.add(name)
            current = Path(root)
            for part in name.split('/'):
                current /= part
                if current.is_symlink():
                    raise ValueError('source_link_refused')
            info = current.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 32 * 1024 * 1024:
                raise ValueError('source_file_refused')
            data = current.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('source_hash_refused')
            import io
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(data), 0o600, 0
            archive.addfile(member, io.BytesIO(data))


if __name__ == '__main__':
    try:
        definition = json.load(sys.stdin)
        encoded = ''.join(entry['sha256'] + '  ' + entry['path'] + '\n' for entry in definition).encode()
        if len(definition) != 273 or hashlib.sha256(encoded).hexdigest() != '591d1f543f8f8b555a2ece43964980d155ee5b78c9d50753c1cb9908abb81680':
            raise ValueError('source_manifest_refused')
        stream_safe_source(definition, '/source', sys.stdout.buffer)
    except Exception:
        sys.stderr.write('source_archive_failed\n')
        sys.exit(1)
