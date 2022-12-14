import datetime
from logging import getLogger
from typing import Any, Dict

from sqlalchemy.orm import Session

from fedimapper.models.instance import Instance
from fedimapper.services import diaspora
from fedimapper.services.nodeinfo import NodeInfoInstance
from fedimapper.tasks.ingesters import utils
from fedimapper.tasks.ingesters.nodeinfo import save as nodeinfo_save

logger = getLogger(__name__)


async def save(session: Session, instance: Instance, nodeinfo: NodeInfoInstance | None) -> bool:
    nodeinfo_res = await nodeinfo_save(session, instance, nodeinfo)
    if not nodeinfo_res:
        return False

    logger.info(f"Host identified as diaspora compatible: {instance.host}")
    if await utils.should_save_peers(instance):
        logger.info(f"Attempting to save peers: {instance.host}")
        instance.last_ingest_peers = datetime.datetime.utcnow()
        await session.commit()
        peers = diaspora.get_peers(instance.www_host)
        if peers and isinstance(peers, set):
            await utils.save_peers(session, instance.host, peers)

    return True
