# ADR-0002: Durable identity, authorization, and multi-worker execution

- Status: Accepted for implementation on security/sec-15-durable-identity-2026-11
- Date: 2026-11-27
- Scope: SEC-15; core API, dashboard API, dashboard web client, worker coordination
- Explicit exclusions: cosmos-web/, public landing pages, Vercel configuration, deployment, and production credentials

## Context

The OIDC resource-server boundary is merged, but identity-to-user mapping, tenant memberships, RBAC records, task ownership, dashboard runs, and WebSocket tickets are process-local. The dashboard has no browser login flow. Multiple API processes therefore cannot safely share authorization or execution state.

The repository already declares SQLAlchemy and aiosqlite as optional storage dependencies and contains a PostgreSQL service in Docker Compose, but it has no canonical persistence models, migration system, or repository layer. Redis is present in Compose but is not currently used as a coordinated task/event system.

## Decisions

### 1. Durable relational source of truth

Use PostgreSQL as the production system of record and SQLAlchemy 2.x async repositories. Use SQLite only for isolated tests where PostgreSQL-specific locking behavior is not under test. Add Alembic migrations; do not use create_all() as a production migration strategy.

Persist at minimum: internal users (immutable UUID, lifecycle state, timestamps); OIDC identities with a unique (issuer, subject) pair; tenants and tenant memberships, including role, status, and revocation timestamps; API-key metadata and scopes (store only a one-way hash of the secret); workflow ACLs; core task ownership and durable task state; dashboard runs and run/task snapshots; one-use, short-lived WebSocket tickets; transactional outbox events for cross-process notifications.

All tenant-owned records must carry a tenant key and use tenant-scoped queries. Add database constraints and indexes for identity uniqueness, membership uniqueness, tenant ownership, ticket expiry, and task claiming.

### 2. OIDC subject mapping and authorization

Treat (iss, sub) as the external identity key. Never use email as an identity key: it is mutable and may be reassigned. Link it to an immutable internal user UUID through an explicit provisioning/invitation or administrator-controlled linking flow. Do not silently create a privileged user or tenant on first login.

The OIDC token proves authentication and audience. It does not independently grant SOLVENS roles. Resolve the subject to an active internal identity, then resolve active tenant membership and roles from PostgreSQL on every protected request (or through a bounded, revocable cache whose invalidation semantics are tested). If identity or membership is absent, suspended, or revoked, fail closed. If a tenant context is supplied, verify it against active memberships; never trust a raw tenant identifier by itself.

Preserve separation between identity, tenant membership, role, permission, and execution. Keep the current role vocabulary only as an application mapping, not as an IdP-specific contract. Record security-sensitive mutations with actor, tenant, target, and timestamp.

### 3. Browser login SDK

Use oidc-client-ts as the provider-neutral OIDC client for the existing Next.js dashboard. Use Authorization Code + PKCE (S256), exact redirect URIs, state and nonce validation, issuer discovery/metadata validation, and a public client with no browser secret. Store tokens in memory where practical; do not place access or refresh tokens in localStorage. Do not expose provider secrets or model-provider API keys to the browser.

The dashboard must obtain an API access token and send it only in the Authorization header. Before opening a WebSocket, it must obtain a one-use ticket through the authenticated API and then connect with that ticket. Logout must clear client state; server-side revocation/suspension must take effect through request-time membership checks. Provider configuration is environment-driven (authority/issuer, client ID, API scope, redirect URI); do not hard-code a vendor.

### 4. Multi-worker task execution and event delivery

PostgreSQL is authoritative for task/run state and ownership. Workers claim queued tasks transactionally using row locks (e.g. FOR UPDATE SKIP LOCKED) and a bounded lease. Persist worker ID, lease expiry, attempt count, heartbeat, and terminal outcome. Expired leases are reclaimable. Use idempotency keys and document execution as at-least-once; external side effects must be idempotent or guarded by durable operation records. Do not claim exactly-once execution.

Use Redis Pub/Sub for low-latency cross-worker event fan-out, not as the source of truth. Persist events/outbox records before publishing. A reconnecting dashboard reads a durable run snapshot and sequence cursor so missed Pub/Sub messages can be recovered. If Redis is unavailable, state remains durable and clients can recover by polling/reconnecting; do not silently lose authorization or ownership state.

WebSocket tickets are cryptographically random, hashed at rest, tenant/user-bound, one-use, and expire quickly. Consume them atomically in PostgreSQL. A ticket must not be reusable on another worker.

## Implementation sequence

1. Establish database configuration, SQLAlchemy models, Alembic baseline, and repository/unit-of-work boundaries.
2. Implement user, tenant, membership, and OIDC identity mapping; add request-time membership resolution and adversarial tenant tests.
3. Persist API keys and ACLs, including hashed key storage and role-change/revocation tests.
4. Persist core task ownership/state and implement a database-backed worker claim/lease protocol.
5. Persist dashboard runs and WebSocket tickets; add outbox plus Redis event fan-out and reconnect recovery.
6. Integrate oidc-client-ts into dashboard/web with PKCE, protected routes, authenticated API calls, and ticket-based WebSockets.
7. Run migrations against PostgreSQL, multi-process integration tests, security regression tests, and full CI.

## Acceptance gates

- A user with the same email but a different OIDC sub cannot inherit another user's account.
- An unknown, suspended, or revoked (iss, sub) cannot access protected resources.
- Tenant A cannot read, mutate, cancel, stream, or receive events for Tenant B.
- Role downgrade and membership revocation take effect without waiting for the original JWT to expire.
- Two or more API/worker processes can claim tasks without duplicate concurrent claims.
- A crashed worker's expired lease is recovered; retries and at-least-once semantics are tested.
- A WebSocket ticket is single-use across processes and cannot cross users or tenants.
- Dashboard login uses PKCE; no client secret or provider API key ships to the browser; tokens are not stored in localStorage.
- Database migration/rollback behavior and PostgreSQL concurrency behavior are tested against PostgreSQL, not inferred from SQLite tests.
- No production readiness claim until IdP configuration, secrets, database, Redis, migration, and operational recovery are actually exercised.

## Risks and non-goals

- Redis Pub/Sub is ephemeral; durable outbox/state and reconnect recovery are mandatory.
- PostgreSQL task claiming prevents concurrent claims, not duplicate external side effects after a worker crash. Idempotency is required.
- This ADR does not choose a commercial IdP. Any standards-compliant OIDC provider supporting Authorization Code + PKCE and the required API audience can be configured.
- This ADR does not authorize merge, deployment, production credentials, or changes to the public landing page.