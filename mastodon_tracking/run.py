import asyncio
import datetime
import logging

from mastodon_tracking.models.instance import Instance
from sqlalchemy import and_, select

from .services import db
from .settings import settings
from .tasks.ingest import ingest_host
from .utils.queuerunner import QueueRunner


async def get_unscanned(session, desired):
    select_stmt = select(Instance).where(Instance.last_ingest == None).limit(desired)
    return await session.execute(select_stmt)


async def get_stale(session, desired):
    stale_scan = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.stale_rescan_hours)
    select_stmt = (
        select(Instance)
        .where(and_(Instance.last_ingest < stale_scan, Instance.last_ingest_status != "unreachable"))
        .limit(desired)
    )
    return await session.execute(select_stmt)


async def get_unreachable(session, desired):
    stale_scan = datetime.datetime.utcnow() - datetime.timedelta(days=settings.unreachable_rescan_hours)
    select_stmt = (
        select(Instance)
        .where(and_(Instance.last_ingest < stale_scan, Instance.last_ingest_status == "unreachable"))
        .limit(desired)
    )
    return await session.execute(select_stmt)


async def get_next_instance(desired: int = None) -> str:

    async with db.get_session() as session:
        for lookup in [get_unscanned, get_stale, get_unreachable]:
            results = await lookup(session, desired)
            for row in results:
                desired += 1
                instance = row[0]
                yield instance.host
            results.close()
            if desired <= 0:
                break

    # Start with our bootstrap instances to ensure we have something to work with.
    if desired > 0:
        for host in settings.bootstrap_instances:
            yield host


if __name__ == "__main__":
    runner = QueueRunner("ingest", reader=ingest_host, writer=get_next_instance, settings=settings)
    asyncio.run(runner.main())
