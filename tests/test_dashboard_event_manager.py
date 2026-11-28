import json

import pytest

from dashboard.api.main import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages: list[str] = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, message: str):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_snapshot_fanout_is_tenant_bound_and_sequence_deduplicated():
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    await manager.connect(
        websocket,
        "run-001",
        tenant_id="tenant-a",
        user_id="user-a",
        sequence=10,
    )
    assert websocket.accepted

    await manager.broadcast_snapshot(
        run_id="run-001",
        tenant_id="tenant-a",
        sequence=10,
        snapshot={"status": "old"},
    )
    await manager.broadcast_snapshot(
        run_id="run-001",
        tenant_id="tenant-b",
        sequence=12,
        snapshot={"status": "wrong-tenant"},
    )
    assert websocket.messages == []

    await manager.broadcast_snapshot(
        run_id="run-001",
        tenant_id="tenant-a",
        sequence=11,
        snapshot={"status": "new"},
    )
    await manager.broadcast_snapshot(
        run_id="run-001",
        tenant_id="tenant-a",
        sequence=9,
        snapshot={"status": "stale"},
    )
    assert len(websocket.messages) == 1
    message = json.loads(websocket.messages[0])
    assert message["type"] == "dag_update"
    assert message["data"]["status"] == "new"

    manager.disconnect(websocket, "run-001")
    assert "run-001" not in manager.run_owners
    assert "run-001" not in manager.last_sequence
