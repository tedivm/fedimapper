import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select

from fedimapper.models.instance import Instance
from fedimapper.routers.api.common.schemas.instances import InstanceList
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES

from .schemas.models import SoftwareList, SoftwareStats

router = APIRouter()


@router.get("/", response_model=SoftwareList)
async def get_software_stats(db: AsyncSession = Depends(get_session_depends)) -> SoftwareList:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    known_software_stmt = (
        select(
            Instance.software,
            func.count(Instance.software).label("installs"),
            func.sum(Instance.current_user_count).label("users"),
        )
        .where(Instance.last_ingest_success >= active_window)
        .group_by(Instance.software)
        .order_by(desc("installs"))
    )

    known_rows = await db.execute(known_software_stmt)
    software = {row.software: SoftwareStats.from_orm(row) for row in known_rows if row.installs > 15}

    unknown_service_stmt = select(
        func.count().label("installs"),
        func.sum(Instance.current_user_count).label("users"),
    ).where(and_(Instance.last_ingest_status == "unknown_service", Instance.last_ingest >= active_window))

    unknown_rows = [x for x in await db.execute(unknown_service_stmt)]
    software["unknown"] = SoftwareStats(installs=unknown_rows[0].installs, users=None)

    software = dict(sorted(software.items(), key=lambda item: item[1].installs, reverse=True))
    return SoftwareList(software=software)


@router.get("/{software}", response_model=InstanceList)
async def get_software_instances(software: str, db: AsyncSession = Depends(get_session_depends)) -> InstanceList:
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    if software == "unknown":
        hosts_stmt = (
            select(Instance.host)
            .where(and_(Instance.last_ingest_status == "unknown_service", Instance.last_ingest >= active_window))
            .order_by(Instance.host)
        )
    else:
        hosts_stmt = (
            select(Instance.host)
            .where(and_(Instance.software == software, Instance.last_ingest_success >= active_window))
            .order_by(Instance.host)
        )
    hosts_rows = (await db.execute(hosts_stmt)).all()
    hosts = [row.host for row in hosts_rows]
    return InstanceList(instances=hosts)
