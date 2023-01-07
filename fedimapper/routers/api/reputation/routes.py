from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select

from fedimapper.models.ban import Ban
from fedimapper.models.instance import Instance
from fedimapper.routers.api.common.schemas.instances import InstanceList
from fedimapper.services.db import AsyncSession
from fedimapper.services.db_session import get_session_depends
from fedimapper.settings import settings

from .schemas.models import (
    BanCount,
    BanCountListResponse,
    SubdomainCluster,
    SubdomainClusterList,
)

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


@router.get("/subdomain_clusters", response_model=SubdomainClusterList)
async def get_subdomain_clusters(db: AsyncSession = Depends(get_session_depends)) -> SubdomainClusterList:

    subdomain_hosts_stmt = (
        select(Instance.base_domain, func.count(Instance.base_domain).label("count"))
        .group_by(Instance.base_domain)
        .order_by(desc("count"))
        .having(func.count(Instance.base_domain) > 1)
        .limit(500)
    )
    subdomain_hosts_rows = (await db.execute(subdomain_hosts_stmt)).all()

    clusters = [SubdomainCluster(host=row.base_domain, count=row.count) for row in subdomain_hosts_rows]
    return SubdomainClusterList(clusters=clusters)


@router.get("/subdomain_clusters/{cluster_domain}", response_model=InstanceList)
async def get_subdomain_cluster_instances(
    cluster_domain: str, db: AsyncSession = Depends(get_session_depends)
) -> InstanceList:
    hosts_stmt = select(Instance.host).where(Instance.base_domain == cluster_domain).order_by(Instance.host)
    hosts_rows = (await db.execute(hosts_stmt)).all()
    hosts = [row.host for row in hosts_rows]
    return InstanceList(instances=hosts)
