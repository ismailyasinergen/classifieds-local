"""Directory descriptors and metadata only: never open regular media files."""
import os
import re
import stat
import time


def signature(s):
    # Preserve inode/nanosecond precision through the Node JSON pipe.
    return [str(s.st_dev), str(s.st_ino), str(s.st_mode), str(s.st_nlink), str(s.st_uid), str(s.st_gid),
            s.st_size, str(s.st_mtime_ns), str(s.st_ctime_ns)]


def open_directory(name, parent=None):
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if (not stat.S_ISDIR(before.st_mode) or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid() or stat.S_IMODE(before.st_mode) != (0o755 if parent is None else 0o700)
            or parent is not None and before.st_dev != os.fstat(parent).st_dev):
        raise ValueError('unsafe_entry')
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        raise ValueError('unstable') from None
    if signature(before) != signature(os.fstat(fd)):
        os.close(fd)
        raise ValueError('unstable')
    return fd, before


def directory_state(name, parent):
    try:
        fd, info = open_directory(name, parent)
        return fd, {'state': 'present', 'identity': signature(info)}
    except FileNotFoundError:
        return None, {'state': 'absent', 'identity': None}
    except TimeoutError:
        raise
    except PermissionError:
        return None, {'state': 'unreadable', 'identity': None, 'reason': 'access_denied'}
    except OSError:
        return None, {'state': 'unreadable', 'identity': None, 'reason': 'io_error'}
    except ValueError as error:
        return None, {'state': 'unstable' if str(error) == 'unstable' else 'unsafe', 'identity': None}


def scan(root='/media', limit=10000, seconds=20, environment='original'):
    if environment not in ('developer', 'original'):
        raise ValueError('input_refused')
    deadline = time.monotonic() + seconds
    result = {'files': {}, 'unsafe': [], 'issues': {}, 'directoryChanged': False, 'entries': 0,
              'directories': {}, 'fixtureDirectories': {}, 'environment': environment}
    def flag(name, reason):
        result['unsafe'].append(name)
        result['issues'][name] = reason
    def tick():
        if time.monotonic() >= deadline:
            raise TimeoutError()
        result['entries'] += 1
        if result['entries'] > limit:
            raise ValueError('limit_exceeded')
    fd, root_before = open_directory(root)
    result['directories']['root'] = {'state': 'present', 'identity': signature(root_before)}
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                tick()
                if entry.name not in ('originals', 'derivatives') and not (environment == 'developer' and entry.name == 'search-fixtures'):
                    flag(entry.name, 'unknown_entry')
        for part in ('originals', 'derivatives'):
            child, state = directory_state(part, fd)
            result['directories'][part] = state
            if child is None:
                continue
            before = os.fstat(child)
            try:
                with os.scandir(child) as entries:
                    for entry in entries:
                        tick()
                        name = part + '/' + entry.name
                        try:
                            s = os.stat(entry.name, dir_fd=child, follow_symlinks=False)
                            if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or s.st_dev != before.st_dev:
                                flag(name, 'unsafe_object')
                                continue
                            after = os.stat(entry.name, dir_fd=child, follow_symlinks=False)
                            if signature(s) != signature(after):
                                flag(name, 'unstable')
                            else:
                                result['files'][name] = signature(s)
                        except FileNotFoundError:
                            flag(name, 'unstable')
                if signature(before) != signature(os.fstat(child)):
                    result['directoryChanged'] = True
                    state['state'] = 'unstable'
            except TimeoutError:
                raise
            except PermissionError:
                state['state'] = 'unreadable'; state['reason'] = 'access_denied'
                flag(part, 'access_denied')
            except OSError:
                state['state'] = 'unreadable'; state['reason'] = 'io_error'
                flag(part, 'io_error')
            finally:
                os.close(child)
        if environment == 'developer':
            fixture, state = directory_state('search-fixtures', fd)
            result['directories']['searchFixtures'] = state
            if fixture is not None:
                def check_directory(child, before, name, parent, record):
                    check, after = directory_state(name, parent)
                    if check is not None:
                        os.close(check)
                    if record != after or signature(before) != signature(os.fstat(child)):
                        record['state'] = 'unstable'
                        result['directoryChanged'] = True
                initial = os.fstat(fixture)
                try:
                    with os.scandir(fixture) as runs:
                        for entry in runs:
                            tick()
                            prefix = 'search-fixtures/' + entry.name
                            if not re.fullmatch('[a-f0-9]{16}', entry.name):
                                flag(prefix, 'unknown_entry')
                                continue
                            child, record = directory_state(entry.name, fixture)
                            result['fixtureDirectories'][prefix] = record
                            # An enumerated directory disappearing is a race, not stable absence.
                            if record['state'] == 'absent':
                                record['state'] = 'unstable'
                            if child is None:
                                continue
                            before = os.fstat(child)
                            try:
                                with os.scandir(child) as files:
                                    for item in files:
                                        tick(); name = prefix + '/' + item.name
                                        if item.name != 'car.jpg':
                                            flag(name, 'unknown_entry')
                                            continue
                                        try:
                                            info = os.stat(item.name, dir_fd=child, follow_symlinks=False)
                                            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_dev != before.st_dev
                                                    or info.st_uid != before.st_uid or info.st_gid != before.st_gid or stat.S_IMODE(info.st_mode) != 0o600):
                                                flag(name, 'unsafe_object')
                                            elif signature(info) != signature(os.stat(item.name, dir_fd=child, follow_symlinks=False)):
                                                flag(name, 'unstable')
                                            else:
                                                result['files'][name] = signature(info)
                                        except FileNotFoundError:
                                            flag(name, 'unstable')
                                        except TimeoutError:
                                            raise
                                        except PermissionError:
                                            flag(name, 'access_denied')
                                        except OSError:
                                            flag(name, 'io_error')
                            except TimeoutError:
                                raise
                            except PermissionError:
                                record['state'] = 'unreadable'; flag(prefix, 'access_denied')
                            except OSError:
                                record['state'] = 'unreadable'; flag(prefix, 'io_error')
                            finally:
                                try:
                                    check_directory(child, before, entry.name, fixture, record)
                                finally:
                                    os.close(child)
                    check_directory(fixture, initial, 'search-fixtures', fd, state)
                except TimeoutError:
                    raise
                except PermissionError:
                    state['state'] = 'unreadable'; flag('search-fixtures', 'access_denied')
                except OSError:
                    state['state'] = 'unreadable'; flag('search-fixtures', 'io_error')
                finally:
                    os.close(fixture)
        for part in ('originals', 'derivatives'):
            check, after = directory_state(part, fd)
            if check is not None:
                os.close(check)
            if after != result['directories'][part]:
                result['directories'][part]['state'] = 'unstable'
                result['directoryChanged'] = True
        if signature(root_before) != signature(os.fstat(fd)) or signature(root_before) != signature(os.stat(root, follow_symlinks=False)):
            result['directoryChanged'] = True
            result['directories']['root']['state'] = 'unstable'
    finally:
        os.close(fd)
    return result
