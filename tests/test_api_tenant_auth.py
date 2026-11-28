"""API boundary tests for OIDC enforcement and tenant isolation."""
import unittest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from security.oidc import Principal, require_principal
from dashboard.api import main as dashboard
from solvens.api.main import app as core_api


def _test_principal(request: Request) -> Principal:
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if token == "tenant-a":
        return Principal("user-a", "tenant-a", frozenset({"developer"}), user_id="db-user-a")
    if token == "tenant-a-other-user":
        return Principal("other-user", "tenant-a", frozenset({"developer"}), user_id="db-user-other")
    if token == "tenant-b":
        return Principal("user-b", "tenant-b", frozenset({"developer"}), user_id="db-user-b")
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Invalid test token")


class DashboardTenantBoundaryTests(unittest.TestCase):
    def setUp(self):
        dashboard.runs.clear()
        dashboard.ws_tickets.clear()
        dashboard.app.dependency_overrides[dashboard.require_principal] = _test_principal
        core_api.dependency_overrides[require_principal] = _test_principal
        self.addCleanup(dashboard.app.dependency_overrides.clear)
        self.addCleanup(core_api.dependency_overrides.clear)
        self.client = TestClient(dashboard.app)

    def test_core_api_requires_auth_except_health(self):
        client = TestClient(core_api)
        self.assertEqual(client.get("/status").status_code, 401)
        self.assertEqual(client.get("/health").status_code, 200)

    def test_dashboard_requires_bearer_token(self):
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 401)

    def test_run_read_is_tenant_scoped(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "private-flow", "tasks": []},
        )
        self.assertEqual(created.status_code, 200)
        run_id = created.json()["run_id"]

        foreign = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-b"},
        )
        own = self.client.get(
            f"/api/run/{run_id}",
            headers={"Authorization": "Bearer tenant-a"},
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(own.status_code, 200)

    def test_run_listing_does_not_disclose_other_tenants(self):
        self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "tenant-a-flow", "tasks": []},
        )
        listed = self.client.get(
            "/api/runs",
            headers={"Authorization": "Bearer tenant-b"},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])

    def test_websocket_ticket_is_one_use_and_tenant_bound(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "ws-flow", "tasks": []},
        )
        run_id = created.json()["run_id"]
        ticket_response = self.client.post(
            "/api/auth/ws-ticket",
            headers={"Authorization": "Bearer tenant-a"},
        )
        ticket = ticket_response.json()["ticket"]

        with self.client.websocket_connect(f"/ws/run/{run_id}?ticket={ticket}") as websocket:
            initial = websocket.receive_json()
            self.assertEqual(initial["type"], "dag_update")

        self.assertNotIn(ticket, dashboard.ws_tickets)

    def test_websocket_ticket_cannot_cross_user_in_same_tenant(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "private-user-run", "tasks": []},
        )
        run_id = created.json()["run_id"]
        ticket_response = self.client.post(
            "/api/auth/ws-ticket",
            headers={"Authorization": "Bearer tenant-a-other-user"},
        )
        ticket = ticket_response.json()["ticket"]
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(f"/ws/run/{run_id}?ticket={ticket}"):
                pass

    def test_websocket_ticket_cannot_cross_tenant(self):
        created = self.client.post(
            "/api/run",
            headers={"Authorization": "Bearer tenant-a"},
            json={"name": "tenant-a-ws", "tasks": []},
        )
        run_id = created.json()["run_id"]
        ticket_response = self.client.post(
            "/api/auth/ws-ticket",
            headers={"Authorization": "Bearer tenant-b"},
        )
        ticket = ticket_response.json()["ticket"]
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(f"/ws/run/{run_id}?ticket={ticket}"):
                pass


if __name__ == "__main__":
    unittest.main()
