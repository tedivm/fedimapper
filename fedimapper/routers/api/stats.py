from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select

from fedimapper.models.instance import Instance
from fedimapper.services.db import AsyncSession, get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES

router = APIRouter()

# Software
@router.get("/")
async def get_software_stats(db: AsyncSession = Depends(get_session_depends)):
    known_software_stmt = (
        select(Instance.software, func.count(Instance.software).label("installs"))
        .where(Instance.last_ingest_status.not_in(UNREADABLE_STATUSES))
        .group_by(Instance.software)
        .order_by(desc("installs"))
    )

    known_rows = await db.execute(known_software_stmt)
    results = {row.software: row.installs for row in known_rows if row.installs > 15}

    unknown_service_stmt = select(func.count().label("installs")).where(
        Instance.last_ingest_status == "unknown_service"
    )

    unknown_rows = [x for x in await db.execute(unknown_service_stmt)]
    results["unknown"] = unknown_rows[0].installs

    results = dict(sorted(results.items(), key=lambda item: item[1], reverse=True))
    return results
