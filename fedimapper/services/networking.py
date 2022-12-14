import socket

import cymruwhois


def get_ip_from_url(url: str) -> str | bool:
    try:
        return socket.gethostbyname(url)
    except:
        return False


def get_asn_data(ip) -> cymruwhois.asrecord:
    client = cymruwhois.Client()
    return client.lookup(ip)
