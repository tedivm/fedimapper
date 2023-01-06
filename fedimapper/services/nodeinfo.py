from logging import getLogger
from typing import Any, Dict, List, cast

from pydantic import BaseModel, ConstrainedStr

from fedimapper.settings import settings

from .www import get_json

logger = getLogger(__name__)


class LowerCaseStr(ConstrainedStr):
    to_lower = True


class NodeInfoSoftware(BaseModel):
    name: LowerCaseStr
    version: str
    repository: str | None
    homepage: str | None


class NodeInfoUsers(BaseModel):
    total: int | None
    activeHalfyear: int | None
    activeMonth: int | None


class NodeInfoUsage(BaseModel):
    users: NodeInfoUsers = NodeInfoUsers()
    localPosts: int | None
    localComments: int | None


class NodeInfoServices(BaseModel):
    inbound: List[LowerCaseStr] = []
    outbound: List[LowerCaseStr] = []


class NodeInfoInstance(BaseModel):
    version: str
    software: NodeInfoSoftware
    protocols: List[LowerCaseStr] | NodeInfoServices = []
    services: NodeInfoServices = NodeInfoServices()
    usage: NodeInfoUsage = NodeInfoUsage()
    openRegistrations: bool
    metadata: Dict[Any, Any] = {}


async def get_nodeinfo(host: str) -> NodeInfoInstance | None:
    try:
        reference = get_json(f"https://{host}/.well-known/nodeinfo")
        nodeinfo_url = reference.get("links", []).pop().get("href", None)
        nodeinfo = get_json(nodeinfo_url)
    except:
        return None

    try:
        instance = NodeInfoInstance.parse_obj(nodeinfo)
        return instance
    except:
        logger.exception(f"Unable to parse nodeinfo for host {host}")
        return None
