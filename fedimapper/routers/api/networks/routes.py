import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select

from fedimapper.models.asn import ASN
from fedimapper.models.instance import Instance
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends

from .schemas.models import ISP, ASNResponse, NetworkList, NetworkStats

router = APIRouter()


async def get_all_asns(db: AsyncSession) -> Dict[str, ASN]:
    asn_map = {}
    known_network_stmt = select(ASN)
    known_rows = await db.execute(known_network_stmt)

    for row in known_rows.scalars().all():
        asn_map[row.asn] = row
    return asn_map


async def get_asn_response(asn: str, db: AsyncSession):
    asn_object = await db.get(ASN, asn)
    hosts_stmt = select(Instance.host).where(Instance.asn == asn).order_by(Instance.host)
    hosts_rows = (await db.execute(hosts_stmt)).all()
    hosts = [row.host for row in hosts_rows]
    return ASNResponse(company=asn_object.company, asn=asn_object.asn, instances=hosts)


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
        if arn_record:
            network.company = arn_record.company
            network.cc = arn_record.cc
            network.company = arn_record.company
            network.prefix = arn_record.prefix
        networks[f"ASN-{row.asn}"] = network
    return NetworkList(network=networks)


@router.get("/asn/{asn}", response_model=ASNResponse)
async def get_network_instances(asn: str, db: AsyncSession = Depends(get_session_depends)) -> ASNResponse:
    return await get_asn_response(asn, db)


@router.get("/company/{company}", response_model=ISP)
async def get_company_networks(company: str, db: AsyncSession = Depends(get_session_depends)) -> ISP:
    asn_stmt = select(ASN).where(func.lower(ASN.company) == company.lower())
    asn_rows = (await db.execute(asn_stmt)).scalars().all()
    if len(asn_rows) == 0:
        raise HTTPException(404)

    asn_response_list = []
    for asn in asn_rows:
        asn_response_list.append(await get_asn_response(asn.asn, db))

    return ISP(networks=asn_response_list)
