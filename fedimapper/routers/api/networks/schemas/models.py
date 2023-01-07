from typing import Dict

from pydantic import BaseModel

from fedimapper.routers.api.common.schemas.base import ResponseBase
from fedimapper.routers.api.common.schemas.instances import InstanceList


class NetworkStats(BaseModel):
    installs: int
    users: int | None = 0
    owner: str | None
    cc: str | None
    prefix: str | None

    class Config:
        orm_mode = True


class NetworkList(ResponseBase):
    network: Dict[str, NetworkStats]


class ASN(InstanceList):
    owner: str | None
