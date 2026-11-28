"""PostgreSQL-safe task claiming with bounded worker leases.

Claims are at-least-once. Callers must make external side effects idempotent.
The caller owns the transaction and must commit the returned claim.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from solvens.persistence.models import CoreTaskRecord


async def claim_next_task(
    session: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    now: datetime | None = None,
) -> CoreTaskRecord | None:
    """Atomically claim one queued or lease-expired task.

    PostgreSQL workers use SKIP LOCKED so concurrent workers do not block on
    the same candidate. A task at its retry limit is never reclaimed.
    """
    if not worker_id or len(worker_id) > 128:
        raise ValueError("worker_id must contain 1..128 characters")
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("lease_seconds must be between 1 and 3600")

    current = now or datetime.now(timezone.utc)

    # Terminalize expired/cancel-requested records that can no longer be claimed.
    terminal_candidates = (
        await session.execute(
            select(CoreTaskRecord)
            .where(
                or_(
                    (CoreTaskRecord.status == "queued")
                    & (CoreTaskRecord.attempt_count >= CoreTaskRecord.max_attempts),
                    (CoreTaskRecord.status == "running")
                    & (CoreTaskRecord.lease_expires_at.is_not(None))
                    & (CoreTaskRecord.lease_expires_at <= current)
                    & (CoreTaskRecord.attempt_count >= CoreTaskRecord.max_attempts),
                    (CoreTaskRecord.status == "cancel_requested")
                    & (CoreTaskRecord.lease_expires_at.is_not(None))
                    & (CoreTaskRecord.lease_expires_at <= current),
                )
            )
            .order_by(CoreTaskRecord.created_at.asc())
            .limit(100)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()
    for exhausted in terminal_candidates:
        if exhausted.status == "cancel_requested":
            exhausted.status = "cancelled"
            exhausted.error = exhausted.error or "Cancelled after worker lease expired"
        else:
            exhausted.status = "failed"
            exhausted.error = exhausted.error or "Worker lease expired after maximum attempts"
        exhausted.completed_at = current
        exhausted.worker_id = None
        exhausted.lease_expires_at = None
        exhausted.heartbeat_at = None
    if terminal_candidates:
        await session.flush()

    eligible = or_(
        CoreTaskRecord.status == "queued",
        (
            (CoreTaskRecord.status == "running")
            & (CoreTaskRecord.lease_expires_at.is_not(None))
            & (CoreTaskRecord.lease_expires_at <= current)
        ),
    )
    statement = (
        select(CoreTaskRecord)
        .where(eligible, CoreTaskRecord.attempt_count < CoreTaskRecord.max_attempts)
        .order_by(CoreTaskRecord.priority.desc(), CoreTaskRecord.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    task = (await session.execute(statement)).scalars().first()
    if task is None:
        return None

    task.status = "running"
    task.worker_id = worker_id
    task.lease_expires_at = current + timedelta(seconds=lease_seconds)
    task.heartbeat_at = current
    task.attempt_count += 1
    if task.started_at is None:
        task.started_at = current
    await session.flush()
    return task


async def heartbeat_task(
    session: AsyncSession,
    *,
    task_id: str,
    worker_id: str,
    lease_seconds: int = 60,
    now: datetime | None = None,
) -> bool:
    """Extend a lease only when the caller still owns an unexpired lease."""
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("lease_seconds must be between 1 and 3600")
    current = now or datetime.now(timezone.utc)
    task = (
        await session.execute(
            select(CoreTaskRecord).where(
                CoreTaskRecord.id == task_id,
                CoreTaskRecord.status == "running",
                CoreTaskRecord.worker_id == worker_id,
                CoreTaskRecord.lease_expires_at > current,
            ).with_for_update()
        )
    ).scalars().one_or_none()
    if task is None:
        return False
    task.heartbeat_at = current
    task.lease_expires_at = current + timedelta(seconds=lease_seconds)
    await session.flush()
    return True
