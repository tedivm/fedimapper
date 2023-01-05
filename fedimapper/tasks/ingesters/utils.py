import datetime
import random
from logging import getLogger
from typing import List, Set
from uuid import uuid4

from sqlalchemy import and_, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from tld import get_tld

from fedimapper.models.evil import Evil
from fedimapper.models.instance import Instance
from fedimapper.models.peer import Peer
from fedimapper.services.db import DB_MODE, DB_MODE_SQLITE, buffer_inserts
from fedimapper.settings import settings

logger = getLogger(__name__)


def get_safe_fld(domain: str):
    # If there are only two parts it has to be a full domain already.
    domain_chunks = domain.split(".")
    if len(domain_chunks) == 2:
        return f"{domain_chunks[0]}.{domain_chunks[1]}"

    # get_tld is expensive because of the large TLD database.
    res = get_tld(domain, as_object=True, fail_silently=True, fix_protocol=True)
    if res and not isinstance(res, str):
        return res.fld

    # This occurs for gTLDs that aren't in our database.
    if len(domain_chunks) >= 2:
        return f"{domain_chunks[-2]}.{domain_chunks[-1]}"
    return domain


async def get_spammers_from_list(hosts: List[str] | Set[str]):
    domain_count = {}
    for host in hosts:
        fld = get_safe_fld(host)
        if not fld in domain_count:
            domain_count[fld] = 1
        else:
            domain_count[fld] += 1
    return set([domain for domain, count in domain_count.items() if count >= settings.spam_domain_threshold])


async def save_evil_domains(session: Session, domains: List[str] | Set[str]):
    if len(domains) <= 0:
        return
    evil_values = [{"domain": x} for x in domains]
    evil_insert_stmt = insert(Evil).values(evil_values)
    evil_update_statement = evil_insert_stmt.on_conflict_do_nothing(index_elements=["domain"])
    await session.execute(evil_update_statement)
    await session.commit()


async def save_peers(session: Session, host: str, peers: Set[str]):

    sorted_peers: List[str] = sorted(peers)
    ingest_id = str(uuid4())
    local_evils = set(settings.evil_domains) | await get_spammers_from_list(sorted_peers)
    insert_peer_values = [
        {
            "host": host,
            "peer_host": peer_host,
            "ingest_id": ingest_id,
        }
        for peer_host in sorted_peers
        if peer_host and len([suffix for suffix in local_evils if peer_host.endswith(suffix)]) == 0
    ]

    if len(insert_peer_values) > 0:
        # Add Peers to Instances for future processing.
        # This also has to have before the peer relationship itself due to foreign keys.
        insert_instance_values = [
            {
                "host": peer_host["peer_host"],
                "base_domain": get_safe_fld(peer_host["peer_host"]),
            }
            for peer_host in insert_peer_values
        ]

        insert_instance_stmt = insert(Instance)
        insert_instance_conflict_stmt = insert_instance_stmt.on_conflict_do_nothing(index_elements=["host"])
        await buffer_inserts(session, insert_instance_conflict_stmt, insert_instance_values)

        insert_peer_stmt = insert(Peer).on_conflict_do_nothing(index_elements=["host", "peer_host"])
        await buffer_inserts(session, insert_peer_stmt, insert_peer_values)

    # Delete old relationships that weren't in this ingest.
    peer_delete_stmt = delete(Peer).where(and_(Peer.host == host, Peer.ingest_id != ingest_id))
    await session.execute(peer_delete_stmt)
    await session.commit()


async def should_save_peers(instance: Instance) -> bool:
    if not instance.last_ingest_peers:
        return True

    peer_age = (datetime.datetime.utcnow() - instance.last_ingest_peers).total_seconds

    # If older than X hours return True.
    if peer_age > 3600 * settings.refresh_peers_hours:
        return True

    # If older than X/2 hours randomly return true.
    # This skews peer lookups so they don't all happen at once.
    if peer_age > 3600 * settings.refresh_peers_hours / 2:
        return random.randint(0, 6) == 0

    return False
