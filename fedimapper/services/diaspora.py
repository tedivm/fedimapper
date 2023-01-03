import ipaddress
from typing import Any, Dict, Set

from .www import get_json


def get_peers(host: str) -> Set[str] | bool:

    try:
        peers = get_json(f"https://{host}/pods.json")
    except:
        return False

    filtered_peers = set([])
    for peer in peers:
        try:
            # We actually want this to fail.
            ipaddress.ip_address(peer["host"])
        except:
            # Since this isn't an IP address we keep it.
            filtered_peers.add(peer["host"])

    return filtered_peers
