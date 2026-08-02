"""Prefer IPv4 for Email Game hosts when the launcher requests it.

This machine's IPv6 route completes TCP setup but stalls during HTTPS. Python
imports ``sitecustomize`` during startup, before requests/httpx/websockets, so a
narrow DNS-result filter fixes both the gateway and live server without changing
Windows network settings. Other hosts and normal project use are unaffected.
"""

from __future__ import annotations

import os
import socket
from typing import Any


if os.getenv("EMAIL_GAME_FORCE_IPV4", "").strip().casefold() in {
    "1",
    "true",
    "yes",
    "on",
}:
    _original_getaddrinfo = socket.getaddrinfo

    def _email_game_ipv4_getaddrinfo(
        host: Any, port: Any, *args: Any, **kwargs: Any
    ) -> list[tuple]:
        results = _original_getaddrinfo(host, port, *args, **kwargs)
        hostname = host.decode("ascii", "ignore") if isinstance(host, bytes) else str(host)
        if hostname.casefold().endswith(".theemailgame.com"):
            ipv4 = [result for result in results if result[0] == socket.AF_INET]
            if ipv4:
                return ipv4
        return results

    socket.getaddrinfo = _email_game_ipv4_getaddrinfo
