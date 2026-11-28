"""API boundary tests for OIDC enforcement and tenant isolation."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from security.oidc import Principal
from dashboard.api import main as dashboard


class DashboardTenantBoundaryTests(unittest.TestCase):
    def setUp(self):
        dashboard.runs.clear()
        dashboard.ws_tickets.clear()

        def resolve(token):
            if token == "tenant-a":
                return Principal("user-a", "tenant-a", frozenset({"developer"}))
            if token == "tenant-b":
                return Principal("user-b", "tenant-b", frozenset({"developer"}))
            raise PermissionError("invalid token")

        self.auth_patch = patch("security.oidc.verify_access_token", side_effect=resolve)
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.client = TestClient(dashboard.app)

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


if __name__ == "__main__":
    unittest.main()
