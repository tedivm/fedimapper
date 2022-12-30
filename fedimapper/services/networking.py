import socket

import cymruwhois
import httpx


def get_ip_from_url(url: str) -> str | bool:
    try:
        return socket.gethostbyname(url)
    except:
        return False


def get_asn_data(ip) -> cymruwhois.asrecord:
    client = cymruwhois.Client()
    return client.lookup(ip)


def can_access_https(host) -> bool | httpx.Response:
    try:
        response = httpx.get(f"https://{host}")
        if response.status_code in [502, 503, 504, 404]:
            return False
        return response
    except httpx.TransportError as exc:
        return False
