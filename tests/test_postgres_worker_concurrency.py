from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from solvens.persistence.leases import claim_next_task
from solvens.persistence.models import CoreTaskRecord, TenantRecord, UserRecord


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (os.getenv("SOLVENS_DATABASE_URL") or os.getenv("DATABASE_URL")),
    reason="PostgreSQL integration requires a configured database URL",
)
async def test_postgres_skip_locked_claims_distinct_rows_without_waiting():
    """Keep worker A's row lock open while worker B claims a different task."""
    from solvens.persistence.database import database_url

    engine = create_async_engine(database_url(), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    task_ids = [str(uuid.uuid4()) for _ in range(3)]

    try:
        async with factory() as session:
            session.add_all([
                TenantRecord(id=tenant_id, name="pg-skip-locked-test"),
                UserRecord(id=user_id, status="active"),
            ])
            await session.flush()
            session.add_all([
                CoreTaskRecord(
                    id=task_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    status="queued",
                    priority=10,
                    payload={"handler": "test", "input": {"n": index}},
                    attempt_count=0,
                    max_attempts=3,
                )
                for index, task_id in enumerate(task_ids)
            ])
            await session.commit()

        async with factory() as worker_a_session:
            first = await claim_next_task(
                worker_a_session,
                worker_id="postgres-worker-a",
                lease_seconds=60,
            )
            assert first is not None
            # Do not commit yet: worker A continues holding its row lock.
            async with factory() as worker_b_session:
                second = await asyncio.wait_for(
                    claim_next_task(
                        worker_b_session,
                        worker_id="postgres-worker-b",
                        lease_seconds=60,
                    ),
                    timeout=2.0,
                )
                assert second is not None
                assert second.id != first.id
                await worker_b_session.commit()
            await worker_a_session.commit()
    finally:
        async with factory() as session:
            await session.execute(
                delete(CoreTaskRecord).where(CoreTaskRecord.tenant_id == tenant_id)
            )
            await session.execute(delete(UserRecord).where(UserRecord.id == user_id))
            await session.execute(delete(TenantRecord).where(TenantRecord.id == tenant_id))
            await session.commit()
        await engine.dispose()
