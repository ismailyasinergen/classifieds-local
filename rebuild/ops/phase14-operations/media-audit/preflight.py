"""Phase 9 fixed-directory metadata only; absent children are not access failures."""
import json
import os
from scanner import open_directory, directory_state, signature


def verify():
    states = dict.fromkeys(('root', 'originals', 'derivatives'), 'unsafe')
    try:
        if not os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 0:
            raise ValueError()
        with open('/proc/self/status') as stream:
            status = dict(line.split(':', 1) for line in stream if ':' in line)
        if (any(int(status[k].strip(), 16) for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'))
                or status['NoNewPrivs'].strip() != '1' or os.listdir('/sys/class/net') != ['lo']):
            raise ValueError()
        for name in ('uid_map', 'gid_map'):
            with open('/proc/self/' + name) as stream:
                if stream.read().split() != ['0', '0', '4294967295']:
                    raise ValueError()
        fd, before = open_directory('/media')
        try:
            states['root'] = 'present'
            for part in ('originals', 'derivatives'):
                child, state = directory_state(part, fd)
                states[part] = state['state']
                if child is not None:
                    os.close(child)
            if signature(before) != signature(os.fstat(fd)) or signature(before) != signature(os.lstat('/media')):
                states['root'] = 'unstable'
        finally:
            os.close(fd)
        return {'metadataAccessVerified': all(s in ('present', 'absent') for s in states.values()), 'directories': states}
    except OSError:
        states['root'] = 'unreadable'
    except ValueError:
        pass
    return {'metadataAccessVerified': False, 'directories': states}


if __name__ == '__main__':
    print(json.dumps(verify()))
