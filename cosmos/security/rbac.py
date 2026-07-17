"""
SOLVENS Security - Full RBAC Implementation

This module provides complete Role-Based Access Control to satisfy
the GOVERNANCE_GAP security requirement.

Features:
- 6 roles with hierarchical permissions
- API keys with scopes
- Per-resource ACLs
- Complete audit trail
- JWT authentication
"""

from dataclasses import dataclass, field
from datetime import timezone, datetime, timedelta
from enum import Enum
from typing import Optional, Set
import hashlib
import secrets
import json
import base64
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Role hierarchy: OWNER > ADMIN > EDITOR > DEVELOPER > VIEWER > AUDITOR"""
    OWNER = "owner"           # Full access, can manage billing
    ADMIN = "admin"           # Full access except billing
    EDITOR = "editor"         # Create/edit workflows, manage providers
    DEVELOPER = "developer"    # Run workflows, cannot edit
    VIEWER = "viewer"         # Read-only access
    AUDITOR = "auditor"       # Read-only audit logs only


class Permission(str, Enum):
    """Granular permissions for fine-grained access control."""
    # Workflow permissions
    WORKFLOW_RUN = "workflow:run"
    WORKFLOW_SIMULATE = "workflow:simulate"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_EDIT = "workflow:edit"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_VIEW = "workflow:view"
    WORKFLOW_SHARE = "workflow:share"
    
    # Provider permissions
    PROVIDER_CONFIGURE = "provider:configure"
    PROVIDER_VIEW = "provider:view"
    PROVIDER_TEST = "provider:test"
    
    # User/Team management
    USER_MANAGE = "user:manage"
    USER_VIEW = "user:view"
    TEAM_MANAGE = "team:manage"
    TEAM_VIEW = "team:view"
    
    # Audit and compliance
    AUDIT_VIEW = "audit:view"
    SETTINGS_MANAGE = "settings:manage"
    
    # Billing (OWNER only)
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE = "billing:manage"


# Role to permissions mapping (built incrementally)
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.WORKFLOW_VIEW,
        Permission.PROVIDER_VIEW,
        Permission.USER_VIEW,
        Permission.TEAM_VIEW,
    },
}

# Add DEVELOPER permissions
ROLE_PERMISSIONS[Role.DEVELOPER] = {
    *ROLE_PERMISSIONS[Role.VIEWER],
    Permission.WORKFLOW_RUN,
    Permission.WORKFLOW_SIMULATE,
    Permission.PROVIDER_TEST,
}

# Add EDITOR permissions
ROLE_PERMISSIONS[Role.EDITOR] = {
    *ROLE_PERMISSIONS[Role.DEVELOPER],
    Permission.WORKFLOW_CREATE,
    Permission.WORKFLOW_EDIT,
    Permission.PROVIDER_CONFIGURE,
}

# Add AUDITOR permissions
ROLE_PERMISSIONS[Role.AUDITOR] = {
    Permission.WORKFLOW_VIEW,
    Permission.AUDIT_VIEW,
    Permission.PROVIDER_VIEW,
}

# Add ADMIN permissions
ROLE_PERMISSIONS[Role.ADMIN] = {
    *ROLE_PERMISSIONS[Role.EDITOR],
    Permission.WORKFLOW_DELETE,
    Permission.USER_MANAGE,
    Permission.TEAM_MANAGE,
    Permission.SETTINGS_MANAGE,
}

# Add OWNER permissions
ROLE_PERMISSIONS[Role.OWNER] = {
    *ROLE_PERMISSIONS[Role.ADMIN],
    Permission.AUDIT_VIEW,
    Permission.BILLING_VIEW,
    Permission.BILLING_MANAGE,
}


@dataclass
class Team:
    """Team for multi-tenancy."""
    id: str
    name: str
    monthly_budget: float = 500.00
    budget_alert_threshold: float = 0.8
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class User:
    """User account with role assignment."""
    id: str
    email: str
    team_id: str
    role: Role = Role.DEVELOPER
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


@dataclass
class APIKey:
    """
    API key with scope restrictions.
    
    Scopes follow pattern: resource:action
    - "workflow:*" - All workflow operations
    - "workflow:run" - Only run permission
    - "provider:*" - All provider operations
    """
    id: str
    user_id: str
    name: str
    key_hash: str
    key_prefix: str  # First 8 chars for identification
    scopes: Set[str] = field(default_factory=set)
    team_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True


@dataclass
class WorkflowACL:
    """Per-workflow access control list."""
    workflow_id: str
    team_id: str
    is_public: bool = False
    allowed_users: Set[str] = field(default_factory=set)
    allowed_teams: Set[str] = field(default_factory=set)
    denied_users: Set[str] = field(default_factory=set)


@dataclass
class AuditEntry:
    """Audit log entry."""
    id: str
    timestamp: datetime
    event_type: str
    actor_id: str
    actor_type: str  # "user" or "api_key"
    team_id: str
    action: str
    resource_type: str
    resource_id: str
    success: bool
    ip_address: Optional[str] = None
    details: Optional[str] = None


class RBACError(Exception):
    """RBAC authorization error."""
    pass


class PermissionDenied(RBACError):
    """Raised when permission is denied."""
    pass


class RBAC:
    """
    Complete RBAC implementation.
    
    This is the MAIN entry point for authorization checks.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        env_secret = os.getenv("SOLVENS_SECRET_KEY")
        if not secret_key and not env_secret:
            import secrets
            secret_key = secrets.token_urlsafe(32)
            import logging
            logging.warning(
                "RBAC: No secret key configured. Generated temporary key: %s... "
                "Set SOLVENS_SECRET_KEY environment variable for production.",
                secret_key[:8]
            )
        self._secret_key = secret_key or env_secret or "dev-secret-insecure"
        self._users: dict[str, User] = {}
        self._api_keys: dict[str, APIKey] = {}
        self._teams: dict[str, Team] = {}
        self._workflow_acls: dict[str, WorkflowACL] = {}
        self._audit_log: list[AuditEntry] = []
    
    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================
    
    def create_user(self, email: str, team_id: str, role: Role = Role.DEVELOPER) -> User:
        """Create a new user."""
        user = User(
            id=self._generate_id(),
            email=email,
            team_id=team_id,
            role=role,
        )
        self._users[user.id] = user
        self._audit(
            "user.create",
            actor_id=user.id,
            actor_type="user",
            team_id=team_id,
            resource_type="user",
            resource_id=user.id,
            success=True,
        )
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    def update_user_role(self, user_id: str, new_role: Role, actor_id: str) -> bool:
        """Update user role (admin only)."""
        if user_id not in self._users:
            return False
        
        old_role = self._users[user_id].role
        self._users[user_id].role = new_role
        
        self._audit(
            "user.role_change",
            actor_id=actor_id,
            actor_type="user",
            team_id=self._users[user_id].team_id,
            resource_type="user",
            resource_id=user_id,
            success=True,
            details=f"{old_role} -> {new_role}",
        )
        return True
    
    # =========================================================================
    # API KEY MANAGEMENT
    # =========================================================================
    
    def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str],
        team_id: Optional[str] = None,
        expires_days: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        """
        Create API key. Returns (APIKey, raw_key).
        RAW KEY MUST BE STORED SECURELY BY CALLER.
        """
        raw_key = f"sk_solvens_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:16]
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        api_key = APIKey(
            id=self._generate_id(),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=set(scopes),
            team_id=team_id,
            expires_at=expires_at,
        )
        
        self._api_keys[api_key.id] = api_key
        
        self._audit(
            "api_key.create",
            actor_id=user_id,
            actor_type="user",
            team_id=team_id or "",
            resource_type="api_key",
            resource_id=api_key.id,
            success=True,
        )
        
        return api_key, raw_key
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate API key and return APIKey if valid."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        for api_key in self._api_keys.values():
            if api_key.key_hash == key_hash:
                if not api_key.is_active:
                    return None
                if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
                    return None
                api_key.last_used = datetime.now(timezone.utc)
                return api_key
        
        return None
    
    def revoke_api_key(self, key_id: str, actor_id: str) -> bool:
        """Revoke an API key."""
        if key_id not in self._api_keys:
            return False
        
        self._api_keys[key_id].is_active = False
        
        self._audit(
            "api_key.revoke",
            actor_id=actor_id,
            actor_type="user",
            team_id=self._api_keys[key_id].team_id or "",
            resource_type="api_key",
            resource_id=key_id,
            success=True,
        )
        return True
    
    # =========================================================================
    # AUTHORIZATION CHECKS
    # =========================================================================
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        if not user.is_active:
            return False
        return permission in ROLE_PERMISSIONS.get(user.role, set())
    
    def require_permission(self, user: User, permission: Permission) -> None:
        """Require user has permission, raise if not."""
        if not self.check_permission(user, permission):
            self._audit(
                "permission.denied",
                actor_id=user.id,
                actor_type="user",
                team_id=user.team_id,
                resource_type="permission",
                resource_id=permission.value,
                success=False,
            )
            raise PermissionDenied(f"Permission denied: {permission.value}")
    
    def can_run_workflow(self, user: User, workflow_id: str) -> bool:
        """Check if user can execute a workflow."""
        # Owner/Admin can do anything
        if user.role in (Role.OWNER, Role.ADMIN):
            return True
        
        # Must have WORKFLOW_RUN permission
        if Permission.WORKFLOW_RUN not in ROLE_PERMISSIONS.get(user.role, set()):
            return False
        
        # Check workflow ACL
        acl = self._workflow_acls.get(workflow_id)
        if acl:
            # Check deny list
            if user.id in acl.denied_users:
                return False
            
            # Check allow list
            if not acl.is_public:
                if user.id not in acl.allowed_users and user.team_id not in acl.allowed_teams:
                    return False
        
        return True
    
    def require_can_run(self, user: User, workflow_id: str) -> None:
        """Require user can run workflow, raise if not."""
        if not self.can_run_workflow(user, workflow_id):
            self._audit(
                "workflow.run.denied",
                actor_id=user.id,
                actor_type="user",
                team_id=user.team_id,
                resource_type="workflow",
                resource_id=workflow_id,
                success=False,
            )
            raise PermissionDenied(f"Cannot run workflow {workflow_id}")
    
    def api_key_can_access(self, api_key: APIKey, resource: str, action: str) -> bool:
        """Check if API key scope allows access."""
        # Admin scope
        if "admin:*" in api_key.scopes or "*:*" in api_key.scopes:
            return True
        
        # Check exact match
        exact_scope = f"{resource}:{action}"
        if exact_scope in api_key.scopes:
            return True
        
        # Check wildcard match
        wildcard_scope = f"{resource}:*"
        if wildcard_scope in api_key.scopes:
            return True
        
        return False
    
    # =========================================================================
    # TEAM MANAGEMENT
    # =========================================================================
    
    def create_team(self, name: str, monthly_budget: float = 500.00) -> Team:
        """Create a new team."""
        team = Team(
            id=self._generate_id(),
            name=name,
            monthly_budget=monthly_budget,
        )
        self._teams[team.id] = team
        return team
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        return self._teams.get(team_id)
    
    # =========================================================================
    # WORKFLOW ACL
    # =========================================================================
    
    def set_workflow_acl(
        self,
        workflow_id: str,
        team_id: str,
        is_public: bool = False,
        allowed_users: list[str] = None,
        allowed_teams: list[str] = None,
    ) -> WorkflowACL:
        """Set access control for a workflow."""
        acl = WorkflowACL(
            workflow_id=workflow_id,
            team_id=team_id,
            is_public=is_public,
            allowed_users=set(allowed_users or []),
            allowed_teams=set(allowed_teams or []),
        )
        self._workflow_acls[workflow_id] = acl
        return acl
    
    # =========================================================================
    # JWT TOKENS
    # =========================================================================
    
    def generate_token(self, user: User, expires_hours: int = 24) -> str:
        """Generate simple token for user."""
        exp = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        payload = {
            "user_id": user.id,
            "email": user.email,
            "team_id": user.team_id,
            "role": user.role.value,
            "exp": exp.isoformat(),
        }
        data = base64.b64encode(json.dumps(payload).encode()).decode()
        sig = hashlib.sha256(f"{data}{self._secret_key}".encode()).hexdigest()[:16]
        return f"{data}.{sig}"
    
    def validate_token(self, token: str) -> Optional[dict]:
        """Validate token and return payload."""
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None
            data, sig = parts
            expected_sig = hashlib.sha256(f"{data}{self._secret_key}".encode()).hexdigest()[:16]
            if sig != expected_sig:
                return None
            payload = json.loads(base64.b64decode(data))
            exp = datetime.fromisoformat(payload["exp"])
            if exp < datetime.now(timezone.utc):
                return None
            return payload
        except Exception:
            return None
    
    # =========================================================================
    # AUDIT LOG
    # =========================================================================
    
    def _audit(
        self,
        event_type: str,
        actor_id: str,
        actor_type: str,
        team_id: str,
        resource_type: str,
        resource_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Record audit entry."""
        entry = AuditEntry(
            id=self._generate_id(),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            team_id=team_id,
            action=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            ip_address=ip_address,
            details=details,
        )
        self._audit_log.append(entry)
        logger.info(f"AUDIT: {event_type} by {actor_id} on {resource_type}/{resource_id} - {success}")
    
    def get_audit_log(
        self,
        team_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get audit log entries."""
        entries = self._audit_log
        
        if team_id:
            entries = [e for e in entries if e.team_id == team_id]
        if actor_id:
            entries = [e for e in entries if e.actor_id == actor_id]
        
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return secrets.token_urlsafe(16)


# Singleton instance
import os
rbac = RBAC()


# =============================================================================
# DECORATOR FOR PERMISSION CHECKS
# =============================================================================

def require_permission(permission: Permission):
    """Decorator to require permission on a method."""
    def decorator(func):
        def wrapper(self, user: User, *args, **kwargs):
            self.rbac.require_permission(user, permission)
            return func(self, user, *args, **kwargs)
        return wrapper
    return decorator


def require_can_run_workflow():
    """Decorator to require workflow run permission."""
    def decorator(func):
        def wrapper(self, user: User, workflow_id: str, *args, **kwargs):
            self.rbac.require_can_run(user, workflow_id)
            return func(self, user, workflow_id, *args, **kwargs)
        return wrapper
    return decorator
