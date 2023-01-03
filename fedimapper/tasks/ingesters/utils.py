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

from fedimapper.models.asn import ASN
from fedimapper.models.ban import Ban
from fedimapper.models.evil import Evil
from fedimapper.models.instance import Instance, InstanceStats
from fedimapper.models.peer import Peer
from fedimapper.services import db, mastodon, networking, peertube
from fedimapper.services.nodeinfo import get_nodeinfo
from fedimapper.services.stopwords import get_key_words
from fedimapper.settings import settings
from fedimapper.utils.hash import sha256string

logger = getLogger(__name__)


def get_safe_tld(domain: str):
    # If there are only two parts it has to be a full domain already.
    domain_chunks = domain.split(".")
    if len(domain_chunks) == 2:
        return f"{domain_chunks[0]}.{domain_chunks[1]}"

    # get_tld is expensive because of the large TLD database.
    res = get_tld(domain, as_object=True, fail_silently=True, fix_protocol=True)
    if res:
        return res.fld

    # This occurs for gTLDs that aren't in our database.
    if len(domain_chunks) >= 2:
        return f"{domain_chunks[-2]}.{domain_chunks[-1]}"
    return domain


async def get_spammers_from_list(hosts: List[str]):
    domain_count = {}
    for host in hosts:
        fld = get_safe_tld(host)
        if not fld in domain_count:
            domain_count[fld] = 1
        else:
            domain_count[fld] += 1
    return set([domain for domain, count in domain_count.items() if count >= settings.spam_domain_threshold])


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