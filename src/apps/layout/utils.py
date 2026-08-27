"""
Esup-Pod - Internal request helper.

Determines whether a request comes from a trusted internal source:
  - Loopback (127.0.0.1, ::1)
  - Docker bridge / private networks (172.x.x.x, 10.x.x.x, 192.168.x.x)

This is used by localhost-only admin endpoints (block sync) instead of a token,
since the Next.js server always runs on the same host or internal Docker network.
"""

import ipaddress


def is_internal_request(request) -> bool:
    """
    Return True if the request originates from a loopback or private (RFC 1918) address.

    Accepts:
    - 127.0.0.1 / ::1                      (true localhost)
    - 172.16.0.0/12                         (Docker bridge default range)
    - 10.0.0.0/8                            (Docker/internal networks)
    - 192.168.0.0/16                        (LAN)
    """
    ip_str = request.META.get("REMOTE_ADDR", "")
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_loopback or addr.is_private
    except ValueError:
        return False
