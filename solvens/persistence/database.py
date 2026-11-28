"""Async SQLAlchemy engine and request-scoped session factory."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def database_url() -> str:
    """Return an async-driver URL; production must configure a durable database."""
    value = os.getenv("SOLVENS_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not value:
        raise RuntimeError("SOLVENS_DATABASE_URL or DATABASE_URL must be configured")
    if value.startswith("postgres://"):
        value = "postgresql+asyncpg://" + value.removeprefix("postgres://")
    elif value.startswith("postgresql://"):
        value = "postgresql+asyncpg://" + value.removeprefix("postgresql://")
    elif value.startswith("sqlite://"):
        value = "sqlite+aiosqlite://" + value.removeprefix("sqlite://")
    if value.startswith("postgresql://") or value.startswith("sqlite://"):
        raise RuntimeError("Database URL must use an installed async SQLAlchemy driver")
    if not (value.startswith("postgresql+asyncpg://") or value.startswith("sqlite+aiosqlite://")):
        raise RuntimeError("Only PostgreSQL/asyncpg and SQLite/aiosqlite URLs are supported")
    return value


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    url = database_url()
    options: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite+aiosqlite://"):
        options["connect_args"] = {"check_same_thread": False}
    return create_async_engine(url, **options)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-compatible dependency. Callers own transaction boundaries."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose pooled connections and clear cached factories (shutdown/tests)."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
