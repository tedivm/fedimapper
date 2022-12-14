import datetime
from logging import getLogger
from typing import Any, Dict, cast
from uuid import uuid4

import httpx
from sqlalchemy import and_, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from fedimapper.models.ban import Ban
from fedimapper.models.instance import Instance, InstanceStats
from fedimapper.services import db, mastodon
from fedimapper.services.nodeinfo import NodeInfoInstance, NodeInfoUsers
from fedimapper.services.stopwords import get_key_words
from fedimapper.settings import settings
from fedimapper.tasks.ingesters import utils

logger = getLogger(__name__)


async def save(session: Session, instance: Instance, nodeinfo: NodeInfoInstance | None) -> bool:
    if not await save_mastodon_metadata(session, instance, nodeinfo):
        return False

    logger.info(f"Host identified as mastodon compatible: {instance.host}")
    await save_mastodon_blocked_instances(session, instance)

    if await utils.should_save_peers(instance):
        await save_mastodon_peered_instance(session, instance)

    return True


async def save_mastodon_metadata(session: Session, instance: Instance, nodeinfo: NodeInfoInstance | None) -> bool:

    try:
        metadata = mastodon.get_metadata(instance.www_host)
    except httpx.TransportError as exc:
        instance.last_ingest_status = "unreachable"
        logger.info(f"Unable to reach host {instance.host} as {instance.www_host}")
        await session.commit()
        return False
    except:
        logger.debug(f"Host is not Mastodon Compatible: {instance.host}")
        return False

    instance.title = metadata.get("title", None)
    instance.short_description = metadata.get("short_description", None)
    instance.email = metadata.get("email", None)

    if nodeinfo:
        instance.version = nodeinfo.software.version
        instance.software_version = nodeinfo.software.version
        instance.software = nodeinfo.software.name

    version_string = metadata.get("version", None)
    if version_string:
        instance.version = version_string
        version_breakdown = mastodon.get_version_breakdown(version_string)
        if version_breakdown:
            instance.mastodon_version = version_breakdown.mastodon_version
            if not nodeinfo:
                instance.software = version_breakdown.software
                instance.software_version = version_breakdown.software_version

    nodeinfo_total_users = None
    nodeinfo_monthly_users = None
    nodeinfo_local_posts = None
    if nodeinfo:
        nodeinfo_total_users = nodeinfo.usage.users.total
        nodeinfo_monthly_users = nodeinfo.usage.users.activeMonth
        nodeinfo_local_posts = nodeinfo.usage.localPosts

    instance.current_user_count = metadata.get("stats", {}).get("user_count", nodeinfo_total_users)
    instance.current_status_count = metadata.get("stats", {}).get("status_count", nodeinfo_local_posts)
    instance.current_domain_count = metadata.get("stats", {}).get("domain_count", None)
    instance.thumbnail = metadata.get("thumbnail", None)

    reg_open = metadata.get("registrations", None)
    if reg_open != None:
        instance.registration_open = bool(reg_open)
    instance.approval_required = metadata.get("approval_required", None)

    instance_stats = InstanceStats(
        host=instance.host,
        user_count=instance.current_user_count,
        active_monthly_users=nodeinfo_monthly_users,
        status_count=instance.current_status_count,
        domain_count=instance.current_domain_count,
    )
    session.add(instance_stats)
    await session.commit()
    return True


async def save_mastodon_blocked_instances(session: Session, instance: Instance):
    try:
        ingest_id = str(uuid4())
        # Will throw exceptions when the ban list isn't public.
        banned = mastodon.get_blocked_instances(instance.www_host)
        instance.has_public_bans = True

        local_evils = set(settings.evil_domains) | await utils.get_spammers_from_list([x["domain"] for x in banned])

        ban_values = [
            {
                "host": instance.host,
                "banned_host": banned_host["domain"],
                "digest": banned_host["digest"],
                "ingest_id": ingest_id,
                "severity": banned_host["severity"],
                "comment": banned_host["comment"],
                # Servers in theory advertise a language, but they're mostly set to the default
                # of english regardless of what language the users and admins actually use.
                "keywords": list(get_key_words("en", banned_host["comment"])),
            }
            for banned_host in banned
            if banned_host and len([suffix for suffix in local_evils if banned_host["domain"].endswith(suffix)]) == 0
        ]

        if len(ban_values) > 0:
            ban_insert_stmt = insert(Ban)
            ban_update_statement = ban_insert_stmt.on_conflict_do_update(
                index_elements=["host", "banned_host"],
                set_=dict(
                    severity=ban_insert_stmt.excluded.severity,
                    comment=ban_insert_stmt.excluded.comment,
                    keywords=ban_insert_stmt.excluded.keywords,
                    ingest_id=ban_insert_stmt.excluded.ingest_id,
                ),
            )
            ban_values.sort(key=lambda x: x["banned_host"])
            await db.buffer_inserts(session, ban_update_statement, ban_values)

        ban_delete_stmt = delete(Ban).where(and_(Ban.host == instance.host, Ban.ingest_id != ingest_id))
        await session.execute(ban_delete_stmt)
        await session.commit()

    except:
        instance.has_public_bans = False
        ban_delete_stmt = delete(Ban).where(and_(Ban.host == instance.host))
        await session.execute(ban_delete_stmt)
        await session.commit()
        logger.debug(f"Unable to get instance ban data for {instance.host}")


async def save_mastodon_peered_instance(session: Session, instance: Instance):
    logger.info(f"Attempting to save peers: {instance.host}")
    try:
        # Will throw exceptions when the peer list isn't public.
        peers = mastodon.get_peers(instance.www_host)
        instance.has_public_peers = True
        instance.last_ingest_peers = datetime.datetime.utcnow()
        await session.commit()
        await utils.save_peers(session, instance.host, peers)
    except:
        instance.last_ingest_peers = datetime.datetime.utcnow()
        instance.has_public_peers = False
        await session.commit()
        logger.debug(f"Unable to get instance peer data for {instance.host} as {instance.www_host}")
