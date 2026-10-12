import hashlib
import os
import re
import stat
import tarfile


def opened(root, name):
    if not re.fullmatch(r'(originals/[a-f0-9]{32}\.bin|derivatives/[a-f0-9]{32}\.jpg)', name):
        raise ValueError('media_path_refused')
    directory, leaf = name.split('/')
    base = sub = None
    try:
        base = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        sub = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=base)
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=sub)
        stream = os.fdopen(fd, 'rb')
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or details.st_size > 512 * 1024 * 1024:
            stream.close()
            raise ValueError('media_type_capacity_refused')
        return stream
    except OSError:
        raise ValueError('media_unavailable') from None
    finally:
        if sub is not None:
            os.close(sub)
        if base is not None:
            os.close(base)


def identity(stream):
    s = os.fstat(stream.fileno())
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink


def inventory(root, assets):
    entries, seen, total = [], set(), 0
    for asset in assets:
        key = asset['key']
        if not re.fullmatch('[a-f0-9]{32}', key) or asset['original'] != f'originals/{key}.bin':
            raise ValueError('media_path_refused')
        names = [(asset['original'], asset['source_bytes'])]
        if asset['state'] == 'ready':
            if asset['derivative'] != f'derivatives/{key}.jpg':
                raise ValueError('media_ready_path_refused')
            names.append((asset['derivative'], None))
        for name, expected in names:
            if name in seen:
                raise ValueError('media_duplicate')
            seen.add(name)
            with opened(root, name) as stream:
                before = identity(stream)
                if expected is not None and before[2] != expected:
                    raise ValueError('media_size_mismatch')
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(65536), b''):
                    digest.update(chunk)
                if before != identity(stream):
                    raise ValueError('media_changed')
            total += before[2]
            if total > 512 * 1024 * 1024:
                raise ValueError('media_capacity')
            entries.append({'name': name, 'bytes': before[2], 'sha256': digest.hexdigest()})
    return entries


def stream_media(root, entries, output):
    seen, total = set(), 0
    with tarfile.open(fileobj=output, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
        for entry in entries:
            name = entry['name']
            if name in seen:
                raise ValueError('media_duplicate')
            seen.add(name)
            with opened(root, name) as stream:
                before = identity(stream)
                total += before[2]
                if before[2] != entry['bytes'] or total > 512 * 1024 * 1024:
                    raise ValueError('media_size_capacity')
                digest = hashlib.sha256()

                class Reader:
                    def read(self, size):
                        data = stream.read(size)
                        digest.update(data)
                        return data

                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = before[2], 0o600, 0
                archive.addfile(info, Reader())
                if before != identity(stream) or digest.hexdigest() != entry['sha256']:
                    raise ValueError('media_changed')
