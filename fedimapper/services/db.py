import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from ..settings import settings


# Enable WAL mode on connect
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


# SQLAlchemy async engine requires non-standard driver DSN that don't work with other libraries.
# We use the standard but transform it for the async engine.
engine_mappings = {
    "sqlite": "sqlite+aiosqlite",
    "postgresql+psycopg2": "postgresql+asyncpg",
    # "postgresql": "postgresql+asyncpg",
}

db_url = settings.database_url
for find, replace in engine_mappings.items():
    db_url = db_url.replace(find, replace)

DB_MODE_POSTGRES = "POSTGRES"
DB_MODE_SQLITE = "SQLITE"
DB_MODE_OTHER = "OTHER"

if "sqlite" in db_url:
    DB_MODE = DB_MODE_SQLITE
elif "postgresql" in db_url:
    DB_MODE = DB_MODE_POSTGRES
else:
    DB_MODE = DB_MODE_OTHER

engine = create_async_engine(
    db_url, future=True, echo=settings.sql_debug, connect_args={"timeout": 20}, poolclass=NullPool
)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await session.close()


async def get_session_depends() -> AsyncSession:
    async with get_session() as session:
        yield session


async def buffer_inserts(session: AsyncSession, stmt, values: List[Dict[Any, Any]]):
    """Breaks up insert statements to prevent deadlocks.
        SQLite inserts are not buffered- its locking system prevents deadlocks.

    Args:
        session (AsyncSession): _description_
        stmt (_type_): _description_
        values (List[Dict[Any, Any]]): _description_
    """
    if DB_MODE == DB_MODE_SQLITE:
        valued_stmt = stmt.values(values)
        await session.execute(valued_stmt)
    else:
        index = 0
        while index * settings.bulk_insert_buffer < len(values):
            start = index * settings.bulk_insert_buffer
            end = start + settings.bulk_insert_buffer
            valued_stmt = stmt.values(values[start:end])
            index += 1
            await session.execute(valued_stmt)
            await session.commit()
