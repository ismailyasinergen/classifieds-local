"""TCP handshakes only, no HTTP, authentication, or source data reads."""
import ipaddress
import json
import socket
import sys


def probe(gateway, host_addresses):
    ipaddress.ip_address(gateway)
    for address in host_addresses:
        ipaddress.ip_address(address)
    rows = []
    for name, host, port in (
        ('host8088', 'host.docker.internal', 8088),
        ('host8089', 'host.docker.internal', 8089),
        ('gateway8088', gateway, 8088),
        ('gateway8089', gateway, 8089),
        ('external443', '1.1.1.1', 443),
    ):
        row = dict(name=name, resolved=False, connected=False, completed=False)
        try:
            addresses = [item for candidate in (host_addresses if host == 'host.docker.internal' else [host])
                         for item in socket.getaddrinfo(candidate, port, type=socket.SOCK_STREAM)]
            row['resolved'] = bool(addresses)
            for family, kind, protocol, _, address in addresses:
                with socket.socket(family, kind, protocol) as connection:
                    connection.settimeout(2)
                    try:
                        connection.connect(address)
                        row['connected'] = True
                    except (TimeoutError, ConnectionError, OSError):
                        pass
            row['completed'] = True
        except OSError:
            pass
        rows.append(row)
    return rows


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1], json.loads(sys.argv[2]))))
