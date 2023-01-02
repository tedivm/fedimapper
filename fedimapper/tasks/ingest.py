import datetime
from logging import getLogger
from typing import Any, Callable, Dict, List
from uuid import UUID, uuid4

import cymruwhois
import httpx
from sqlalchemy import and_, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from tld import get_tld

from fedimapper.services.nodeinfo import get_nodeinfo
from fedimapper.services.stopwords import get_key_words
from fedimapper.utils.hash import sha256string

from ..models.asn import ASN
from ..models.ban import Ban
from ..models.evil import Evil
from ..models.instance import Instance, InstanceStats
from ..models.peer import Peer
from ..services import db, mastodon, networking, peertube
from ..settings import settings

logger = getLogger(__name__)


def get_safe_tld(domain: str):
    # If there are only two parts it has to be a full domain already.
    domain_chunks = domain.split(".")
    if len(domain_chunks) == 2:
        return f"{domain_chunks[0]}.{domain_chunks[1]}"

    # get_tld is expensive because of the large TLD database.
    res = get_tld(domain, as_object=True, fail_silently=True)
    if res:
        return res.fld

    # This occurs for gTLDs that aren't in our database.
    if len(domain_chunks) >= 2:
        return f"{domain_chunks[-2]}.{domain_chunks[-1]}"
    return domain


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
        if not instance.digest:
            instance.digest = sha256string(host)
        if not instance.base_domain:
            instance.base_domain = get_safe_tld(host)
        await session.commit()

        if not ip_address:
            logger.info(f"No DNS for {host}")
            instance.last_ingest_status = "no_dns"
            await session.commit()
            return

        instance.ip_address = ip_address
        asn_info = networking.get_asn_data(ip_address)
        if asn_info:
            instance.asn = asn_info.asn
            await save_asn(session, asn_info)
            logger.debug(f"ASN Saved for {host}")

        # Add Reachability Check on port 443
        index_response, index_contents = networking.can_access_https(host)
        if not index_response:
            instance.last_ingest_status = "unreachable"
            await session.commit()
            logger.info(f"Unable to reach {host}")
            return

        if index_response.status_code == 530 or (index_contents and "domain parking" in index_contents.lower()):
            instance.last_ingest_status = "disabled"
            await session.commit()
            logger.info(f"Host no longer has hosting {host}")
            return

        nodeinfo = await get_nodeinfo(host)
        if nodeinfo:
            instance.nodeinfo_version = nodeinfo.get("version", None)
            await session.commit()

        # Process with service specific function.
        processor = await get_processor(nodeinfo)
        if await processor(session, instance, nodeinfo):
            logger.info(f"Successfully processed {instance.host}")
            return True

        # Save whatever nodeinfo we have.
        if nodeinfo and await save_nodeinfo(session, instance, nodeinfo):
            logger.info(f"Successfully processed {instance.host}")
            return True

        instance.last_ingest_status = "unknown_service"
        logger.info(f"Unable to process {host}")
        await session.commit()


