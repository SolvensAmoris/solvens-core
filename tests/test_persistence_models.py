from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from solvens.persistence.models import (
    Base,
    MembershipRecord,
    OIDCIdentityRecord,
    TenantRecord,
    UserRecord,
)


def test_persistence_schema_has_required_security_tables() -> None:
    expected = {
        "users",
        "tenants",
        "oidc_identities",
        "tenant_memberships",
        "api_keys",
        "workflow_acls",
        "core_tasks",
        "dashboard_runs",
        "websocket_tickets",
        "outbox_events",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_oidc_identity_is_unique_by_issuer_and_subject() -> None:
    table = Base.metadata.tables["oidc_identities"]
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("issuer", "subject") in unique_columns


def test_membership_is_unique_per_user_and_tenant() -> None:
    table = Base.metadata.tables["tenant_memberships"]
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("tenant_id", "user_id") in unique_columns


@pytest.mark.asyncio
async def test_identity_and_membership_persist_with_sqlite() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with factory() as session:
            tenant = TenantRecord(name="tenant-a")
            user = UserRecord(email="same@example.invalid")
            session.add_all([tenant, user])
            await session.flush()
            identity = OIDCIdentityRecord(
                user_id=user.id,
                issuer="https://issuer.example",
                subject="immutable-subject-1",
            )
            membership = MembershipRecord(
                tenant_id=tenant.id,
                user_id=user.id,
                role="viewer",
            )
            session.add_all([identity, membership])
            await session.commit()

        async with factory() as session:
            result = await session.execute(
                select(OIDCIdentityRecord).where(
                    OIDCIdentityRecord.issuer == "https://issuer.example",
                    OIDCIdentityRecord.subject == "immutable-subject-1",
                )
            )
            assert result.scalar_one().user_id == user.id

            session.add(
                OIDCIdentityRecord(
                    user_id=user.id,
                    issuer="https://issuer.example",
                    subject="immutable-subject-1",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        await engine.dispose()
