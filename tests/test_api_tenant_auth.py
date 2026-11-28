"""API boundary tests for OIDC enforcement and durable dashboard ownership."""
import asyncio
import hashlib
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.websockets import WebSocketDisconnect

from security.oidc import Principal, require_principal
from dashboard.api import main as dashboard
from solvens.api.main import app as core_api
from solvens.persistence.models import (
    Base,
    DashboardRunRecord,
    OutboxEventRecord,
    TenantRecord,
    UserRecord,
    WebSocketTicketRecord,
)


def _test_principal(request: Request) -> Principal:
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if token == "tenant-a":
        return Principal("user-a", "tenant-a", frozenset({"developer"}), user_id="db-user-a")
    if token == "tenant-a-other-user":
        return Principal("other-user", "tenant-a", frozenset({"developer"}), user_id="db-user-other")
    if token == "tenant-a-viewer":
        return Principal("viewer-a", "tenant-a", frozenset({"viewer"}), user_id="db-user-a")
    if token == "tenant-b":
        return Principal("user-b", "tenant-b", frozenset({"developer"}), user_id="db-user-b")
    raise HTTPException(status_code=401, detail="Invalid test token")


class DashboardTenantBoundaryTests(unittest.TestCase):
    def setUp(self):
        dashboard.runs.clear()
        dashboard.run_tasks.clear()
        self.db_path = tempfile.mktemp(suffix=".sqlite")
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}", poolclass=NullPool
        )
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

        async def setup_db():
            async with self.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with self.factory() as session:
                session.add_all([
                    TenantRecord(id="tenant-a", name="Tenant A"),
                    TenantRecord(id="tenant-b", name="Tenant B"),
                ])
                session.add_all([
                    UserRecord(id="db-user-a", status="active"),
                    UserRecord(id="db-user-b", status="active"),
                    UserRecord(id="db-user-other", status="active"),
                ])
                await session.commit()

        asyncio.run(setup_db())
        self.db_patch = patch("dashboard.api.main.get_session_factory", return_value=self.factory)
        self.db_patch.start()
        self.addCleanup(self._cleanup_db)
        dashboard.app.dependency_overrides[dashboard.require_principal] = _test_principal
        core_api.dependency_overrides[require_principal] = _test_principal
        self.addCleanup(dashboard.app.dependency_overrides.clear)
        self.addCleanup(core_api.dependency_overrides.clear)
        self.client = TestClient(dashboard.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def _cleanup_db(self):
        dashboard.run_tasks.clear()
        self.db_patch.stop()
        asyncio.run(self.engine.dispose())
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _wait_for_completed(self, run_id: str, token: str = "tenant-a", timeout: float = 4.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self.client.get(
                f"/api/run/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200 and response.json()["status"] == "completed":
                return response.json()
            time.sleep(0.05)
        self.fail(f"run {run_id} did not reach completed state")

    def _issue_ticket(self, run_id: str, token: str):
        return self.client.post(
            "/api/auth/ws-ticket",
            headers={"Authorization": f"Bearer {token}"},
            json={"run_id": run_id},
        )

    def test_core_api_requires_auth_except_health(self):
        client = TestClient(core_api)
        self.assertEqual(client.get("/status").status_code, 401)
        self.assertEqual(client.get("/health").status_code, 200)
        client.close()

    def test_dashboard_requires_bearer_token(self):
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 401)

    def test_run_read_is_tenant_and_user_scoped(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "private-flow", "tasks": []},
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)

        foreign_tenant = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-b"},
        )
        foreign_user = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-a-other-user"},
        )
        own = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-a"},
        )
        self.assertEqual(foreign_tenant.status_code, 404)
        self.assertEqual(foreign_user.status_code, 404)
        self.assertEqual(own.status_code, 200)

    def test_viewer_can_read_owned_run_but_cannot_start_execution(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "role-gate-flow", "tasks": []},
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)

        read_response = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-a-viewer"},
        )
        execute_response = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a-viewer"},
            json={"name": "viewer-forbidden", "tasks": []},
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(execute_response.status_code, 403)

    def test_run_survives_process_local_cache_loss(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "persisted-flow", "tasks": []},
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)
        dashboard.runs.clear()

        restored = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-a"},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["run_id"], run_id)

    def test_task_progress_and_metrics_survive_cache_loss(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "durable-progress", "tasks": [{"name": "task-1"}]},
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id, timeout=4.0)
        dashboard.runs.clear()

        restored = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-a"},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["status"], "completed")
        self.assertEqual(restored.json()["nodes"][0]["data"]["status"], "done")
        metrics = self.client.get(
            f"/api/run/{run_id}/metrics",
            headers={"Authorization": "Bearer tenant-a"},
        )
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(metrics.json()["tasks_completed"], 1)

    def test_run_snapshot_and_outbox_events_commit_together(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "outbox-flow", "tasks": []},
        )
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)

        async def read_events():
            async with self.factory() as session:
                return (
                    await session.execute(
                        select(OutboxEventRecord)
                        .where(OutboxEventRecord.aggregate_id == run_id)
                        .order_by(OutboxEventRecord.id.asc())
                    )
                ).scalars().all()

        events = asyncio.run(read_events())
        self.assertGreaterEqual(len(events), 3)
        sequences = [event.payload["sequence"] for event in events]
        self.assertEqual(sequences, sorted(sequences))
        self.assertEqual(events[-1].payload["user_id"], "db-user-a")
        self.assertIsNone(events[-1].published_at)

    def test_run_listing_does_not_disclose_other_tenants(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "tenant-a-flow", "tasks": []},
        )
        self._wait_for_completed(created.json()["run_id"])
        listed = self.client.get(
            "/api/runs",
            headers={"Authorization": "Bearer tenant-b"},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])

    def test_websocket_ticket_is_hashed_run_bound_and_one_use(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "ws-flow", "tasks": []},
        )
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)
        ticket_response = self._issue_ticket(run_id, "tenant-a")
        self.assertEqual(ticket_response.status_code, 200)
        ticket = ticket_response.json()["ticket"]

        with self.client.websocket_connect(f"/ws/run/{run_id}?ticket={ticket}") as websocket:
            initial = websocket.receive_json()
            self.assertEqual(initial["type"], "dag_update")

        async def read_ticket():
            async with self.factory() as session:
                return (
                    await session.execute(
                        select(WebSocketTicketRecord).where(
                            WebSocketTicketRecord.ticket_hash
                            == hashlib.sha256(ticket.encode()).hexdigest()
                        )
                    )
                ).scalars().one()

        record = asyncio.run(read_ticket())
        self.assertNotEqual(record.ticket_hash, ticket)
        self.assertEqual(record.run_id, run_id)
        self.assertEqual(record.user_id, "db-user-a")
        self.assertIsNotNone(record.consumed_at)
        self.assertFalse(hasattr(dashboard, "ws_tickets"))

        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(f"/ws/run/{run_id}?ticket={ticket}"):
                pass

    def test_ticket_cannot_be_issued_for_another_users_run(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "private-user-run", "tasks": []},
        )
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)
        response = self._issue_ticket(run_id, "tenant-a-other-user")
        self.assertEqual(response.status_code, 404)

    def test_ticket_cannot_be_issued_across_tenants(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "tenant-a-ws", "tasks": []},
        )
        run_id = created.json()["run_id"]
        self._wait_for_completed(run_id)
        response = self._issue_ticket(run_id, "tenant-b")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
