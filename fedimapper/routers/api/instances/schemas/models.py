from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel

from fedimapper.routers.api.common.schemas.base import ResponseBase


class InstanceResponse(ResponseBase):
    host: str
    last_ingest: datetime
    last_ingest_status: str

    title: str | None
    short_description: str | None
    email: str | None
    version: str | None

    software: str | None
    mastodon_version: str | None
    software_version: str | None

    current_user_count: int | None
    current_status_count: int | None
    current_domain_count: int | None

    registration_open: bool | None
    approval_required: bool | None


class InstanceBan(BaseModel):
    host: str
    banned_host: str
    digest: str | None
    severity: str
    comment: str | None
    keywords: List[str] | None

    class Config:
        orm_mode = True


class InstanceBanListResponse(ResponseBase):
    bans: List[InstanceBan]
