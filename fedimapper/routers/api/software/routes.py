from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select

from fedimapper.models.instance import Instance
from fedimapper.services.db import AsyncSession, get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES

from .schemas.models import SoftwareList, SoftwareStats

router = APIRouter()


@router.get("/", response_model=SoftwareList)
async def get_software_stats(db: AsyncSession = Depends(get_session_depends)) -> SoftwareList:
    known_software_stmt = (
        select(
            Instance.software,
            func.count(Instance.software).label("installs"),
            func.sum(Instance.current_user_count).label("users"),
        )
        .where(Instance.last_ingest_status.not_in(UNREADABLE_STATUSES))
        .group_by(Instance.software)
        .order_by(desc("installs"))
    )

    known_rows = await db.execute(known_software_stmt)
    software = {row.software: SoftwareStats.from_orm(row) for row in known_rows if row.installs > 15}

    unknown_service_stmt = select(
        func.count().label("installs"),
        func.sum(Instance.current_user_count).label("users"),
    ).where(Instance.last_ingest_status == "unknown_service")

    unknown_rows = [x for x in await db.execute(unknown_service_stmt)]
    software["unknown"] = SoftwareStats(installs=unknown_rows[0].installs, users=None)

    software = dict(sorted(software.items(), key=lambda item: item[1].installs, reverse=True))
    return SoftwareList(software=software)
