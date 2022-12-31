import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select

from fedimapper.models.instance import Instance
from fedimapper.run import get_stale, get_unreachable
from fedimapper.services.db import AsyncSession, get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES, settings

from .schemas.models import MetaData

router = APIRouter()


@router.get("/", response_model=MetaData)
async def get_meta(db: AsyncSession = Depends(get_session_depends)) -> MetaData:

    queue_lag_stale = 0
    oldest_stale = (await get_stale(db, 1)).first()[0]
    if oldest_stale:
        stale_window = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.stale_rescan_hours)
        queue_lag_stale = (stale_window - oldest_stale.last_ingest).total_seconds()

    queue_lag_unreachable = 0
    oldest_unreachable = (await get_unreachable(db, 1)).first()[0]
    if oldest_unreachable:
        unreachable_window = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.unreachable_rescan_hours)
        queue_lag_unreachable = (unreachable_window - oldest_unreachable.last_ingest).total_seconds()

    select_stmt = (
        select(Instance).where(and_(Instance.last_ingest != None)).order_by(Instance.last_ingest.desc()).limit(1)
    )
    try:
        last_ingest = (await db.execute(select_stmt)).first()[0].last_ingest
    except:
        last_ingest = None

    seconds_to_scan = 60
    sps_scan = datetime.datetime.utcnow() - datetime.timedelta(seconds=seconds_to_scan)
    select_stmt = select(func.count("*").label("count")).where(
        and_(Instance.last_ingest != None, Instance.last_ingest >= sps_scan)
    )

    try:
        sps = (await db.execute(select_stmt)).first()[0] / seconds_to_scan
    except:
        sps = 0

    return MetaData(
        queue_lag_stale=queue_lag_stale,
        queue_lag_unreachable=queue_lag_unreachable,
        last_ingest=last_ingest,
        sps=sps,
    )
