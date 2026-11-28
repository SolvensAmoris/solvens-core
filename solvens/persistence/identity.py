"""Database-authoritative OIDC identity and tenant membership resolution.

JWT validation proves who authenticated. This module resolves that external
identity to an internal user and current tenant authorization on every request.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solvens.persistence.models import (
    MembershipRecord,
    OIDCIdentityRecord,
    TenantRecord,
    UserRecord,
)


class IdentityResolutionError(PermissionError):
    """Raised when an authenticated external identity has no active authority."""


@dataclass(frozen=True)
class DurablePrincipal:
    user_id: str
    subject: str
    issuer: str
    tenant_id: str
    roles: frozenset[str]


async def resolve_durable_principal(
    session: AsyncSession,
    *,
    issuer: str,
    subject: str,
    tenant_id: str,
) -> DurablePrincipal:
    """Resolve (issuer, sub) and an explicitly selected active membership.

    Email and token role claims are deliberately not consulted. Unknown,
    disabled, or revoked records fail closed. The caller owns the transaction.
    """
    if not issuer or not subject or not tenant_id:
        raise IdentityResolutionError("A verified issuer, subject, and tenant are required")

    statement = (
        select(UserRecord, OIDCIdentityRecord, TenantRecord, MembershipRecord)
        .join(OIDCIdentityRecord, OIDCIdentityRecord.user_id == UserRecord.id)
        .join(MembershipRecord, MembershipRecord.user_id == UserRecord.id)
        .join(TenantRecord, TenantRecord.id == MembershipRecord.tenant_id)
        .where(
            OIDCIdentityRecord.issuer == issuer,
            OIDCIdentityRecord.subject == subject,
            OIDCIdentityRecord.status == "active",
            UserRecord.status == "active",
            TenantRecord.id == tenant_id,
            TenantRecord.status == "active",
            MembershipRecord.status == "active",
            MembershipRecord.revoked_at.is_(None),
        )
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise IdentityResolutionError("Identity or active tenant membership not found")

    user, identity, tenant, membership = row
    allowed_roles = {"viewer", "developer", "editor", "auditor", "admin", "owner"}
    role = membership.role.lower()
    if role not in allowed_roles:
        raise IdentityResolutionError("Membership contains an unknown role")
    return DurablePrincipal(
        user_id=user.id,
        subject=identity.subject,
        issuer=identity.issuer,
        tenant_id=tenant.id,
        roles=frozenset({role}),
    )
