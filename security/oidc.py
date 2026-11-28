"""OIDC resource-server authentication for SOLVENS APIs.

The identity provider owns authentication. SOLVENS owns authorization.
The signed tenant claim selects a tenant; current membership and roles are
resolved from the database on every protected request.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from solvens.persistence.database import get_session
from solvens.persistence.identity import (
    IdentityResolutionError,
    resolve_durable_principal,
)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    email: str | None = None
    user_id: str | None = None


class OIDCConfigurationError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    issuer = os.getenv("SOLVENS_OIDC_ISSUER", "")
    if not issuer:
        raise OIDCConfigurationError("SOLVENS_OIDC_ISSUER is required")
    jwks_uri = os.getenv("SOLVENS_OIDC_JWKS_URI", "").strip()
    if not jwks_uri:
        raise OIDCConfigurationError("SOLVENS_OIDC_JWKS_URI is required")
    return PyJWKClient(jwks_uri, cache_keys=True, timeout=5)


def verify_access_token(token: str) -> Principal:
    """Validate token cryptographically; returned roles are not authorization."""
    issuer = os.getenv("SOLVENS_OIDC_ISSUER", "")
    audience = os.getenv("SOLVENS_OIDC_AUDIENCE", "").strip()
    jwks_uri = os.getenv("SOLVENS_OIDC_JWKS_URI", "").strip()
    if not issuer or not audience or not jwks_uri:
        raise OIDCConfigurationError(
            "Configure SOLVENS_OIDC_ISSUER, SOLVENS_OIDC_AUDIENCE and "
            "SOLVENS_OIDC_JWKS_URI before exposing protected APIs"
        )
    if urlparse(issuer).scheme != "https" or urlparse(jwks_uri).scheme != "https":
        raise OIDCConfigurationError("OIDC issuer and JWKS endpoints must use HTTPS")
    if not isinstance(token, str) or not token or len(token) > 16384:
        raise PermissionError("Malformed access token")
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token).key
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            leeway=30,
        )
    except (jwt.PyJWTError, OSError, ValueError) as exc:
        raise PermissionError("Invalid access token") from exc

    subject = claims.get("sub")
    tenant_id = claims.get("tenant_id")
    if claims.get("exp", 0) - claims.get("iat", 0) > 3600:
        raise PermissionError("Access token lifetime exceeds one hour")
    if not isinstance(subject, str) or not subject:
        raise PermissionError("Token has no subject")
    if (
        not isinstance(tenant_id, str)
        or not tenant_id
        or len(tenant_id) > 128
        or tenant_id.strip() != tenant_id
    ):
        raise PermissionError("Token has no valid tenant selector")
    # Keep the verified claim for compatibility/diagnostics only. require_principal
    # replaces these roles with database-authoritative membership roles.
    roles_claim = claims.get("solvens_roles", [])
    if isinstance(roles_claim, str):
        roles_claim = [roles_claim]
    allowed_roles = {"viewer", "developer", "editor", "auditor", "admin", "owner"}
    if not isinstance(roles_claim, list) or any(
        not isinstance(role, str) or role.lower() not in allowed_roles
        for role in roles_claim
    ):
        raise PermissionError("Token roles claim is malformed or contains an unknown role")
    return Principal(
        subject=subject,
        tenant_id=tenant_id,
        roles=frozenset(role.lower() for role in roles_claim),
        email=claims.get("email") if isinstance(claims.get("email"), str) else None,
    )


async def _auth_session() -> AsyncIterator[AsyncSession]:
    """Translate missing/broken database configuration into a fail-closed 503."""
    try:
        async for session in get_session():
            yield session
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail="Authorization database is not configured"
        ) from exc


bearer_scheme = HTTPBearer(auto_error=False)


async def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(_auth_session),
) -> Principal:
    if credentials is None:
        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required",
            )
        token = authorization[7:].strip()
    else:
        token = credentials.credentials
    try:
        verified = verify_access_token(token)
    except OIDCConfigurationError as exc:
        raise HTTPException(
            status_code=503, detail="OIDC authentication is not configured"
        ) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc

    issuer = os.getenv("SOLVENS_OIDC_ISSUER", "")
    try:
        durable = await resolve_durable_principal(
            session,
            issuer=issuer,
            subject=verified.subject,
            tenant_id=verified.tenant_id,
        )
    except IdentityResolutionError as exc:
        raise HTTPException(
            status_code=403, detail="No active identity or tenant membership"
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503, detail="Authorization database unavailable"
        ) from exc

    principal = Principal(
        subject=durable.subject,
        tenant_id=durable.tenant_id,
        roles=durable.roles,
        email=verified.email,
        user_id=durable.user_id,
    )
    request.state.principal = principal
    return principal


def principal_from_request(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="Authentication required")
    return principal


def require_role(principal: Principal, *allowed_roles: str) -> None:
    if not principal.roles.intersection({role.lower() for role in allowed_roles}):
        raise HTTPException(status_code=403, detail="Insufficient role")
