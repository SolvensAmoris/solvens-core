"""Integration tests for database-authoritative OIDC authorization."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from security.oidc import Principal, require_principal
from solvens.persistence.models import (
    Base,
    MembershipRecord,
    OIDCIdentityRecord,
    TenantRecord,
    UserRecord,
)


def _request() -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/protected",
        "query_string": b"",
        "headers": [],
        "server": ("test", 80),
        "client": ("test", 1),
        "scheme": "http",
    })


@pytest.mark.asyncio
async def test_require_principal_replaces_token_roles_with_database_roles():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            user = UserRecord(status="active")
            tenant = TenantRecord(name="tenant-a", status="active")
            session.add_all([user, tenant])
            await session.flush()
            session.add_all([
                OIDCIdentityRecord(
                    user_id=user.id,
                    issuer="https://issuer.example/",
                    subject="stable-subject",
                    status="active",
                ),
                MembershipRecord(
                    user_id=user.id,
                    tenant_id=tenant.id,
                    role="viewer",
                    status="active",
                ),
            ])
            await session.commit()

            # The signed token contains a stale, overprivileged role.
            with patch(
                "security.oidc.verify_access_token",
                return_value=Principal(
                    "stable-subject", tenant.id, frozenset({"owner"})
                ),
            ), patch.dict(
                "os.environ", {"SOLVENS_OIDC_ISSUER": "https://issuer.example/"}
            ):
                principal = await require_principal(
                    _request(),
                    HTTPAuthorizationCredentials(
                        scheme="Bearer", credentials="valid-test-token"
                    ),
                    session,
                )

            assert principal.user_id == user.id
            assert principal.tenant_id == tenant.id
            assert principal.roles == frozenset({"viewer"})
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_require_principal_rejects_revoked_membership():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            user = UserRecord(status="active")
            tenant = TenantRecord(name="tenant-a", status="active")
            session.add_all([user, tenant])
            await session.flush()
            session.add_all([
                OIDCIdentityRecord(
                    user_id=user.id,
                    issuer="https://issuer.example/",
                    subject="stable-subject",
                    status="active",
                ),
                MembershipRecord(
                    user_id=user.id,
                    tenant_id=tenant.id,
                    role="owner",
                    status="revoked",
                ),
            ])
            await session.commit()
            with patch(
                "security.oidc.verify_access_token",
                return_value=Principal(
                    "stable-subject", tenant.id, frozenset({"owner"})
                ),
            ), patch.dict(
                "os.environ", {"SOLVENS_OIDC_ISSUER": "https://issuer.example/"}
            ):
                with pytest.raises(HTTPException) as error:
                    await require_principal(
                        _request(),
                        HTTPAuthorizationCredentials(
                            scheme="Bearer", credentials="valid-test-token"
                        ),
                        session,
                    )
            assert error.value.status_code == 403
    finally:
        await engine.dispose()
