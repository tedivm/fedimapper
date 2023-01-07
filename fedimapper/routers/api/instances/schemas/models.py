from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, HttpUrl

from fedimapper.routers.api.common.schemas.base import ResponseBase


class InstanceResponse(ResponseBase):
    host: str
    www_host: str | None
    last_ingest: datetime | None
    last_ingest_status: str | None
    first_ingest_success: datetime | None

    title: str | None
    short_description: str | None
    email: str | None
    version: str | None

    current_user_count: int | None
    current_status_count: int | None
    current_domain_count: int | None

    thumbnail: HttpUrl | None

    registration_open: bool | None
    approval_required: bool | None

    has_public_bans: bool | None
    has_public_peers: bool | None

    software: str | None
    mastodon_version: str | None
    software_version: str | None

    asn: str | None


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
