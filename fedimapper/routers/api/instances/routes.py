from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select

from fedimapper.models.ban import Ban
from fedimapper.models.instance import Instance
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES
from fedimapper.utils.banstats import get_ban_keywords

from .schemas.models import (
    InstanceBan,
    InstanceBanListResponse,
    InstanceModeration,
    InstanceResponse,
)

router = APIRouter()

from logging import getLogger

logger = getLogger(__name__)


@router.get("/{host}", response_model=InstanceResponse)
async def get_instance(host: str, db: AsyncSession = Depends(get_session_depends)) -> InstanceResponse:
    instance = await db.get(Instance, host)
    if not instance:
        raise HTTPException(404)
    response = InstanceResponse.from_orm(instance)
    reputation_block = InstanceModeration(
        all_keywords=await get_ban_keywords(db, host),
        block_keywords=await get_ban_keywords(db, host, "suspended"),
        silence_keywords=await get_ban_keywords(db, host, "silenced"),
    )
    response.reputation = reputation_block
    return response


@router.get("/{host}/banned_from", response_model=InstanceBanListResponse)
async def get_instance_banned_from(
    host: str, db: AsyncSession = Depends(get_session_depends)
) -> InstanceBanListResponse:
    banned_hosts_stmt = select(Ban).where(Ban.banned_host == host)
    banned_hosts_rows = (await db.execute(banned_hosts_stmt)).all()
    bans = [InstanceBan.from_orm(row[0]) for row in banned_hosts_rows]
    return InstanceBanListResponse(bans=bans)


@router.get("/{host}/bans", response_model=InstanceBanListResponse)
async def get_instance_bans(host: str, db: AsyncSession = Depends(get_session_depends)) -> InstanceBanListResponse:
    banned_hosts_stmt = select(Ban).where(Ban.host == host)
    banned_hosts_rows = (await db.execute(banned_hosts_stmt)).all()
    bans = [InstanceBan.from_orm(row[0]) for row in banned_hosts_rows]
    return InstanceBanListResponse(bans=bans)
