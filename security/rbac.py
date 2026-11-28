"""
SOLVENS Security - Role-Based Access Control (RBAC)

Enterprise-grade authorization system with:
- Multi-tenant support
- Per-workflow ACLs
- API keys with scopes
- Audit logging
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import secrets
import jwt


class Role(str, Enum):
    """System roles with increasing privilege levels."""
    VIEWER = "viewer"      # Read-only access
    DEVELOPER = "developer" # Can run/simulate workflows
    EDITOR = "editor"      # Can create/edit workflows
    AUDITOR = "auditor"    # Read-only audit logs
    ADMIN = "admin"        # Full access
    OWNER = "owner"        # Tenant owner


class Permission(str, Enum):
    """Granular permissions."""
    # Workflow permissions
    WORKFLOW_RUN = "workflow:run"
    WORKFLOW_SIMULATE = "workflow:simulate"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_EDIT = "workflow:edit"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_VIEW = "workflow:view"
    
    # Provider permissions
    PROVIDER_CONFIGURE = "provider:configure"
    PROVIDER_VIEW = "provider:view"
    
    # Admin permissions
    USER_MANAGE = "user:manage"
    TEAM_MANAGE = "team:manage"
    AUDIT_VIEW = "audit:view"
    SETTINGS_MANAGE = "settings:manage"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.WORKFLOW_VIEW,
        Permission.PROVIDER_VIEW,
    },
    Role.DEVELOPER: {
        Permission.WORKFLOW_VIEW,
        Permission.WORKFLOW_RUN,
        Permission.WORKFLOW_SIMULATE,
        Permission.PROVIDER_VIEW,
    },
    Role.EDITOR: {
        Permission.WORKFLOW_VIEW,
        Permission.WORKFLOW_RUN,
        Permission.WORKFLOW_SIMULATE,
        Permission.PROVIDER_VIEW,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EDIT,
        Permission.PROVIDER_CONFIGURE,
    },
    Role.AUDITOR: {
        Permission.WORKFLOW_VIEW,
        Permission.AUDIT_VIEW,
        Permission.PROVIDER_VIEW,
    },
    Role.ADMIN: {
        Permission.WORKFLOW_VIEW,
        Permission.WORKFLOW_RUN,
        Permission.WORKFLOW_SIMULATE,
        Permission.PROVIDER_VIEW,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EDIT,
        Permission.PROVIDER_CONFIGURE,
        Permission.WORKFLOW_DELETE,
        Permission.USER_MANAGE,
        Permission.TEAM_MANAGE,
        Permission.SETTINGS_MANAGE,
    },
    Role.OWNER: {
        Permission.WORKFLOW_VIEW,
        Permission.WORKFLOW_RUN,
        Permission.WORKFLOW_SIMULATE,
        Permission.PROVIDER_VIEW,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EDIT,
        Permission.PROVIDER_CONFIGURE,
        Permission.WORKFLOW_DELETE,
        Permission.USER_MANAGE,
        Permission.TEAM_MANAGE,
        Permission.SETTINGS_MANAGE,
        Permission.AUDIT_VIEW,
    },
}


@dataclass
class Team:
    """Team/group for multi-tenancy."""
    id: str
    name: str
    monthly_budget: float = 500.00
    budget_alert_threshold: float = 0.8  # Alert at 80%
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class User:
    """User account."""
    id: str
    email: str
    team_id: str
    role: Role = Role.DEVELOPER
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


@dataclass
class APIKey:
    """
    API key with scope restrictions.
    
    Example:
        key = APIKey(
            user_id="user123",
            name="CI/CD Pipeline",
            scopes=["workflow:crm_*", "workflow:run"],
            expires_at=datetime(2025, 12, 31),
        )
    """
    id: str
    user_id: str
    name: str
    key_hash: str  # SHA256 of actual key
    key_prefix: str  # First 8 chars for identification
    scopes: list[str] = field(default_factory=list)
    team_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True


@dataclass
class WorkflowACL:
    """Per-workflow access control."""
    workflow_id: str
    team_id: str
    public: bool = False
    allowed_users: list[str] = field(default_factory=list)
    allowed_teams: list[str] = field(default_factory=list)
    deny_users: list[str] = field(default_factory=list)


class RBACManager:
    """
    Central RBAC manager for authorization decisions.
    """
    
    def __init__(self):
        self._users: dict[str, User] = {}
        self._api_keys: dict[str, APIKey] = {}
        self._teams: dict[str, Team] = {}
        self._workflow_acls: dict[str, WorkflowACL] = {}
    
    # User Management
    def create_user(self, email: str, team_id: str, role: Role = Role.DEVELOPER) -> User:
        user = User(
            id=self._generate_id(),
            email=email,
            team_id=team_id,
            role=role,
        )
        self._users[user.id] = user
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    # Team Management
    def create_team(self, name: str, monthly_budget: float = 500.00) -> Team:
        team = Team(
            id=self._generate_id(),
            name=name,
            monthly_budget=monthly_budget,
        )
        self._teams[team.id] = team
        return team
    
    def get_team(self, team_id: str) -> Optional[Team]:
        return self._teams.get(team_id)
    
    # API Key Management
    def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str],
        team_id: Optional[str] = None,
        expires_days: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.
        
        Returns:
            Tuple of (APIKey object, raw key - store securely!)
        """
        raw_key = f"sk_solvens_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:16]
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_key = APIKey(
            id=self._generate_id(),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            team_id=team_id,
            expires_at=expires_at,
        )
        
        owner = self._users.get(user_id)
        if owner is None:
            raise ValueError("API key owner does not exist")
        effective_team = team_id or owner.team_id
        if effective_team != owner.team_id:
            raise PermissionError("API keys cannot be bound outside the owner's tenant")
        api_key.team_id = effective_team
        self._api_keys[api_key.id] = api_key
        return api_key, raw_key
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return the APIKey if valid."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        for api_key in self._api_keys.values():
            if api_key.key_hash == key_hash:
                if not api_key.is_active:
                    return None
                if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                    return None
                api_key.last_used = datetime.utcnow()
                return api_key
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self._api_keys:
            self._api_keys[key_id].is_active = False
            return True
        return False
    
    # Authorization
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        stored_user = self._users.get(user.id)
        if stored_user is None or stored_user.team_id != user.team_id or stored_user.role != user.role:
            return False
        return permission in ROLE_PERMISSIONS.get(stored_user.role, set())
    
    def can_run_workflow(self, user: User, workflow_id: str) -> bool:
        """Check if user can run a specific workflow."""
        # Reject stale/foreign user objects before evaluating privileges.
        stored_user = self._users.get(user.id)
        if stored_user is None or stored_user.team_id != user.team_id or stored_user.role != user.role:
            return False

        # Tenant boundary applies to every role, including OWNER and ADMIN.
        acl = self._workflow_acls.get(workflow_id)
        if acl and acl.team_id != user.team_id:
            return False

        if acl and (user.id in acl.deny_users or user.team_id in acl.deny_users):
            return False

        # Privileged roles bypass allow-lists only inside their own tenant.
        if user.role in (Role.OWNER, Role.ADMIN):
            return True
        if acl and not acl.public:
            if user.id not in acl.allowed_users and user.team_id not in acl.allowed_teams:
                return False

        return Permission.WORKFLOW_RUN in ROLE_PERMISSIONS.get(stored_user.role, set())
    
    def scope_matches(self, scope_pattern: str, target: str) -> bool:
        """
        Check if a scope pattern matches a target.
        
        Patterns:
            workflow:* - All workflows
            workflow:crm_* - Workflows starting with crm_
            workflow:crm_generator - Exact match
        """
        if scope_pattern.endswith("*"):
            prefix = scope_pattern[:-1]
            return target.startswith(prefix)
        return scope_pattern == target
    
    def api_key_can_access(self, api_key: APIKey, resource: str, action: str) -> bool:
        """Check if API key scope allows access to resource/action."""
        # Never trust a caller-held APIKey object: reload authoritative state.
        stored = self._api_keys.get(api_key.id)
        if stored is None or stored.key_hash != api_key.key_hash or not stored.is_active:
            return False
        if stored.expires_at and stored.expires_at <= datetime.utcnow():
            return False
        owner = self._users.get(stored.user_id)
        if owner is None:
            return False
        if stored.team_id != owner.team_id:
            return False

        # Admin scopes are powerful, but only after current key and owner validation.
        if "admin:*" in stored.scopes:
            return True
        
        # Check scope patterns
        target_scope = f"{resource}:{action}"
        workflow_target = f"{resource}:*"
        
        for scope in stored.scopes:
            if self.scope_matches(scope, target_scope):
                return True
            if self.scope_matches(scope, workflow_target):
                return True
        
        return False
    
    # Workflow ACL
    def set_workflow_acl(
        self,
        workflow_id: str,
        team_id: str,
        public: bool = False,
        allowed_users: list[str] = None,
        allowed_teams: list[str] = None,
    ) -> WorkflowACL:
        """Set access control for a workflow."""
        acl = WorkflowACL(
            workflow_id=workflow_id,
            team_id=team_id,
            public=public,
            allowed_users=allowed_users or [],
            allowed_teams=allowed_teams or [],
        )
        self._workflow_acls[workflow_id] = acl
        return acl
    
    # Token Generation (for sessions)
    def generate_token(self, user: User, expires_hours: int = 24) -> str:
        """Generate a JWT token for a user."""
        stored_user = self._users.get(user.id)
        if (
            stored_user is None
            or stored_user.email != user.email
            or stored_user.team_id != user.team_id
            or stored_user.role != user.role
        ):
            raise PermissionError("Cannot mint a token for an unverified or modified user")

        payload = {
            "user_id": stored_user.id,
            "email": stored_user.email,
            "team_id": stored_user.team_id,
            "role": stored_user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        }
        return jwt.encode(payload, self._get_secret(), algorithm="HS256")
    
    def validate_token(self, token: str) -> Optional[dict]:
        """Validate a JWT token and return payload."""
        try:
            payload = jwt.decode(token, self._get_secret(), algorithms=["HS256"])
            stored_user = self._users.get(payload.get("user_id"))
            if (
                stored_user is None
                or payload.get("email") != stored_user.email
                or payload.get("team_id") != stored_user.team_id
                or payload.get("role") != stored_user.role.value
            ):
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def _generate_id(self) -> str:
        return secrets.token_urlsafe(16)
    
    def _get_secret(self) -> str:
        import os
        secret = os.getenv("SOLVENS_SECRET_KEY")
        if not secret:
            raise RuntimeError("SOLVENS_SECRET_KEY must be configured; refusing insecure JWT fallback")
        return secret
