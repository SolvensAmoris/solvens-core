"""Durable task submission and leased execution.

Workers provide at-least-once delivery. Handlers must make external side effects
idempotent; a lease prevents concurrent ownership, not duplicate effects after crash.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from solvens.persistence.database import get_session_factory
from solvens.persistence.leases import claim_next_task, heartbeat_task
from solvens.persistence.models import CoreTaskRecord

DurableHandler = Callable[[dict[str, Any]], Awaitable[Any]]
logger = structlog.get_logger(__name__)


class DurableTaskWorker:
    """Claim, execute, heartbeat, and finalize durable task records."""

    def __init__(
        self,
        *,
        worker_id: str,
        handlers: dict[str, DurableHandler],
        lease_seconds: int = 60,
        poll_interval: float = 1.0,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        if not worker_id or len(worker_id) > 128:
            raise ValueError("worker_id must contain 1..128 characters")
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.worker_id = worker_id
        self.handlers = handlers
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self._session_factory = session_factory
        self._stop = asyncio.Event()

    def _factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory or get_session_factory()

    async def submit_task(
        self,
        *,
        tenant_id: str,
        user_id: str,
        handler_name: str,
        payload: dict[str, Any],
        priority: int = 0,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
    ) -> str:
        """Persist a serializable task; duplicate idempotency keys return same ID."""
        if handler_name not in self.handlers:
            raise ValueError(f"Unregistered durable handler: {handler_name}")
        if not tenant_id or not user_id:
            raise ValueError("tenant_id and user_id are required")
        if not -100 <= priority <= 100:
            raise ValueError("priority must be between -100 and 100")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        if idempotency_key is not None and not 1 <= len(idempotency_key) <= 256:
            raise ValueError("idempotency_key must contain 1..256 characters")
        json.dumps(payload)

        factory = self._factory()
        async with factory() as session:
            if idempotency_key:
                existing = await self._find_idempotent(
                    session, tenant_id=tenant_id, idempotency_key=idempotency_key
                )
                if existing is not None:
                    if existing.user_id != user_id:
                        raise PermissionError("Idempotency key belongs to another user")
                    return existing.id

            task_id = str(uuid.uuid4())
            record = CoreTaskRecord(
                id=task_id,
                tenant_id=tenant_id,
                user_id=user_id,
                status="queued",
                priority=priority,
                payload={"handler": handler_name, "input": payload},
                idempotency_key=idempotency_key,
                attempt_count=0,
                max_attempts=max_attempts,
            )
            session.add(record)
            try:
                await session.commit()
                return task_id
            except IntegrityError:
                await session.rollback()
                if not idempotency_key:
                    raise
                existing = await self._find_idempotent(
                    session, tenant_id=tenant_id, idempotency_key=idempotency_key
                )
                if existing is None:
                    raise
                if existing.user_id != user_id:
                    raise PermissionError("Idempotency key belongs to another user")
                return existing.id

    @staticmethod
    async def _find_idempotent(
        session: AsyncSession, *, tenant_id: str, idempotency_key: str
    ) -> CoreTaskRecord | None:
        return (
            await session.execute(
                select(CoreTaskRecord).where(
                    CoreTaskRecord.tenant_id == tenant_id,
                    CoreTaskRecord.idempotency_key == idempotency_key,
                )
            )
        ).scalars().one_or_none()

    async def run_once(self) -> bool:
        """Claim and process one task. Returns False when no claim was available."""
        factory = self._factory()
        async with factory() as session:
            record = await claim_next_task(
                session,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
            if record is None:
                await session.commit()
                return False
            claim = {
                "id": record.id,
                "tenant_id": record.tenant_id,
                "user_id": record.user_id,
                "payload": dict(record.payload or {}),
                "attempt_count": record.attempt_count,
                "max_attempts": record.max_attempts,
            }
            await session.commit()

        envelope = claim["payload"]
        handler_name = envelope.get("handler")
        handler = self.handlers.get(handler_name) if isinstance(handler_name, str) else None
        input_payload = envelope.get("input", {})
        if handler is None or not isinstance(input_payload, dict):
            await self._finish_failure(
                claim,
                "Unknown handler or invalid durable task payload",
                retryable=False,
            )
            return True

        execution = asyncio.create_task(handler(input_payload))
        stop_heartbeat = asyncio.Event()
        lease_lost = asyncio.Event()
        heartbeat = asyncio.create_task(
            self._heartbeat_loop(claim["id"], execution, stop_heartbeat, lease_lost)
        )
        try:
            result = await execution
            json.dumps(result)
        except asyncio.CancelledError:
            if lease_lost.is_set():
                await self._finish_cancelled(claim["id"])
                return True
            raise
        except Exception as exc:
            if not lease_lost.is_set():
                await self._finish_failure(claim, str(exc), retryable=True)
            return True
        finally:
            stop_heartbeat.set()
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)

        if lease_lost.is_set():
            await self._finish_cancelled(claim["id"])
            return True
        await self._finish_success(claim["id"], result)
        return True

    async def _heartbeat_loop(
        self,
        task_id: str,
        execution: asyncio.Task[Any],
        stop: asyncio.Event,
        lease_lost: asyncio.Event,
    ) -> None:
        interval = max(0.5, self.lease_seconds / 3)
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
                return
            except TimeoutError:
                pass
            factory = self._factory()
            async with factory() as session:
                owned = await heartbeat_task(
                    session,
                    task_id=task_id,
                    worker_id=self.worker_id,
                    lease_seconds=self.lease_seconds,
                )
                await session.commit()
            if not owned:
                lease_lost.set()
                if not execution.done():
                    execution.cancel()
                return

    async def _finish_success(self, task_id: str, result: Any) -> bool:
        current = datetime.now(timezone.utc)
        factory = self._factory()
        async with factory() as session:
            record = (
                await session.execute(
                    select(CoreTaskRecord)
                    .where(
                        CoreTaskRecord.id == task_id,
                        CoreTaskRecord.status == "running",
                        CoreTaskRecord.worker_id == self.worker_id,
                        CoreTaskRecord.lease_expires_at > current,
                    )
                    .with_for_update()
                )
            ).scalars().one_or_none()
            if record is None:
                await session.rollback()
                return False
            record.status = "completed"
            record.result = result
            record.error = None
            record.completed_at = current
            record.worker_id = None
            record.lease_expires_at = None
            record.heartbeat_at = None
            await session.commit()
            return True

    async def _finish_failure(
        self, claim: dict[str, Any], error: str, *, retryable: bool
    ) -> None:
        current = datetime.now(timezone.utc)
        factory = self._factory()
        async with factory() as session:
            record = (
                await session.execute(
                    select(CoreTaskRecord)
                    .where(
                        CoreTaskRecord.id == claim["id"],
                        CoreTaskRecord.worker_id == self.worker_id,
                        CoreTaskRecord.status.in_(("running", "cancel_requested")),
                    )
                    .with_for_update()
                )
            ).scalars().one_or_none()
            if record is None:
                await session.rollback()
                return
            if record.status == "cancel_requested":
                record.status = "cancelled"
                record.completed_at = current
            elif retryable and record.attempt_count < record.max_attempts:
                record.status = "queued"
                record.completed_at = None
            else:
                record.status = "failed"
                record.completed_at = current
            record.error = error[:4000]
            record.worker_id = None
            record.lease_expires_at = None
            record.heartbeat_at = None
            await session.commit()

    async def _finish_cancelled(self, task_id: str) -> None:
        current = datetime.now(timezone.utc)
        factory = self._factory()
        async with factory() as session:
            record = (
                await session.execute(
                    select(CoreTaskRecord)
                    .where(
                        CoreTaskRecord.id == task_id,
                        CoreTaskRecord.status == "cancel_requested",
                        CoreTaskRecord.worker_id == self.worker_id,
                    )
                    .with_for_update()
                )
            ).scalars().one_or_none()
            if record is None:
                await session.rollback()
                return
            record.status = "cancelled"
            record.completed_at = current
            record.worker_id = None
            record.lease_expires_at = None
            record.heartbeat_at = None
            await session.commit()

    async def cancel_task(
        self, *, task_id: str, tenant_id: str, user_id: str
    ) -> bool:
        """Cancel queued work or signal a running owner to stop at heartbeat."""
        current = datetime.now(timezone.utc)
        factory = self._factory()
        async with factory() as session:
            record = (
                await session.execute(
                    select(CoreTaskRecord)
                    .where(
                        CoreTaskRecord.id == task_id,
                        CoreTaskRecord.tenant_id == tenant_id,
                        CoreTaskRecord.user_id == user_id,
                    )
                    .with_for_update()
                )
            ).scalars().one_or_none()
            if record is None or record.status not in ("queued", "running"):
                return False
            if record.status == "queued":
                record.status = "cancelled"
                record.completed_at = current
                record.error = "Cancelled by owner"
            else:
                record.status = "cancel_requested"
                record.error = "Cancellation requested by owner"
            await session.commit()
            return True

    async def run(self) -> None:
        """Poll continuously until stop() or task cancellation."""
        while not self._stop.is_set():
            try:
                claimed = await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Durable worker iteration failed", worker_id=self.worker_id, error=str(exc))
                claimed = False
            if not claimed:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
                except TimeoutError:
                    pass

    def stop(self) -> None:
        self._stop.set()
