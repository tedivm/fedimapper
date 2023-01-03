import datetime
import logging
from logging import getLogger

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.sqlite import insert
from tld.utils import update_tld_names

from fedimapper.models.instance import Instance

from .services import db
from .settings import UNREADABLE_STATUSES, settings

logger = logging.getLogger(__name__)


async def bootstrap(session):
    insert_instance_values = [{"host": host} for host in settings.bootstrap_instances]
    insert_instance_stmt = (
        insert(Instance).values(insert_instance_values).on_conflict_do_nothing(index_elements=["host"])
    )
    await session.execute(insert_instance_stmt)
    await session.commit()


async def get_unscanned(session, desired):
    select_stmt = select(Instance).where(Instance.last_ingest == None).limit(desired)
    return await session.execute(select_stmt)


async def get_stale(session, desired):
    stale_scan = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.stale_rescan_hours)
    select_stmt = (
        select(Instance)
        .where(and_(Instance.last_ingest < stale_scan, Instance.last_ingest_status.not_in(UNREADABLE_STATUSES)))
        .order_by(Instance.last_ingest.asc())
        .limit(desired)
    )
    return await session.execute(select_stmt)


async def get_unreachable(session, desired):
    stale_scan = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.unreachable_rescan_hours)
    select_stmt = (
        select(Instance)
        .where(
            and_(
                Instance.last_ingest < stale_scan,
                or_(Instance.last_ingest_status.in_(UNREADABLE_STATUSES), Instance.last_ingest_status == None),
            )
        )
        .order_by(Instance.last_ingest.asc())
        .limit(desired)
    )
    return await session.execute(select_stmt)


async def get_next_instance(desired: int = None) -> str:

    async with db.get_session() as session:
        await bootstrap(session)
        for lookup in [get_unscanned, get_stale, get_unreachable]:
            results = await lookup(session, desired)
            for row in results:
                desired -= 1
                instance = row[0]
                yield instance.host
            results.close()
            if desired <= 0:
                break

    # Start with our bootstrap instances to ensure we have something to work with.
    if desired > 0:
        logger.debug("All instances have been crawled- nothing available.")
