from logging import getLogger
from typing import Any, Dict

from sqlalchemy.orm import Session

from fedimapper.models.instance import Instance, InstanceStats

logger = getLogger(__name__)


async def save(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:
    if not nodeinfo:
        nodeinfo = {}

    logger.info(f"Host identified as nodeinfo compatible: {instance.host}")

    software_name = nodeinfo.get("software", {}).get("name", None)
    if software_name:
        instance.software = software_name.lower()

    instance.software_version = nodeinfo.get("software", {}).get("version", None)
    instance.version = nodeinfo.get("software", {}).get("version", None)

    instance.has_public_bans = False
    instance.has_public_peers = False

    await session.commit()

    await save_nodeinfo_stats(session, instance, nodeinfo)
    return True


async def save_nodeinfo_stats(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:

    node_meta = nodeinfo.get("meta", {})
    if "nodeName" in node_meta:
        instance.title = node_meta["nodeName"]
        await session.commit()

    nodeinfo_usage = nodeinfo.get("usage", None)
    if not nodeinfo_usage:
        return False

    user_piece = nodeinfo_usage.get("users", {}).get("total", None)
    user_count = None
    if user_piece:
        if isinstance(user_piece, dict):
            user_count = user_piece.get("total", None)
        else:
            try:
                user_count = int(user_piece)
            except:
                pass

    if user_count and user_count < 1250000:
        instance.current_user_count = user_count
    else:
        instance.current_user_count = None

    local_posts = nodeinfo_usage.get("localPosts", None)
    if local_posts and local_posts < 1000000000:
        instance.current_status_count = local_posts
    else:
        instance.current_status_count = None

    active_monthly = nodeinfo_usage.get("users", {}).get("activeMonth", None)
    if active_monthly and active_monthly > 1250000:
        active_monthly = None

    instance_stats = InstanceStats(
        host=instance.host,
        user_count=user_count,
        active_monthly_users=active_monthly,
        status_count=instance.current_status_count,
        domain_count=None,
    )
    session.add(instance_stats)
    await session.commit()
    return True
