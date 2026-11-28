from __future__ import annotations

import json
import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from solvens.persistence.models import Base, OutboxEventRecord
from solvens.persistence.outbox import OutboxPublisher


class FakeRedis:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.entries: list[tuple[str, dict[str, str]]] = []

    async def xadd(self, stream, fields, *, maxlen, approximate):
        if self.fail:
            raise RuntimeError("redis unavailable")
        self.entries.append((stream, fields))
        return f"{len(self.entries)}-0"


@pytest.mark.asyncio
async def test_outbox_publisher_marks_only_after_stream_accepts_event():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with factory() as session:
        event = OutboxEventRecord(
            tenant_id="tenant-outbox",
            aggregate_type="dashboard_run",
            aggregate_id="run-outbox",
            event_type="dashboard.run.snapshot",
            payload={"sequence": 7, "snapshot": {"status": "completed"}},
        )
        session.add(event)
        await session.commit()
        event_id = event.id

    redis = FakeRedis()
    publisher = OutboxPublisher(
        redis_url="redis://unused",
        redis_client=redis,
        session_factory=factory,
        stream="test:dashboard:events",
    )
    assert await publisher.publish_once() == 1
    assert redis.entries[0][0] == "test:dashboard:events"
    envelope = json.loads(redis.entries[0][1]["event"])
    assert envelope["event_id"] == event_id
    assert envelope["payload"]["sequence"] == 7

    async with factory() as session:
        record = await session.get(OutboxEventRecord, event_id)
        assert record.published_at is not None
    assert await publisher.publish_once() == 0
    await engine.dispose()


@pytest.mark.asyncio
async def test_outbox_publish_failure_leaves_event_unpublished():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        event = OutboxEventRecord(
            tenant_id="tenant-outbox",
            aggregate_type="dashboard_run",
            aggregate_id="run-failure",
            event_type="dashboard.run.snapshot",
            payload={"sequence": 1},
        )
        session.add(event)
        await session.commit()
        event_id = event.id

    publisher = OutboxPublisher(
        redis_url="redis://unused",
        redis_client=FakeRedis(fail=True),
        session_factory=factory,
    )
    with pytest.raises(RuntimeError, match="redis unavailable"):
        await publisher.publish_once()
    async with factory() as session:
        record = await session.get(OutboxEventRecord, event_id)
        assert record.published_at is None
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (
        os.getenv("SOLVENS_REDIS_URL")
        and (os.getenv("SOLVENS_DATABASE_URL") or os.getenv("DATABASE_URL"))
    ),
    reason="Redis Streams integration requires Redis and database URLs",
)
async def test_redis_stream_replays_published_outbox_event():
    from redis.asyncio import Redis

    from solvens.persistence.database import database_url

    engine = create_async_engine(database_url(), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    stream = f"test:solvens:outbox:{uuid.uuid4().hex}"
    redis = Redis.from_url(os.environ["SOLVENS_REDIS_URL"], decode_responses=True)
    publisher = OutboxPublisher(
        redis_url=os.environ["SOLVENS_REDIS_URL"],
        redis_client=redis,
        session_factory=factory,
        stream=stream,
    )
    event_id = None
    try:
        async with factory() as session:
            event = OutboxEventRecord(
                tenant_id=str(uuid.uuid4()),
                aggregate_type="test",
                aggregate_id=str(uuid.uuid4()),
                event_type="test.replay",
                payload={"sequence": 11, "value": "replayable"},
            )
            session.add(event)
            await session.commit()
            event_id = event.id

        assert await publisher.publish_once() >= 1
        first = await redis.xread({stream: "0-0"}, block=1000, count=10)
        second = await redis.xread({stream: "0-0"}, block=1000, count=10)
        first_event = json.loads(first[0][1][0][1]["event"])
        second_event = json.loads(second[0][1][0][1]["event"])
        assert first_event["event_id"] == event_id
        assert second_event["event_id"] == event_id
        assert first_event["payload"]["sequence"] == 11
    finally:
        if event_id is not None:
            async with factory() as session:
                await session.execute(
                    OutboxEventRecord.__table__.delete().where(
                        OutboxEventRecord.id == event_id
                    )
                )
                await session.commit()
        await redis.delete(stream)
        await redis.aclose()
        await engine.dispose()
