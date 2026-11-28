from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from solvens.persistence.identity import (
    IdentityResolutionError,
    resolve_durable_principal,
)
from solvens.persistence.leases import claim_next_task, heartbeat_task
from solvens.persistence.models import (
    Base,
    CoreTaskRecord,
    MembershipRecord,
    OIDCIdentityRecord,
    TenantRecord,
    UserRecord,
)


@pytest.mark.asyncio
async def test_identity_resolution_uses_issuer_subject_and_current_membership():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            user = UserRecord(email="same@example.invalid")
            tenant = TenantRecord(name="tenant-a")
            session.add_all([user, tenant])
            await session.flush()
            session.add_all([
                OIDCIdentityRecord(
                    user_id=user.id, issuer="https://issuer.example",
                    subject="immutable-subject", status="active",
                ),
                MembershipRecord(
                    user_id=user.id, tenant_id=tenant.id,
                    role="viewer", status="active",
                ),
            ])
            await session.commit()
            principal = await resolve_durable_principal(
                session, issuer="https://issuer.example",
                subject="immutable-subject", tenant_id=tenant.id,
            )
            assert principal.user_id == user.id
            assert principal.roles == frozenset({"viewer"})
            with pytest.raises(IdentityResolutionError):
                await resolve_durable_principal(
                    session, issuer="https://issuer.example",
                    subject="different-subject", tenant_id=tenant.id,
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoked_membership_fails_closed():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            user, tenant = UserRecord(), TenantRecord(name="tenant-a")
            session.add_all([user, tenant])
            await session.flush()
            session.add_all([
                OIDCIdentityRecord(
                    user_id=user.id, issuer="https://issuer.example",
                    subject="subject", status="active",
                ),
                MembershipRecord(
                    user_id=user.id, tenant_id=tenant.id, role="owner",
                    status="revoked", revoked_at=datetime.now(timezone.utc),
                ),
            ])
            await session.commit()
            with pytest.raises(IdentityResolutionError):
                await resolve_durable_principal(
                    session, issuer="https://issuer.example",
                    subject="subject", tenant_id=tenant.id,
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_worker_claim_and_heartbeat_are_bound_to_owner():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            tenant, user = TenantRecord(name="tenant-a"), UserRecord()
            session.add_all([tenant, user])
            await session.flush()
            session.add(CoreTaskRecord(
                id="task-1", tenant_id=tenant.id, user_id=user.id,
                status="queued", priority=1, payload={},
                attempt_count=0, max_attempts=3,
            ))
            await session.commit()
        async with factory() as session:
            task = await claim_next_task(
                session, worker_id="worker-a", lease_seconds=30, now=now,
            )
            assert task is not None
            assert task.worker_id == "worker-a"
            assert task.attempt_count == 1
            await session.commit()
        async with factory() as session:
            assert not await heartbeat_task(
                session, task_id="task-1", worker_id="worker-b", now=now,
            )
            assert await heartbeat_task(
                session, task_id="task-1", worker_id="worker-a", now=now,
            )
    finally:
        await engine.dispose()
