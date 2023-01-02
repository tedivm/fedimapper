import socket
from typing import Tuple

import cymruwhois
import httpx

from .www import get_safe


def get_ip_from_url(url: str) -> str | bool:
    try:
        return socket.gethostbyname(url)
    except:
        return False


def get_asn_data(ip) -> cymruwhois.asrecord:
    client = cymruwhois.Client()
    return client.lookup(ip)


def can_access_https(host) -> Tuple[bool | httpx.Response, str | None]:
    try:
        # Ignore Robots.txt on this call due to a chicken/egg problem- we need to know
        # if the HTTPS service is accessible before we can pull files from it, and the
        # robots.txt file can't be pulled without access to the service itself.
        response, content = get_safe(f"https://{host}", validate_robots=False)

        # Return "unreachable" for specific status codes.
        if 500 <= response.status_code <= 520 or response.status_code == 404:
            return False, None

        if content and len(content) > 0:
            return response, content.decode("utf-8")
        return response, ""

    except httpx.TransportError as exc:
        return False, None
