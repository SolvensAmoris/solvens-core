"""Transactional outbox publisher for dashboard snapshot events.

The database transaction owns event creation and publication markers. Redis Streams
provide replayable fan-out; duplicate publication is possible and consumers dedupe
using the event's aggregate sequence.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from solvens.persistence.database import get_session_factory
from solvens.persistence.models import OutboxEventRecord

logger = structlog.get_logger(__name__)


class OutboxPublisher:
    def __init__(
        self,
        *,
        redis_url: str,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        redis_client: Redis | None = None,
        stream: str = "solvens:dashboard:events",
        batch_size: int = 100,
        max_stream_length: int = 50000,
        poll_interval: float = 0.5,
    ) -> None:
        if not redis_url and redis_client is None:
            raise ValueError("redis_url or redis_client is required")
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        if max_stream_length < 100:
            raise ValueError("max_stream_length must be at least 100")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self._session_factory = session_factory
        self.redis = redis_client or Redis.from_url(redis_url, decode_responses=True)
        self._owns_redis = redis_client is None
        self.stream = stream
        self.batch_size = batch_size
        self.max_stream_length = max_stream_length
        self.poll_interval = poll_interval
        self._stop = asyncio.Event()

    def _factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory or get_session_factory()

    async def publish_once(self) -> int:
        """Publish one bounded batch and mark rows only after Redis accepts them."""
        factory = self._factory()
        published = 0
        async with factory() as session:
            events = (
                await session.execute(
                    select(OutboxEventRecord)
                    .where(OutboxEventRecord.published_at.is_(None))
                    .order_by(OutboxEventRecord.created_at.asc(), OutboxEventRecord.id.asc())
                    .limit(self.batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).scalars().all()
            if not events:
                await session.rollback()
                return 0

            now = datetime.now(timezone.utc)
            for event in events:
                envelope = {
                    "event_id": event.id,
                    "tenant_id": event.tenant_id,
                    "aggregate_type": event.aggregate_type,
                    "aggregate_id": event.aggregate_id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "created_at": event.created_at.isoformat(),
                }
                encoded = json.dumps(envelope, separators=(",", ":"), allow_nan=False)
                await self.redis.xadd(
                    self.stream,
                    {"event": encoded},
                    maxlen=self.max_stream_length,
                    approximate=True,
                )
                event.published_at = now
                published += 1
            await session.commit()
        return published

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                count = await self.publish_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Outbox publish failed", error=str(exc))
                count = 0
            if count == 0:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
                except TimeoutError:
                    pass

    def stop(self) -> None:
        self._stop.set()

    async def close(self) -> None:
        if self._owns_redis:
            await self.redis.aclose()
