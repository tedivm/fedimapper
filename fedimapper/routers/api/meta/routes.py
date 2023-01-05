import datetime
from logging import getLogger

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select

from fedimapper.models.instance import Instance
from fedimapper.run import get_stale, get_unreachable
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES, settings

from .schemas.models import MetaData

router = APIRouter()
logger = getLogger(__name__)


async def get_oldest_stale_lag(db: AsyncSession = Depends(get_session_depends)):
    try:
        oldest_stale = (await get_stale(db, 1)).first()[0]
        if oldest_stale:
            stale_window = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.stale_rescan_hours)
            return (stale_window - oldest_stale.last_ingest).total_seconds()
    except:
        return 0


async def get_oldest_unreachable_lag(db: AsyncSession = Depends(get_session_depends)):
    try:
        oldest_unreachable = (await get_unreachable(db, 1)).first()[0]
        if oldest_unreachable:
            unreachable_window = datetime.datetime.utcnow() - datetime.timedelta(
                hours=settings.unreachable_rescan_hours
            )
            return (unreachable_window - oldest_unreachable.last_ingest).total_seconds()
    except:
        return 0


async def get_last_ingest(db: AsyncSession = Depends(get_session_depends)):
    select_stmt = (
        select(Instance).where(and_(Instance.last_ingest != None)).order_by(Instance.last_ingest.desc()).limit(1)
    )
    try:
        return (await db.execute(select_stmt)).first()[0].last_ingest
    except:
        return None


async def get_unscanned_count(db: AsyncSession = Depends(get_session_depends)):
    select_stmt = select(func.count("*").label("count")).select_from(Instance).where(Instance.last_ingest == None)
    return (await db.execute(select_stmt)).first()[0]


async def get_scanned_count(db: AsyncSession = Depends(get_session_depends)):
    select_stmt = select(func.count("*").label("count")).select_from(Instance).where(Instance.last_ingest != None)
    return (await db.execute(select_stmt)).first()[0]


async def get_sps(db: AsyncSession = Depends(get_session_depends)):
    seconds_to_scan = 60
    sps_scan = datetime.datetime.utcnow() - datetime.timedelta(seconds=seconds_to_scan)
    select_stmt = select(func.count("*").label("count")).where(
        and_(Instance.last_ingest != None, Instance.last_ingest >= sps_scan)
    )

    try:
        return (await db.execute(select_stmt)).first()[0] / seconds_to_scan
    except:
        return 0


@router.get("/", response_model=MetaData)
async def get_meta(db: AsyncSession = Depends(get_session_depends)) -> MetaData:
    return MetaData(
        queue_lag_stale=await get_oldest_stale_lag(db),
        queue_lag_unreachable=await get_oldest_unreachable_lag(db),
        unscanned=await get_unscanned_count(db),
        scanned=await get_scanned_count(db),
        last_ingest=await get_last_ingest(db),
        sps=await get_sps(db),
    )
