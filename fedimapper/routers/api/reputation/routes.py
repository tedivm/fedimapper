from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select

from fedimapper.models.ban import Ban
from fedimapper.models.instance import Instance
from fedimapper.services.db import AsyncSession, get_session_depends
from fedimapper.settings import settings

from .schemas.models import BanCount, BanCountListResponse

router = APIRouter()

from logging import getLogger

logger = getLogger(__name__)


@router.get("/bans", response_model=BanCountListResponse)
async def get_bans_ranked(db: AsyncSession = Depends(get_session_depends)) -> BanCountListResponse:
    banned_hosts_stmt = (
        select(
            Ban.banned_host,
            func.count(Ban.banned_host).label("blocked_instances"),
            func.sum(Instance.current_user_count).label("blocked_population"),
        )
        .join(Instance, Instance.host == Ban.host)
        .group_by(Ban.banned_host)
        .order_by(desc("blocked_population"))
        .having(func.count(Ban.banned_host) >= settings.top_lists_min_threshold)
    )
    banned_hosts_rows = (await db.execute(banned_hosts_stmt)).all()
    bans = [BanCount.from_orm(row) for row in banned_hosts_rows]
    return BanCountListResponse(hosts=bans)


@router.get("/bans/silenced", response_model=BanCountListResponse)
async def get_bans_silenced_ranked(db: AsyncSession = Depends(get_session_depends)) -> BanCountListResponse:
    banned_hosts_stmt = (
        select(
            Ban.banned_host,
            func.count(Ban.banned_host).label("blocked_instances"),
            func.sum(Instance.current_user_count).label("blocked_population"),
        )
        .join(Instance, Instance.host == Ban.host)
        .where(Ban.severity == "silence")
        .group_by(Ban.banned_host)
        .order_by(desc("blocked_population"))
        .having(func.count(Ban.banned_host) >= settings.top_lists_min_threshold)
    )
    banned_hosts_rows = (await db.execute(banned_hosts_stmt)).all()
    bans = [BanCount.from_orm(row) for row in banned_hosts_rows]
    return BanCountListResponse(hosts=bans)


@router.get("/bans/suspended", response_model=BanCountListResponse)
async def get_bans_suspended_ranked(db: AsyncSession = Depends(get_session_depends)) -> BanCountListResponse:
    banned_hosts_stmt = (
        select(
            Ban.banned_host,
            func.count(Ban.banned_host).label("blocked_instances"),
            func.sum(Instance.current_user_count).label("blocked_population"),
        )
        .join(Instance, Instance.host == Ban.host)
        .where(Ban.severity == "suspend")
        .group_by(Ban.banned_host)
        .order_by(desc("blocked_population"))
        .having(func.count(Ban.banned_host) >= settings.top_lists_min_threshold)
    )
    banned_hosts_rows = (await db.execute(banned_hosts_stmt)).all()
    bans = [BanCount.from_orm(row) for row in banned_hosts_rows]
    return BanCountListResponse(hosts=bans)
