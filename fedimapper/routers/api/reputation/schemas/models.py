from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel

from fedimapper.routers.api.common.schemas.base import ResponseBase


class BanCount(BaseModel):
    banned_host: str
    blocked_instances: int = 0
    blocked_population: int = 0
    keywords: Dict[str, int] = {}

    class Config:
        orm_mode = True


class BanCountListResponse(ResponseBase):
    hosts: List[BanCount]

    class Config:
        orm_mode = True


class SubdomainCluster(BaseModel):
    host: str
    count: int


class SubdomainClusterList(ResponseBase):
    clusters: List[SubdomainCluster]

    class Config:
        orm_mode = True
