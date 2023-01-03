import datetime
from logging import getLogger
from typing import Any, Callable, Dict, cast

import cymruwhois
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from fedimapper.models.asn import ASN
from fedimapper.models.instance import Instance
from fedimapper.services import db, networking
from fedimapper.services.nodeinfo import get_nodeinfo
from fedimapper.settings import settings
from fedimapper.tasks.ingesters import diaspora, mastodon, nodeinfo, peertube, utils
from fedimapper.utils.hash import sha256string

logger = getLogger(__name__)

PROCESSORS = {
    "diaspora": diaspora.save,
    "mastodon": mastodon.save,
    "nodeinfo": nodeinfo.save,
    "peertube": peertube.save,
}


async def ingest_host(host: str) -> bool:
    logger.info(f"Ingesting from {host}")

    try:

        for suffix in settings.evil_domains:
            if host.endswith(suffix):
                logger.info(f"Skipping ingest from {host} for matching evil pattern: {suffix}")
                return False

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
                instance.base_domain = utils.get_safe_fld(host)

            await session.commit()

            if not ip_address:
                logger.info(f"No DNS for {host}")
                instance.last_ingest_status = "no_dns"
                await session.commit()
                return False

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
                return False

            if index_response.status_code == 530 or (index_contents and "domain parking" in index_contents.lower()):  # type: ignore
                instance.last_ingest_status = "disabled"
                await session.commit()
                logger.info(f"Host no longer has hosting {host}")
                return False

            nodeinfo = await get_nodeinfo(host)
            if nodeinfo:
                instance.nodeinfo_version = cast(Dict[Any, Any], nodeinfo).get("version", None)
                await session.commit()

            # Process with service specific function.
            processor = await get_processor(nodeinfo)
            if await processor(session, instance, nodeinfo):
                await mark_success(session, instance)
                return True

            # Save whatever nodeinfo we have.
            if nodeinfo and await PROCESSORS["nodeinfo"](session, instance, nodeinfo):
                await mark_success(session, instance)
                return True

            instance.last_ingest_status = "unknown_service"
            logger.info(f"Unable to process {host}")
            await session.commit()
            return True
    except:
        logger.exception(f"Unhandled error while processing host {host}.")
        if instance:
            instance.last_ingest_status = "crawl_error"
            await session.commit()
        raise


async def mark_success(session: Session, instance: Instance):
    instance.last_ingest_status = "success"
    instance.last_ingest_success = datetime.datetime.utcnow()
    if not instance.first_ingest_success:
        instance.first_ingest_success = instance.last_ingest_success
    await session.commit()
    logger.info(f"Successfully processed {instance.host}")


async def get_processor(nodeinfo: Dict[Any, Any] | None) -> Callable:
    if nodeinfo and "software" in nodeinfo:
        software = nodeinfo["software"].get("name", "").lower()
        if software in PROCESSORS:
            return PROCESSORS[software]

    # Try Mastodon based APIs. There are a lot of non-mastodon services which
    # support the Mastodon APIs, or at least the informational ones.
    return PROCESSORS["mastodon"]


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
