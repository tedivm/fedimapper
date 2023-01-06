from logging import getLogger
from typing import Any, Dict, cast

from sqlalchemy.orm import Session

from fedimapper.models.instance import Instance, InstanceStats
from fedimapper.services.nodeinfo import NodeInfoInstance, NodeInfoUsers

logger = getLogger(__name__)


async def save(session: Session, instance: Instance, nodeinfo: NodeInfoInstance | None) -> bool:
    if not nodeinfo:
        return False

    logger.info(f"Host identified as nodeinfo compatible: {instance.host}")

    instance.software = nodeinfo.software.name

    instance.software_version = nodeinfo.software.version
    instance.version = nodeinfo.software.version

    instance.has_public_bans = False
    instance.has_public_peers = False

    await session.commit()

    await save_nodeinfo_stats(session, instance, nodeinfo)
    return True


async def save_nodeinfo_stats(session: Session, instance: Instance, nodeinfo: NodeInfoInstance) -> bool:

    if "nodeName" in nodeinfo.metadata:
        instance.title = nodeinfo.metadata["nodeName"]
        await session.commit()

    if nodeinfo.usage.users.total and nodeinfo.usage.users.total < 1250000:
        instance.current_user_count = nodeinfo.usage.users.total
    else:
        instance.current_user_count = None

    if nodeinfo.usage.localPosts and nodeinfo.usage.localPosts < 1000000000:
        instance.current_status_count = nodeinfo.usage.localPosts
    else:
        instance.current_status_count = None

    active_monthly = None
    if nodeinfo.usage.users.activeMonth and nodeinfo.usage.users.activeMonth < 1250000:
        active_monthly = nodeinfo.usage.users.activeMonth

    instance_stats = InstanceStats(
        host=instance.host,
        user_count=instance.current_user_count,
        active_monthly_users=active_monthly,
        status_count=instance.current_status_count,
        domain_count=None,
    )
    session.add(instance_stats)
    await session.commit()
    return True
