import datetime
from logging import getLogger

from fastapi import APIRouter, Depends
from sqlalchemy import Column, and_, desc, distinct, func, select

from fedimapper.models.instance import Instance
from fedimapper.run import get_stale, get_unreachable
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES, settings

from .schemas.models import WorldData

router = APIRouter()
logger = getLogger(__name__)


async def get_distinct_count(db: AsyncSession, column: Column) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.count(distinct(column)).label("count"))
        .select_from(Instance)
        .where(Instance.last_ingest_success >= active_window)
    )
    return (await db.execute(select_stmt)).first()[0]


async def get_instance_column_count(db: AsyncSession, column: Column) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.count(column).label("count"))
        .select_from(Instance)
        .where(Instance.last_ingest_success >= active_window)
    )
    return (await db.execute(select_stmt)).first()[0]


async def get_instance_column_sum(db: AsyncSession, column: Column) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.sum(column).label("count"))
        .select_from(Instance)
        .where(Instance.last_ingest_success >= active_window)
    )
    return (await db.execute(select_stmt)).first()[0]


async def get_instance_count(db: AsyncSession) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.count("*").label("count"))
        .select_from(Instance)
        .where(Instance.last_ingest_success >= active_window)
    )
    return (await db.execute(select_stmt)).first()[0]


async def get_population(db: AsyncSession) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.sum(Instance.current_user_count).label("count"))
        .select_from(Instance)
        .where(Instance.last_ingest_success >= active_window)
    )
    return (await db.execute(select_stmt)).first()[0]


async def get_public_ban_population(db: AsyncSession) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.sum(Instance.current_user_count).label("count"))
        .select_from(Instance)
        .where(and_(Instance.last_ingest_success >= active_window, Instance.has_public_bans == True))
    )
    results = (await db.execute(select_stmt)).first()
    if not results[0]:
        return 0
    return results[0]


async def get_network_count(db: AsyncSession) -> int:
    return await get_distinct_count(db, Instance.asn)


async def get_software_count(db: AsyncSession) -> int:
    return await get_distinct_count(db, Instance.software)


async def get_public_ban_count(db: AsyncSession) -> int:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    select_stmt = (
        select(func.count("*").label("count"))
        .select_from(Instance)
        .where(and_(Instance.last_ingest_success >= active_window, Instance.has_public_bans == True))
    )
    results = (await db.execute(select_stmt)).first()
    if not results[0]:
        return 0
    return results[0]


async def get_mastodon_compatible_count(db: AsyncSession) -> int:
    return await get_instance_column_count(db, Instance.mastodon_version)


@router.get("/", response_model=WorldData)
async def get_world_statistics(db: AsyncSession = Depends(get_session_depends)) -> WorldData:

    return WorldData(
        total_population=await get_population(db),
        active_instances=await get_instance_count(db),
        networks=await get_network_count(db),
        software=await get_software_count(db),
        public_ban_lists=await get_public_ban_count(db),
        public_ban_population=await get_public_ban_population(db),
        mastodon_compatible_instances=await get_mastodon_compatible_count(db),
    )
