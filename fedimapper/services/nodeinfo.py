from typing import Any, Dict

from .www import get_json


async def get_nodeinfo(host: str) -> Dict[Any, Any] | bool:
    try:
        reference = get_json(f"https://{host}/.well-known/nodeinfo")
        nodeinfo_url = reference.get("links", []).pop().get("href", None)
        nodeinfo = get_json(nodeinfo_url)
        return nodeinfo
    except:
        return False
