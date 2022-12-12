import datetime
from logging import getLogger
from uuid import uuid4

import httpx
from sqlalchemy import and_, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from mastodon_tracking.models.peer import Peer

from ..models.ban import Ban
from ..models.instance import Instance
from ..services import db, mastodon

logger = getLogger(__name__)


async def ingest_host(host: str) -> None:
    logger.info(f"Ingesting from {host}")
    ingest_id = str(uuid4())
    ingest_status = "success"

    async with db.get_session() as session:

        instance = await get_or_save_host(session, host)
        instance.last_ingest = datetime.datetime.utcnow()

        try:
            metadata = mastodon.get_metadata(host)
        except httpx.TransportError as exc:
            instance.last_ingest_status = "unreachable"
            logger.error(f"Unable to get reach host {host}")
            await session.commit()
            return
        except:
            instance.last_ingest_status = "failed"
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

        instance.registration_open = metadata.get("registrations", None)
        instance.approval_required = metadata.get("approval_required", None)

        try:
            # Add banned servers.
            banned = mastodon.get_blocked_instances(host)
            ban_values = [
                {
                    "host": host,
                    "banned_host": banned_host["domain"],
                    "ingest_id": ingest_id,
                    "severity": banned_host["severity"],
                    "comment": banned_host["comment"],
                }
                for banned_host in banned
            ]
            ban_insert_stmt = insert(Ban).values(ban_values)
            ban_update_statement = ban_insert_stmt.on_conflict_do_update(
                index_elements=["host", "banned_host"],
                set_=dict(severity=ban_insert_stmt.excluded.severity, comment=ban_insert_stmt.excluded.comment),
            )
            await session.execute(ban_update_statement)

            ban_delete_stmt = delete(Ban).where(and_(Ban.host == host, Ban.ingest_id != ingest_id))
            await session.execute(ban_delete_stmt)
        except:
            logger.error(f"Unable to get instance ban data for {host}")
            ingest_status = "failed"

        try:
            # Add peered servers.
            peers = mastodon.get_peers(host)
            insert_peer_values = [
                {
                    "host": host,
                    "peer_host": peer_host,
                    "ingest_id": ingest_id,
                }
                for peer_host in peers
            ]
            insert_peer_stmt = (
                insert(Peer).values(insert_peer_values).on_conflict_do_nothing(index_elements=["host", "peer_host"])
            )
            await session.execute(insert_peer_stmt)

            peer_delete_stmt = delete(Peer).where(and_(Peer.host == host, Peer.ingest_id != ingest_id))
            await session.execute(peer_delete_stmt)

            # Add Peers to Instances for future processing.
            insert_instance_values = [{"host": peer_host} for peer_host in peers]
            insert_instance_stmt = (
                insert(Instance).values(insert_instance_values).on_conflict_do_nothing(index_elements=["host"])
            )
            await session.execute(insert_instance_stmt)

        except:
            ingest_status = "failed"
            logger.error(f"Unable to get instance peer data for {host}")

        instance.last_ingest_status = ingest_status
        await session.commit()
        logger.info(f"Finished processing {host}")


async def get_or_save_host(db: Session, host) -> Instance:

    instance = await db.get(Instance, host)
    if instance:
        return instance

    instance = Instance(host=host)
    db.add(instance)
    await db.commit()
    return instance
