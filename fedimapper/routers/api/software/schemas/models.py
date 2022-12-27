from typing import Dict

from pydantic import BaseModel

from fedimapper.routers.api.common.schemas.base import ResponseBase


class SoftwareStats(BaseModel):
    installs: int
    users: int | None = 0

    class Config:
        orm_mode = True


class SoftwareList(ResponseBase):
    software: Dict[str, SoftwareStats]
