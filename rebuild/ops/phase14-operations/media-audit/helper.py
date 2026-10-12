"""Private metadata pipe; stdout is captured in the controller, never logged."""
import json
import re
import signal
import sys
from audit import compare
from scanner import scan


def validate_assets(rows):
    if not isinstance(rows, list) or len(rows) > 10000:
        raise ValueError('limit_exceeded')
    for a in rows:
        if (set(a) != {'id', 'key', 'original', 'derivative', 'source_bytes', 'state', 'links', 'retained'} or
            any(type(a[k]) is not int or a[k] < 0 for k in ('id', 'source_bytes', 'links')) or
            not isinstance(a['key'], str) or re.fullmatch('[a-f0-9]{32}', a['key']) is None or
            any(not isinstance(a[k], str) or len(a[k]) > 200 for k in ('original', 'derivative')) or
            a['state'] not in ('pending', 'ready', 'failed') or type(a['retained']) is not bool):
            raise ValueError('invalid_response')


def main():
    def deadline(*_):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, deadline); signal.alarm(20)
    try:
        args = sys.argv[1:]
        environment = args[1] if len(args) == 2 else 'original'
        if environment not in ('developer', 'original') or len(args) not in (1, 2):
            raise ValueError('input_refused')
        if args[0] == 'scan':
            data = scan(environment=environment)
        elif args[0] == 'compare':
            raw = sys.stdin.buffer.read(32 * 1024 * 1024 + 1)
            if len(raw) > 32 * 1024 * 1024:
                raise ValueError('limit_exceeded')
            package = json.loads(raw)
            if not isinstance(package, list) or len(package) != 4:
                raise ValueError('invalid_response')
            validate_assets(package[0]); validate_assets(package[1])
            data = compare(*package, environment=environment)
        else:
            raise ValueError('input_refused')
        result = dict(ok=True, data=data)
    except Exception as error:
        category = ('timeout' if isinstance(error, TimeoutError) else 'access_denied' if isinstance(error, PermissionError) else
                    str(error) if isinstance(error, ValueError) and str(error) in ('identity_mismatch', 'limit_exceeded', 'unsafe_entry', 'unstable', 'invalid_response', 'input_refused') else 'invalid_response')
        result = dict(ok=False, error=category)
    print(json.dumps(result, separators=(',', ':')))


if __name__ == '__main__':
    main()
