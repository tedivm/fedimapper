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


def can_access_https(host) -> bool:
    try:
        httpx.get(f"https://{host}")
    except httpx.TransportError as exc:
        return False
    return True
