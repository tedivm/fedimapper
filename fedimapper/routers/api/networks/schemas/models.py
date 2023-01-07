from typing import Dict, List

from pydantic import BaseModel

from fedimapper.routers.api.common.schemas.base import ResponseBase
from fedimapper.routers.api.common.schemas.instances import InstanceList


class NetworkStats(BaseModel):
    installs: int
    users: int | None = 0
    company: str | None
    cc: str | None
    prefix: str | None

    class Config:
        orm_mode = True


class NetworkList(ResponseBase):
    network: Dict[str, NetworkStats]


class ASN(BaseModel):
    asn: str | None
    company: str | None
    instances: List[str]


class ASNResponse(ASN, ResponseBase):
    pass


class ISP(ResponseBase):
    networks: List[ASN]
