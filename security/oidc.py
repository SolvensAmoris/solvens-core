"""OIDC resource-server authentication for SOLVENS APIs.

The identity provider owns authentication. SOLVENS owns authorization.
No role or tenant value from request parameters is trusted.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    email: str | None = None


class OIDCConfigurationError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    issuer = os.getenv("SOLVENS_OIDC_ISSUER", "")
    if not issuer:
        raise OIDCConfigurationError("SOLVENS_OIDC_ISSUER is required")
    jwks_uri = os.getenv("SOLVENS_OIDC_JWKS_URI", "").strip()
    if not jwks_uri:
        # OIDC discovery must be performed by deployment/configuration.
        # Requiring an explicit JWKS URI avoids implicit issuer URL guessing.
        raise OIDCConfigurationError("SOLVENS_OIDC_JWKS_URI is required")
    return PyJWKClient(jwks_uri, cache_keys=True, timeout=5)


def verify_access_token(token: str) -> Principal:
    issuer = os.getenv("SOLVENS_OIDC_ISSUER", "").rstrip("/")
    audience = os.getenv("SOLVENS_OIDC_AUDIENCE", "").strip()
    if not issuer or not audience or not os.getenv("SOLVENS_OIDC_JWKS_URI"):
        raise OIDCConfigurationError(
            "Configure SOLVENS_OIDC_ISSUER, SOLVENS_OIDC_AUDIENCE and "
            "SOLVENS_OIDC_JWKS_URI before exposing protected APIs"
        )
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
    roles_claim = claims.get("solvens_roles", [])
    if claims.get("exp", 0) - claims.get("iat", 0) > 3600:
        raise PermissionError("Access token lifetime exceeds one hour")
    if not isinstance(subject, str) or not subject:
        raise PermissionError("Token has no subject")
    if not isinstance(tenant_id, str) or not tenant_id:
        raise PermissionError("Token has no verified tenant_id claim")
    if isinstance(roles_claim, str):
        roles_claim = [roles_claim]
    if not isinstance(roles_claim, list) or any(not isinstance(r, str) for r in roles_claim):
        raise PermissionError("Token roles claim is malformed")
    return Principal(
        subject=subject,
        tenant_id=tenant_id,
        roles=frozenset(r.lower() for r in roles_claim),
        email=claims.get("email") if isinstance(claims.get("email"), str) else None,
    )


bearer_scheme = HTTPBearer(auto_error=False)


async def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    # FastAPI injects HTTPBearer only when declared as a dependency.
    if credentials is None:
        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
        token = authorization[7:].strip()
    else:
        token = credentials.credentials
    try:
        principal = verify_access_token(token)
    except OIDCConfigurationError as exc:
        raise HTTPException(status_code=503, detail="OIDC authentication is not configured") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc
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
