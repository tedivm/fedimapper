from logging import getLogger
from typing import Any, Dict

import httpx
from sqlalchemy.orm import Session

from fedimapper.models.instance import Instance
from fedimapper.services import peertube
from fedimapper.services.nodeinfo import NodeInfoInstance
from fedimapper.tasks.ingesters import utils
from fedimapper.tasks.ingesters.nodeinfo import save_nodeinfo_stats

logger = getLogger(__name__)


async def save(session: Session, instance: Instance, nodeinfo: NodeInfoInstance | None) -> bool:

    # The next most common set of services that don't support the above APIs
    # is PeerTube.
    if not await save_peertube_metadata(session, instance, nodeinfo):
        return False

    if nodeinfo:
        await save_nodeinfo_stats(session, instance, nodeinfo)

    logger.info(f"Host identified as peertube compatible: {instance.host}")
    await save_peertube_peered_instance(session, instance)

    # PeerTube doesn't support public ban lists at all.
    instance.has_public_bans = False
    await session.commit()
    return True


async def save_peertube_metadata(session: Session, instance: Instance, nodeinfo: NodeInfoInstance | None) -> bool:

    try:
        metadata = peertube.get_metadata(instance.host)
    except httpx.TransportError as exc:
        instance.last_ingest_status = "unreachable"
        logger.info(f"Unable to reach host {instance.host}")
        await session.commit()
        return False
    except:
        logger.debug(f"Host is not Peertube Compatible: {instance.host}")
        return False

    instance.software = "peertube"

    instance_config = metadata.get("instance", {})
    instance.title = instance_config.get("name", None)
    instance.short_description = instance_config.get("shortDescription", None)

    instance_signup = metadata.get("signup", {})
    instance.registration_open = instance_signup.get("allowed", None)

    version = metadata.get("serverVersion", None)
    instance.version = version
    instance.software_version = version

    try:
        user_count = None
        status_count = None

        if nodeinfo:
            nodeinfo.usage.localPosts
            user_count = nodeinfo.usage.users.total
            status_count = nodeinfo.usage.localPosts

        if user_count and status_count:
            instance.user_count = user_count
            instance.status_count = status_count
        else:
            stats = peertube.get_stats(instance.host)
            instance.user_count = stats.get("totalUsers", None)
            instance.status_count = stats.get("totalVideos", None)
    except httpx.TransportError as exc:
        pass

    try:
        about = peertube.get_about(instance.host)
        instance.email = about.get("admin", {}).get("email", None)
    except httpx.TransportError as exc:
        pass

    await session.commit()
    return True


async def save_peertube_peered_instance(session: Session, instance: Instance) -> bool:
    try:
        # Will throw exceptions when the peer list isn't public.
        peers_full = peertube.get_peers(instance.host)
        instance.domain_count = peers_full.get("total", None)
        instance.has_public_peers = True
        await session.commit()
        peers = set([x["follower"]["host"] for x in peers_full.get("data", [])])
        await utils.save_peers(session, instance.host, peers)
        return True
    except:
        instance.has_public_peers = False
        await session.commit()
        logger.exception(f"Unable to get instance peer data for {instance.host}")
        return False
