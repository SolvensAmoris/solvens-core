# OIDC authentication and tenant boundary

SOLVENS APIs are OIDC resource servers. The identity provider authenticates users; SOLVENS validates access tokens and enforces application authorization. No local password store or vendor-specific login flow is introduced.

## Required deployment configuration

Set these environment variables in the API and dashboard runtimes:

- `SOLVENS_OIDC_ISSUER`: exact HTTPS issuer URL from the trusted OIDC provider.
- `SOLVENS_OIDC_AUDIENCE`: audience issued specifically for the SOLVENS API.
- `SOLVENS_OIDC_JWKS_URI`: HTTPS JWKS endpoint published by that issuer.
- `SOLVENS_CORS_ORIGINS`: comma-separated exact browser origins; never use `*` with credentials.
- `SOLVENS_RBAC_BOOTSTRAP_TOKEN`: high-entropy bootstrap secret used to create the initial tenant and first OWNER.
- `SOLVENS_SECRET_KEY`: at least 32 random bytes for legacy internal Cosmos RBAC JWT issuance; OIDC API validation does not use this secret.

Do not start protected services with a shared static API token. If OIDC settings are absent, protected HTTP routes return 503; invalid or missing bearer tokens return 401.

## Access-token contract

The provider must issue signed access tokens with:

- `iss`: exact configured issuer.
- `aud`: configured SOLVENS API audience.
- `sub`: stable, non-reassigned subject identifier.
- `exp` and `iat`: short lifetime; SOLVENS rejects lifetimes over one hour.
- `tenant_id`: current, server-authorized tenant membership.
- `solvens_roles`: array of application roles: `viewer`, `developer`, `editor`, `auditor`, `admin`, `owner`.

Only RS256 and ES256 are accepted. The JWKS URI is configured explicitly; arbitrary token-provided key URLs are never followed. The tenant and role claims must be generated from current IdP-side membership/entitlement records, not copied from user-editable profile fields or request headers. Use Authorization Code + PKCE for browser/native user sign-in. Use Client Credentials or workload identity for non-human services, with a distinct service principal and least-privilege role.

The browser must never receive provider API secrets. Keep Anthropic and other model-provider credentials exclusively in server-side secret storage.

## Dashboard WebSockets

The browser first calls authenticated `POST /api/auth/ws-ticket`, then connects to `/ws/run/{run_id}?ticket=...`. The ticket is single-use and expires after 30 seconds. It is not an access token. The server binds the ticket to the verified tenant and rejects a run belonging to another tenant.

Tickets and dashboard run state are currently process-local. Run one dashboard worker per isolated process until shared transactional storage is implemented; do not assume tickets or run ownership survive restarts or coordinate across workers.

## RBAC bootstrap and mutation

Create the initial tenant and first RBAC user (which must be an OWNER) with `SOLVENS_RBAC_BOOTSTRAP_TOKEN` before normal provisioning. Subsequent user creation and workflow ACL changes require an authoritative OWNER/ADMIN actor in the same tenant. ADMIN cannot grant ADMIN or OWNER. API-key creation/revocation requires an authenticated owner of the key or an authorized tenant administrator. Tenant creation remains a platform bootstrap operation.

Both `security.RBACManager` and the primary `cosmos.security.RBAC` implementation are in-memory. Their bootstrap and actor checks close unauthenticated mutation paths in these managers, but they do not replace persistent identity/membership storage. Before multi-instance production use, persist users, memberships, API keys and ACLs transactionally and map OIDC `sub` to an immutable internal principal. The core API task-to-tenant ownership map is also process-local, so run a single worker until that mapping moves into shared durable storage.

## Operational requirements

1. Configure an IdP application with the exact API audience and custom claims above.
2. Use HTTPS end-to-end and store configuration/secrets in the deployment secret manager.
3. Use access tokens around 5-15 minutes where the IdP supports it; the API's one-hour cap is a hard ceiling, not a target.
4. Configure exact CORS origins.
5. Test two tenants and verify list, read, run, metrics and WebSocket access cannot cross tenant boundaries.
6. Rotate provider/service credentials and disable compromised credentials promptly.

This change provides token verification and tenant checks at the API boundary. It does not claim persistent RBAC, cross-worker state sharing, database row-level security, or immediate JWT revocation.
