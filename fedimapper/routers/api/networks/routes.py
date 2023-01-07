import datetime
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select

from fedimapper.models.asn import ASN
from fedimapper.models.instance import Instance
from fedimapper.routers.api.common.schemas.instances import InstanceList
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends
from fedimapper.settings import UNREADABLE_STATUSES

from .schemas.models import ASN as ASNResponse
from .schemas.models import NetworkList, NetworkStats

router = APIRouter()


async def get_all_asns(db: AsyncSession) -> Dict[str, ASN]:
    asn_map = {}
    known_network_stmt = select(ASN)
    known_rows = await db.execute(known_network_stmt)

    for row in known_rows.scalars().all():
        asn_map[row.asn] = row
    return asn_map


@router.get("/", response_model=NetworkList)
async def get_network_stats(db: AsyncSession = Depends(get_session_depends)) -> NetworkList:
    asn_map = await get_all_asns(db)
    active_window = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    known_network_stmt = (
        select(
            Instance.asn,
            func.count(Instance.asn).label("installs"),
            func.sum(Instance.current_user_count).label("users"),
        )
        .where(Instance.last_ingest_success >= active_window)
        .group_by(Instance.asn)
        .order_by(desc("installs"))
    )

    known_rows = await db.execute(known_network_stmt)
    networks = {}
    for row in known_rows:
        network = NetworkStats.from_orm(row)
        arn_record = asn_map.get(row.asn, None)
        if network:
            network.owner = arn_record.owner
            network.cc = arn_record.cc
            network.prefix = arn_record.prefix
        networks[f"ASN-{row.asn}"] = network
    return NetworkList(network=networks)


@router.get("/asn/{asn}", response_model=ASNResponse)
async def get_network_instances(asn: str, db: AsyncSession = Depends(get_session_depends)) -> ASNResponse:
    asn_object = await db.get(ASN, asn)
    hosts_stmt = select(Instance.host).where(Instance.asn == asn).order_by(Instance.host)
    hosts_rows = (await db.execute(hosts_stmt)).all()
    hosts = [row.host for row in hosts_rows]
    return ASNResponse(owner=asn_object.owner, instances=hosts)
