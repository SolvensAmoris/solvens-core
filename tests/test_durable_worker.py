from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from solvens.persistence.models import Base, CoreTaskRecord, TenantRecord, UserRecord
from solvens.persistence.worker import DurableTaskWorker


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tenant_id = "tenant-worker-test"
    user_id = "user-worker-test"
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        session.add_all([
            TenantRecord(id=tenant_id, name="worker-test"),
            UserRecord(id=user_id, status="active"),
        ])
        await session.commit()
    yield factory, tenant_id, user_id
    await engine.dispose()


@pytest.mark.asyncio
async def test_durable_worker_completes_and_clears_lease(db):
    factory, tenant_id, user_id = db

    async def echo(payload):
        return {"echo": payload["value"]}

    worker = DurableTaskWorker(
        worker_id="worker-success",
        handlers={"test.echo": echo},
        session_factory=factory,
        lease_seconds=3,
    )
    task_id = await worker.submit_task(
        tenant_id=tenant_id,
        user_id=user_id,
        handler_name="test.echo",
        payload={"value": "proof"},
    )

    assert await worker.run_once()
    async with factory() as session:
        task = await session.get(CoreTaskRecord, task_id)
        assert task.status == "completed"
        assert task.result == {"echo": "proof"}
        assert task.attempt_count == 1
        assert task.worker_id is None
        assert task.lease_expires_at is None


@pytest.mark.asyncio
async def test_durable_worker_retries_then_completes(db):
    factory, tenant_id, user_id = db
    calls = 0

    async def flaky(payload):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return {"ok": True}

    worker = DurableTaskWorker(
        worker_id="worker-retry",
        handlers={"test.flaky": flaky},
        session_factory=factory,
        lease_seconds=3,
    )
    task_id = await worker.submit_task(
        tenant_id=tenant_id,
        user_id=user_id,
        handler_name="test.flaky",
        payload={},
        max_attempts=3,
    )

    assert await worker.run_once()
    async with factory() as session:
        task = await session.get(CoreTaskRecord, task_id)
        assert task.status == "queued"
        assert task.attempt_count == 1
        assert task.error == "transient"

    assert await worker.run_once()
    async with factory() as session:
        task = await session.get(CoreTaskRecord, task_id)
        assert task.status == "completed"
        assert task.attempt_count == 2


@pytest.mark.asyncio
async def test_expired_lease_is_reclaimed_by_another_worker(db):
    factory, tenant_id, user_id = db

    async def echo(payload):
        return {"recovered": True}

    expired = datetime.now(timezone.utc) - timedelta(seconds=20)
    async with factory() as session:
        session.add(CoreTaskRecord(
            id="expired-recoverable",
            tenant_id=tenant_id,
            user_id=user_id,
            status="running",
            priority=1,
            payload={"handler": "test.echo", "input": {}},
            attempt_count=1,
            max_attempts=3,
            worker_id="worker-crashed",
            lease_expires_at=expired,
            heartbeat_at=expired,
        ))
        await session.commit()

    worker = DurableTaskWorker(
        worker_id="worker-recovery",
        handlers={"test.echo": echo},
        session_factory=factory,
        lease_seconds=3,
    )
    assert await worker.run_once()
    async with factory() as session:
        task = await session.get(CoreTaskRecord, "expired-recoverable")
        assert task.status == "completed"
        assert task.worker_id is None
        assert task.attempt_count == 2


@pytest.mark.asyncio
async def test_exhausted_expired_lease_is_terminalized(db):
    factory, tenant_id, user_id = db
    expired = datetime.now(timezone.utc) - timedelta(seconds=20)
    async with factory() as session:
        session.add(CoreTaskRecord(
            id="expired-exhausted",
            tenant_id=tenant_id,
            user_id=user_id,
            status="running",
            priority=1,
            payload={"handler": "test.echo", "input": {}},
            attempt_count=3,
            max_attempts=3,
            worker_id="worker-dead",
            lease_expires_at=expired,
            heartbeat_at=expired,
        ))
        await session.commit()

    worker = DurableTaskWorker(
        worker_id="worker-terminalizer",
        handlers={},
        session_factory=factory,
        lease_seconds=3,
    )
    assert not await worker.run_once()
    async with factory() as session:
        task = await session.get(CoreTaskRecord, "expired-exhausted")
        assert task.status == "failed"
        assert task.completed_at is not None
        assert task.worker_id is None
        assert "maximum attempts" in task.error


@pytest.mark.asyncio
async def test_idempotency_key_returns_same_task_and_is_user_bound(db):
    factory, tenant_id, user_id = db

    async def echo(payload):
        return payload

    worker = DurableTaskWorker(
        worker_id="worker-idempotency",
        handlers={"test.echo": echo},
        session_factory=factory,
    )
    first = await worker.submit_task(
        tenant_id=tenant_id,
        user_id=user_id,
        handler_name="test.echo",
        payload={"x": 1},
        idempotency_key="request-001",
    )
    second = await worker.submit_task(
        tenant_id=tenant_id,
        user_id=user_id,
        handler_name="test.echo",
        payload={"x": 2},
        idempotency_key="request-001",
    )
    assert first == second
    with pytest.raises(PermissionError):
        await worker.submit_task(
            tenant_id=tenant_id,
            user_id="another-user",
            handler_name="test.echo",
            payload={},
            idempotency_key="request-001",
        )


@pytest.mark.asyncio
async def test_cancel_queued_task_and_running_task(db):
    factory, tenant_id, user_id = db
    started = asyncio.Event()

    async def slow(payload):
        started.set()
        await asyncio.sleep(30)
        return {"done": True}

    worker = DurableTaskWorker(
        worker_id="worker-cancel",
        handlers={"test.slow": slow},
        session_factory=factory,
        lease_seconds=1,
        poll_interval=0.1,
    )
    queued_id = await worker.submit_task(
        tenant_id=tenant_id,
        user_id=user_id,
        handler_name="test.slow",
        payload={},
    )
    assert await worker.cancel_task(
        task_id=queued_id, tenant_id=tenant_id, user_id=user_id
    )
    async with factory() as session:
        queued = await session.get(CoreTaskRecord, queued_id)
        assert queued.status == "cancelled"

    running_id = await worker.submit_task(
        tenant_id=tenant_id,
        user_id=user_id,
        handler_name="test.slow",
        payload={},
    )
    execution = asyncio.create_task(worker.run_once())
    await asyncio.wait_for(started.wait(), timeout=2)
    assert await worker.cancel_task(
        task_id=running_id, tenant_id=tenant_id, user_id=user_id
    )
    assert await asyncio.wait_for(execution, timeout=3)
    async with factory() as session:
        running = await session.get(CoreTaskRecord, running_id)
        assert running.status == "cancelled"
        assert running.worker_id is None
