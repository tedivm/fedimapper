from contextlib import asynccontextmanager
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..settings import settings


# Enable WAL mode on connect
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


# SQLAlchemy async engine requires non-standard driver DSN that don't work with other libraries.
# We use the standard but transform it for the async engine.
engine_mappings = {
    "sqlite": "sqlite+aiosqlite",
    "postgresql": "postgresql+asyncpg",
}

db_url = settings.database_url
for find, replace in engine_mappings.items():
    db_url = db_url.replace(find, replace)


engine = create_async_engine(db_url, future=True, echo=settings.debug, connect_args={"timeout": 20})


@asynccontextmanager
async def get_session() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def get_session_depends() -> AsyncSession:
    async with get_session() as session:
        yield session
