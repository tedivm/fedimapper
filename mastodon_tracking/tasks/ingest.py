import datetime
from logging import getLogger
from typing import List
from uuid import UUID, uuid4

import httpx
from mastodon_tracking.models.peer import Peer
from sqlalchemy import and_, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from tld import get_tld

from ..models.ban import Ban
from ..models.evil import Evil
from ..models.instance import Instance
from ..services import db, mastodon
from ..settings import settings

logger = getLogger(__name__)


async def ingest_host(host: str) -> None:
    logger.info(f"Ingesting from {host}")

    for suffix in settings.evil_domains:
        if host.endswith(suffix):
            logger.info(f"Skipping ingest from {host} for matching evil pattern: {suffix}")
            return

    async with db.get_session() as session:

        instance = await save_metadata(session, host)
        if not instance:
            return

        await save_blocked_instances(session, instance)
        await save_peered_instance(session, instance)

        instance.last_ingest_status = "success"
        await session.commit()
        logger.info(f"Finished processing {host}")


async def save_metadata(session: Session, host: str) -> Instance | None:

    instance = await get_or_save_host(session, host)
    instance.last_ingest = datetime.datetime.utcnow()

    try:
        metadata = mastodon.get_metadata(host)
    except httpx.TransportError as exc:
        instance.last_ingest_status = "unreachable"
        logger.error(f"Unable to reach host {host}")
        await session.commit()
        return
    except:
        instance.last_ingest_status = "no_meta"
        logger.error(f"Unable to get Metadata for {host}")
        await session.commit()
        return

    instance.title = metadata.get("title", None)
    instance.short_description = metadata.get("short_description", None)
    instance.email = metadata.get("email", None)
    instance.version = metadata.get("version", None)

    instance.user_count = metadata.get("stats", {}).get("user_count", None)
    instance.status_count = metadata.get("stats", {}).get("status_count", None)
    instance.domain_count = metadata.get("stats", {}).get("domain_count", None)

    instance.thumbnail = metadata.get("thumbnail", None)

    reg_open = metadata.get("registrations", None)
    if reg_open != None:
        instance.registration_open = bool(reg_open)
    instance.approval_required = metadata.get("approval_required", None)
    await session.commit()
    return instance


async def save_blocked_instances(session: Session, instance: Instance):
    try:
        ingest_id = str(uuid4())
        # Will throw exceptions when the ban list isn't public.
        banned = mastodon.get_blocked_instances(instance.host)
        instance.has_public_bans = True

        local_evils = set(settings.evil_domains) | await get_spammers_from_list([x["domain"] for x in banned])

        ban_values = [
            {
                "host": instance.host,
                "banned_host": banned_host["domain"],
                "ingest_id": ingest_id,
                "severity": banned_host["severity"],
                "comment": banned_host["comment"],
            }
            for banned_host in banned
            if banned_host and len([suffix for suffix in local_evils if banned_host["domain"].endswith(suffix)]) == 0
        ]
        if len(ban_values) > 0:
            ban_insert_stmt = insert(Ban).values(ban_values)
            ban_update_statement = ban_insert_stmt.on_conflict_do_update(
                index_elements=["host", "banned_host"],
                set_=dict(severity=ban_insert_stmt.excluded.severity, comment=ban_insert_stmt.excluded.comment),
            )
            await session.execute(ban_update_statement)

        ban_delete_stmt = delete(Ban).where(and_(Ban.host == instance.host, Ban.ingest_id != ingest_id))
        await session.execute(ban_delete_stmt)
        await session.commit()
    except:
        instance.has_public_bans = False
        logger.error(f"Unable to get instance ban data for {instance.host}")


async def save_peered_instance(session: Session, instance: Instance):
    try:
        ingest_id = str(uuid4())
        # Will throw exceptions when the peer list isn't public.
        peers = mastodon.get_peers(instance.host)
        instance.has_public_peers = True
        local_evils = set(settings.evil_domains) | await get_spammers_from_list(peers)
        insert_peer_values = [
            {
                "host": instance.host,
                "peer_host": peer_host,
                "ingest_id": ingest_id,
            }
            for peer_host in peers
            if peer_host and len([suffix for suffix in local_evils if peer_host.endswith(suffix)]) == 0
        ]

        if len(insert_peer_values) > 0:
            # Add Peers to Instances for future processing.
            insert_instance_values = [{"host": peer_host["peer_host"]} for peer_host in insert_peer_values]
            insert_instance_stmt = (
                insert(Instance).values(insert_instance_values).on_conflict_do_nothing(index_elements=["host"])
            )
            await session.execute(insert_instance_stmt)
            await session.commit()

            # Save Peer Relationship
            insert_peer_stmt = (
                insert(Peer).values(insert_peer_values).on_conflict_do_nothing(index_elements=["host", "peer_host"])
            )
            await session.execute(insert_peer_stmt)

        # Delete old relationships that weren't in this ingest.
        peer_delete_stmt = delete(Peer).where(and_(Peer.host == instance.host, Peer.ingest_id != ingest_id))
        await session.execute(peer_delete_stmt)
        await session.commit()

    except:
        instance.has_public_peers = False
        logger.error(f"Unable to get instance peer data for {instance.host}")


async def save_evil_domains(session: Session, domains):
    if len(domains) <= 0:
        return
    evil_values = [{"domain": x} for x in domains]
    print(evil_values)
    evil_insert_stmt = insert(Evil).values(evil_values)
    evil_update_statement = evil_insert_stmt.on_conflict_do_nothing(index_elements=["domain"])
    await session.execute(evil_update_statement)
    await session.commit()


async def get_or_save_host(db: Session, host) -> Instance:
    instance = await db.get(Instance, host)
    if instance:
        return instance
    instance = Instance(host=host)
    db.add(instance)
    await db.commit()
    return instance


async def get_spammers_from_list(hosts: List[str]):
    domain_count = {}
    for host in hosts:
        res = get_tld(host, as_object=True, fail_silently=True)
        if not res:
            continue
        if not res.fld in domain_count:
            domain_count[res.fld] = 1
        else:
            domain_count[res.fld] += 1
    return set([domain for domain, count in domain_count.items() if count >= settings.spam_domain_threshold])
