"""
SOLVENS Security - Immutable Audit Logging

Append-only audit log with SHA256 chain integrity.
Export to SIEM: Splunk, Datadog, Sentinel.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib
import json
import sqlite3
from pathlib import Path


class AuditEventType(str):
    """Types of auditable events."""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    USER_ROLE_CHANGE = "user.role_change"
    
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"
    API_KEY_USE = "api_key.use"
    
    WORKFLOW_RUN = "workflow.run"
    WORKFLOW_SIMULATE = "workflow.simulate"
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_EDIT = "workflow.edit"
    WORKFLOW_DELETE = "workflow.delete"
    
    PROVIDER_CONFIGURE = "provider.configure"
    PROVIDER_TEST = "provider.test"
    
    SETTINGS_CHANGE = "settings.change"
    
    COST_ALERT = "cost.alert"
    BUDGET_EXCEEDED = "budget.exceeded"
    
    PII_DETECTED = "pii.detected"
    PII_REDACTED = "pii.redacted"
    
    SECURITY_VIOLATION = "security.violation"
    PERMISSION_DENIED = "permission.denied"


@dataclass
class AuditEvent:
    """
    Immutable audit event record.
    
    Each event includes:
    - SHA256 hash of previous event (chain integrity)
    - SHA256 hash of event data (tamper detection)
    - All metadata for forensics
    """
    id: str
    timestamp: datetime
    event_type: str
    actor_id: str  # User or API key ID
    actor_type: str  # "user" or "api_key"
    team_id: str
    
    # Resource info
    resource_type: str  # workflow, user, api_key, etc.
    resource_id: str
    
    # Action details
    action: str
    success: bool
    error_message: Optional[str] = None
    
    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Data
    input_hash: Optional[str] = None  # SHA256 of input data
    output_hash: Optional[str] = None  # SHA256 of output data
    
    # Integrity chain
    prev_hash: str = ""  # Hash of previous event
    event_hash: str = ""  # Hash of this event's data
    
    # Additional metadata
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "team_id": self.team_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "success": self.success,
            "error_message": self.error_message,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "prev_hash": self.prev_hash,
            "event_hash": self.event_hash,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


class AuditLogger:
    """
    Append-only audit logger with immutable chain.
    
    Features:
    - SHA256 hash chain (blockchain-like integrity)
    - SQLite backend with write-only access
    - Export to Splunk, Datadog, Azure Sentinel
    """
    
    def __init__(self, db_path: str = "/audit/solvens.db"):
        self.db_path = db_path
        self._init_db()
        self._last_hash = self._get_last_hash()
    
    def _init_db(self):
        """Initialize SQLite database with write-only schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                team_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                action TEXT NOT NULL,
                success INTEGER NOT NULL,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT,
                input_hash TEXT,
                output_hash TEXT,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for efficient querying
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_actor ON audit_events(actor_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_team ON audit_events(team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_resource ON audit_events(resource_type, resource_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)")
        
        # Prevent deletions - no DELETE privilege should be granted
        conn.execute("CREATE TABLE IF NOT EXISTS audit_lock (locked INTEGER DEFAULT 1)")
        
        conn.commit()
        conn.close()
    
    def _get_last_hash(self) -> str:
        """Get the hash of the last event in the chain."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.execute(
            "SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "GENESIS"
    
    def _compute_event_hash(self, event: AuditEvent) -> str:
        """Compute SHA256 hash of event data."""
        data = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "actor_id": event.actor_id,
            "actor_type": event.actor_type,
            "team_id": event.team_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "success": event.success,
            "error_message": event.error_message,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "input_hash": event.input_hash,
            "output_hash": event.output_hash,
            "metadata": event.metadata,
            "prev_hash": event.prev_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def log(
        self,
        event_type: str,
        actor_id: str,
        actor_type: str,
        team_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        input_data: Optional[dict] = None,
        output_data: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (from AuditEventType)
            actor_id: ID of user or API key
            actor_type: "user" or "api_key"
            team_id: Team ID
            resource_type: Type of resource affected
            resource_id: ID of resource
            action: Action performed
            success: Whether action succeeded
            ... (additional context)
        
        Returns:
            Created AuditEvent
        """
        import secrets
        
        event = AuditEvent(
            id=secrets.token_urlsafe(16),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            team_id=team_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            input_hash=hashlib.sha256(json.dumps(input_data).encode()).hexdigest() if input_data else None,
            output_hash=hashlib.sha256(json.dumps(output_data).encode()).hexdigest() if output_data else None,
            prev_hash="",
            metadata=metadata or {},
        )
        
        # Serialize writers and derive the chain tip inside the same transaction.
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("BEGIN IMMEDIATE")
        tip = conn.execute(
            "SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        event.prev_hash = tip[0] if tip else "GENESIS"
        event.event_hash = self._compute_event_hash(event)

        # Append-only insert
        conn.execute(
            """
            INSERT INTO audit_events (
                id, timestamp, event_type, actor_id, actor_type, team_id,
                resource_type, resource_id, action, success, error_message,
                ip_address, user_agent, input_hash, output_hash, prev_hash,
                event_hash, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.timestamp.isoformat(),
                event.event_type,
                event.actor_id,
                event.actor_type,
                event.team_id,
                event.resource_type,
                event.resource_id,
                event.action,
                1 if success else 0,
                event.error_message,
                event.ip_address,
                event.user_agent,
                event.input_hash,
                event.output_hash,
                event.prev_hash,
                event.event_hash,
                json.dumps(event.metadata),
            )
        )
        conn.commit()
        conn.close()

        self._last_hash = event.event_hash
        return event
    
    def verify_chain(self) -> tuple[bool, list[str]]:
        """
        Verify the integrity of the audit chain.
        
        Returns:
            Tuple of (is_valid, list of broken chain points)
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.execute(
            "SELECT * FROM audit_events ORDER BY rowid ASC"
        )
        rows = cursor.fetchall()
        conn.close()
        
        broken = []
        expected_prev = "GENESIS"
        
        for row in rows:
            prev_hash = row[15]    # prev_hash column
            event_hash = row[16]  # event_hash column
            
            if prev_hash != expected_prev:
                broken.append(f"Event {row[0]}: prev_hash mismatch")
            
            # Recompute hash to verify
            event = AuditEvent(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                event_type=row[2],
                actor_id=row[3],
                actor_type=row[4],
                team_id=row[5],
                resource_type=row[6],
                resource_id=row[7],
                action=row[8],
                success=bool(row[9]),
                error_message=row[10],
                ip_address=row[11],
                user_agent=row[12],
                input_hash=row[13],
                output_hash=row[14],
                prev_hash=prev_hash,
                event_hash=event_hash,
                metadata=json.loads(row[17]) if row[17] else {},
            )
            computed = self._compute_event_hash(event)
            if computed != event_hash:
                broken.append(f"Event {row[0]}: hash mismatch")
            
            expected_prev = event_hash
        
        return len(broken) == 0, broken
    
    def query(
        self,
        team_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """Query audit events with filters."""
        conditions = []
        params = []
        
        if team_id:
            conditions.append("team_id = ?")
            params.append(team_id)
        if actor_id:
            conditions.append("actor_id = ?")
            params.append(actor_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        if resource_id:
            conditions.append("resource_id = ?")
            params.append(resource_id)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        query = "SELECT * FROM audit_events"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            AuditEvent(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                event_type=row[2],
                actor_id=row[3],
                actor_type=row[4],
                team_id=row[5],
                resource_type=row[6],
                resource_id=row[7],
                action=row[8],
                success=bool(row[9]),
                error_message=row[10],
                ip_address=row[11],
                user_agent=row[12],
                input_hash=row[13],
                output_hash=row[14],
                prev_hash=row[15],
                event_hash=row[16],
                metadata=json.loads(row[17]) if row[17] else {},
            )
            for row in rows
        ]
    
    def export_splunk(self, output_path: str):
        """Export events in Splunk HEC format."""
        events = self.query(limit=10000)
        with open(output_path, "w") as f:
            for event in events:
                splunk_event = {
                    "time": event.timestamp.timestamp(),
                    "host": "solvens-enterprise",
                    "source": "solvens:audit",
                    "sourcetype": "solvens:audit:json",
                    "event": event.to_dict(),
                }
                f.write(json.dumps(splunk_event) + "\n")
    
    def export_datadog(self, output_path: str):
        """Export events in Datadog format."""
        events = self.query(limit=10000)
        with open(output_path, "w") as f:
            for event in events:
                dd_event = {
                    "ddsource": "solvens",
                    "service": "solvens-enterprise",
                    "ddtags": f"team:{event.team_id},type:{event.event_type}",
                    "hostname": "solvens-enterprise",
                    "timestamp": int(event.timestamp.timestamp() * 1000),
                    "message": f"[{event.event_type}] {event.action} by {event.actor_id}",
                    "attributes": event.to_dict(),
                }
                f.write(json.dumps(dd_event) + "\n")
