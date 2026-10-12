"""Metadata and directory-open checks only; no source file contents."""
import json
import os
import stat
import sys


def require(condition):
    if not condition:
        raise ValueError('reader_preflight_refused')


def verify(profile):
    require(profile in ('nonroot', 'original-owner'))
    uid = 0 if profile == 'original-owner' else 1000
    require(os.getuid() == os.geteuid() == uid)
    require(os.getgid() == os.getegid() == uid)
    status = dict(line.split(':', 1) for line in open('/proc/self/status') if ':' in line)
    require(all(int(status[k].strip(), 16) == 0 for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')))
    require(status['NoNewPrivs'].strip() == '1')
    require(os.listdir('/sys/class/net') == ['lo'])
    for name in ('uid_map', 'gid_map'):
        require(open('/proc/self/' + name).read().split() == ['0', '0', '4294967295'])
    for index, name in enumerate(('/media', '/media/originals', '/media/derivatives')):
        info = os.lstat(name)
        require(stat.S_ISDIR(info.st_mode))
        if profile == 'original-owner':
            require(info.st_uid == info.st_gid == 0)
            require(stat.S_IMODE(info.st_mode) == (0o755 if index == 0 else 0o700))
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        os.close(fd)
    return True


if __name__ == '__main__':
    try:
        verify(sys.argv[1])
        print(json.dumps({'metadataAccessVerified': True}))
    except Exception:
        sys.stderr.write('reader_preflight_refused\n')
        sys.exit(1)
