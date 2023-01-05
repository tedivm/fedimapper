from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from .db import get_engine

async_engine = get_engine()


@asynccontextmanager
async def get_session() -> AsyncSession:
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await session.close()


async def get_session_depends() -> AsyncSession:
    async with get_session() as session:
        yield session
