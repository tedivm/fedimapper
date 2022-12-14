import datetime
from logging import getLogger
from typing import List
from uuid import UUID, uuid4

import cymruwhois
import httpx
from sqlalchemy import and_, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from tld import get_tld

from ..models.asn import ASN
from ..models.ban import Ban
from ..models.evil import Evil
from ..models.instance import Instance
from ..models.peer import Peer
from ..services import db, mastodon, networking, peertube
from ..settings import settings

logger = getLogger(__name__)


async def ingest_host(host: str) -> None:
    logger.info(f"Ingesting from {host}")

    for suffix in settings.evil_domains:
        if host.endswith(suffix):
            logger.info(f"Skipping ingest from {host} for matching evil pattern: {suffix}")
            return

    async with db.get_session() as session:

        # This lookup can be slow as it hits an API, so do it before
        # there are any locks on the database.
        ip_address = networking.get_ip_from_url(host)

        # Now do database stuff.
        instance = await get_or_save_host(session, host)
        instance.last_ingest = datetime.datetime.utcnow()
        if not ip_address:
            logger.warning(f"No DNS for {host}")
            instance.last_ingest_status = "no_dns"
            await session.commit()
            return

        instance.ip_address = ip_address
        asn_info = networking.get_asn_data(ip_address)
        if asn_info:
            instance.asn = asn_info.asn
            await save_asn(session, asn_info)
            logger.info(f"ASN Saved for {host}")

        # Try Mastodon based APIs. There are a lot of non-mastodon services which
        # support the Mastodon APIs, or at least the informational ones.
        if await save_mastodon_metadata(session, instance):
            logger.info(f"Host identified as mastodon compatible: {host}")
            await save_mastodon_blocked_instances(session, instance)
            await save_mastodon_peered_instance(session, instance)

            instance.last_ingest_status = "success"
            await session.commit()
            logger.info(f"Finished processing {host}")
            return

        # The next most common set of services that don't support the above APIs
        # is PeerTube.
        if await save_peertube_metadata(session, instance):
            logger.info(f"Host identified as peertube compatible: {host}")
            await save_peertube_peered_instance(session, instance)
            instance.last_ingest_status = "success"
            # PeerTube doesn't support public ban lists at all.
            instance.has_public_bans = False
            await session.commit()
            logger.info(f"Finished processing {host}")
            return

        instance.last_ingest_status = "unknown_service"
        await session.commit()


async def save_mastodon_metadata(session: Session, instance: Instance) -> bool:
    try:
        metadata = mastodon.get_metadata(host)
    except httpx.TransportError as exc:
        instance.last_ingest_status = "unreachable"
        logger.warning(f"Unable to reach host {instance.host}")
        await session.commit()
        return
    except:
        logger.debug(f"Host is not Peertube Compatible: {instance.host}")
        return False

    instance.title = metadata.get("title", None)
    instance.short_description = metadata.get("short_description", None)
    instance.email = metadata.get("email", None)

    version_string = metadata.get("version", None)
    if version_string:
        instance.version = version_string
        version_breakdown = mastodon.get_version_breakdown(version_string)
        if version_breakdown:
            instance.software = version_breakdown.software
            instance.software_version = version_breakdown.software_version
            instance.mastodon_version = version_breakdown.mastodon_version

    instance.user_count = metadata.get("stats", {}).get("user_count", None)
    instance.status_count = metadata.get("stats", {}).get("status_count", None)
    instance.domain_count = metadata.get("stats", {}).get("domain_count", None)
    instance.thumbnail = metadata.get("thumbnail", None)

    reg_open = metadata.get("registrations", None)
    if reg_open != None:
        instance.registration_open = bool(reg_open)
    instance.approval_required = metadata.get("approval_required", None)
    await session.commit()
    return True


async def save_mastodon_blocked_instances(session: Session, instance: Instance):
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
        logger.warning(f"Unable to get instance ban data for {instance.host}")


async def save_mastodon_peered_instance(session: Session, instance: Instance):
    try:
        # Will throw exceptions when the peer list isn't public.
        peers = mastodon.get_peers(instance.host)
        instance.has_public_peers = True
        await session.commit()
        await save_peers(session, instance.host, peers)
    except:
        instance.has_public_peers = False
        await session.commit()
        logger.warning(f"Unable to get instance peer data for {instance.host}")


async def save_peertube_metadata(session: Session, instance: Instance) -> bool:

    try:
        metadata = peertube.get_metadata(instance.host)
    except httpx.TransportError as exc:
        instance.last_ingest_status = "unreachable"
        logger.warning(f"Unable to reach host {instance.host}")
        await session.commit()
        return False
    except:
        logger.debug(f"Host is not Peertube Compatible: {instance.host}")
        return False

    instance.software = "Peertube"

    instance_config = metadata.get("instance", {})
    instance.title = instance_config.get("name", None)
    instance.short_description = instance_config.get("shortDescription", None)

    instance_signup = metadata.get("signup", {})
    instance.registration_open = instance_signup.get("allowed", None)

    version = metadata.get("serverVersion", None)
    instance.version = version
    instance.software_version = version

    try:
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
        await save_peers(session, instance.host, peers)
    except:
        instance.has_public_peers = False
        await session.commit()
        logger.exception(f"Unable to get instance peer data for {instance.host}")


async def save_evil_domains(session: Session, domains: List[str]):
    if len(domains) <= 0:
        return
    evil_values = [{"domain": x} for x in domains]
    evil_insert_stmt = insert(Evil).values(evil_values)
    evil_update_statement = evil_insert_stmt.on_conflict_do_nothing(index_elements=["domain"])
    await session.execute(evil_update_statement)
    await session.commit()


async def save_peers(session: Session, host: str, peers: List[str]):
    ingest_id = str(uuid4())
    local_evils = set(settings.evil_domains) | await get_spammers_from_list(peers)
    insert_peer_values = [
        {
            "host": host,
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
    peer_delete_stmt = delete(Peer).where(and_(Peer.host == host, Peer.ingest_id != ingest_id))
    await session.execute(peer_delete_stmt)
    await session.commit()


async def get_or_save_host(db: Session, host) -> Instance:
    instance = await db.get(Instance, host)
    if instance:
        return instance
    instance = Instance(host=host)
    db.add(instance)
    await db.commit()
    return instance


async def save_asn(session: Session, asn: cymruwhois.asrecord) -> None:
    asn_insert_stmt = insert(ASN).values([{"asn": asn.asn, "cc": asn.cc, "owner": asn.owner, "prefix": asn.prefix}])
    asn_update_statement = asn_insert_stmt.on_conflict_do_update(
        index_elements=["asn"],
        set_=dict(
            cc=asn_insert_stmt.excluded.cc,
            owner=asn_insert_stmt.excluded.owner,
            prefix=asn_insert_stmt.excluded.prefix,
        ),
    )
    await session.execute(asn_update_statement)
    await session.commit()


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