#
# Mastodon
#
async def save_mastodon(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:
    if not await save_mastodon_metadata(session, instance, nodeinfo):
        return False

    logger.info(f"Host identified as mastodon compatible: {instance.host}")
    await save_mastodon_blocked_instances(session, instance)
    await save_mastodon_peered_instance(session, instance)

    instance.last_ingest_status = "success"
    await session.commit()
    return True


async def save_mastodon_metadata(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:
    if not nodeinfo:
        nodeinfo = {}
    nodeinfo_usage = nodeinfo.get("usage", {})

    try:
        metadata = mastodon.get_metadata(instance.host)
    except httpx.TransportError as exc:
        instance.last_ingest_status = "unreachable"
        logger.info(f"Unable to reach host {instance.host}")
        await session.commit()
        return False
    except:
        logger.debug(f"Host is not Mastodon Compatible: {instance.host}")
        return False

    instance.title = metadata.get("title", None)
    instance.short_description = metadata.get("short_description", None)
    instance.email = metadata.get("email", None)

    software = nodeinfo.get("software", {}).get("name", None)
    if software:
        instance.software = software.lower()

    version = nodeinfo.get("software", {}).get("version", None)
    if version:
        instance.version = version
        instance.software_version = version

    version_string = metadata.get("version", None)
    if version_string:
        instance.version = version_string
        version_breakdown = mastodon.get_version_breakdown(version_string)
        if version_breakdown:
            if not software:
                instance.software = version_breakdown.software
            if not version:
                instance.software_version = version_breakdown.software_version
            instance.mastodon_version = version_breakdown.mastodon_version

    instance.current_user_count = metadata.get("stats", {}).get("user_count", nodeinfo_usage.get("total", None))
    instance.current_status_count = metadata.get("stats", {}).get("status_count", None)
    instance.current_domain_count = metadata.get("stats", {}).get("domain_count", None)
    instance.thumbnail = metadata.get("thumbnail", None)

    reg_open = metadata.get("registrations", None)
    if reg_open != None:
        instance.registration_open = bool(reg_open)
    instance.approval_required = metadata.get("approval_required", None)

    instance_stats = InstanceStats(
        host=instance.host,
        user_count=instance.current_user_count,
        active_monthly_users=nodeinfo_usage.get("users", {}).get("activeMonth", None),
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
        banned = mastodon.get_blocked_instances(instance.host)
        instance.has_public_bans = True

        local_evils = set(settings.evil_domains) | await get_spammers_from_list([x["domain"] for x in banned])

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
            ban_insert_stmt = insert(Ban).values(ban_values)
            ban_update_statement = ban_insert_stmt.on_conflict_do_update(
                index_elements=["host", "banned_host"],
                set_=dict(
                    severity=ban_insert_stmt.excluded.severity,
                    comment=ban_insert_stmt.excluded.comment,
                    keywords=ban_insert_stmt.excluded.keywords,
                    ingest_id=ban_insert_stmt.excluded.ingest_id,
                ),
            )
            await session.execute(ban_update_statement)

        ban_delete_stmt = delete(Ban).where(and_(Ban.host == instance.host, Ban.ingest_id != ingest_id))
        await session.execute(ban_delete_stmt)
        await session.commit()

    except:
        instance.has_public_bans = False
        logger.debug(f"Unable to get instance ban data for {instance.host}")


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
        logger.debug(f"Unable to get instance peer data for {instance.host}")


#
# Peertube
#
async def save_peertube(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:

    # The next most common set of services that don't support the above APIs
    # is PeerTube.
    if not await save_peertube_metadata(session, instance, nodeinfo):
        return False

    if nodeinfo:
        await save_nodeinfo_stats(session, instance, nodeinfo)

    logger.info(f"Host identified as peertube compatible: {instance.host}")
    await save_peertube_peered_instance(session, instance)

    instance.last_ingest_status = "success"
    # PeerTube doesn't support public ban lists at all.
    instance.has_public_bans = False
    await session.commit()
    return True


async def save_peertube_metadata(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:

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
        user_count = None
        status_count = None

        if nodeinfo:
            usage = nodeinfo.get("usage", {})
            user_count = usage.get("users", {}).get("total", None)
            status_count = usage.get("localPosts", None)

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
        await save_peers(session, instance.host, peers)
    except:
        instance.has_public_peers = False
        await session.commit()
        logger.exception(f"Unable to get instance peer data for {instance.host}")


#
# Nodeinfo
#


async def save_nodeinfo(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:
    if not nodeinfo:
        nodeinfo = {}

    logger.info(f"Host identified as nodeinfo compatible: {instance.host}")

    instance.software = nodeinfo.get("software", {}).get("name", None)
    instance.software_version = nodeinfo.get("software", {}).get("version", None)
    instance.version = nodeinfo.get("software", {}).get("version", None)
    await session.commit()

    await save_nodeinfo_stats(session, instance, nodeinfo)
    return True


async def save_nodeinfo_stats(session: Session, instance: Instance, nodeinfo: Dict[Any, Any] | None) -> bool:

    nodeinfo_usage = nodeinfo.get("usage", None)
    if not nodeinfo_usage:
        return False

    user_piece = nodeinfo_usage.get("users", {}).get("total", None)
    if user_piece:
        if isinstance(user_piece, dict):
            instance.current_user_count = user_piece.get("total", None)
        else:
            try:
                instance.current_user_count = int(user_piece)
            except:
                instance.current_user_count = None

    instance.current_status_count = nodeinfo_usage.get("localPosts", None)

    instance_stats = InstanceStats(
        host=instance.host,
        user_count=instance.current_user_count,
        active_monthly_users=nodeinfo_usage.get("users", {}).get("activeMonth", None),
        status_count=instance.current_status_count,
        domain_count=instance.current_domain_count,
    )
    session.add(instance_stats)
    await session.commit()
    return True


#
# General
#


async def get_processor(nodeinfo: Dict[Any, Any] | None) -> Callable:
    if not nodeinfo:
        return save_mastodon

    software = nodeinfo.get("software", {}).get("name", "").lower()
    if software == "peertube":
        return save_peertube

    # Try Mastodon based APIs. There are a lot of non-mastodon services which
    # support the Mastodon APIs, or at least the informational ones.
    return save_mastodon


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
        insert_instance_values = [
            {
                "host": peer_host["peer_host"],
                "base_domain": get_safe_tld(peer_host["peer_host"]),
            }
            for peer_host in insert_peer_values
        ]
        insert_instance_stmt = insert(Instance).values(insert_instance_values)
        insert_instance_conflict_stmt = insert_instance_stmt.on_conflict_do_update(
            index_elements=["host"],
            set_=dict(base_domain=insert_instance_stmt.excluded.base_domain),
        )

        await session.execute(insert_instance_conflict_stmt)
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
        fld = get_safe_tld(host)
        if not fld in domain_count:
            domain_count[fld] = 1
        else:
            domain_count[fld] += 1
    return set([domain for domain, count in domain_count.items() if count >= settings.spam_domain_threshold])
