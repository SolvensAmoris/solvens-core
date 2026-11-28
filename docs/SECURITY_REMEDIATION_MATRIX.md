# Security remediation matrix

Baseline scanner report: commit `89f4c7c65d45c84d386ec48438f5d2d1c67e2c06` (2026-11-28).
Working branch: `security/remediation-oss-scan-2026-11`.

This matrix distinguishes source confirmation from runtime reproduction. A scanner finding is not treated as an exploit until its preconditions and impact are reproduced.

| ID | Finding / evidence | Risk | Intervention | Status / acceptance evidence |
|---|---|---:|---|---|
| SEC-01 | Unsafe `eval(line)` in `solvens/plugins/ollama/__init__.py`; duplicate in `AUDIT_PACKAGE/SOURCE_CODE/...` | High | Parse each line with `json.loads`; reject non-object chunks. Keep the audit snapshot synchronized. | Canonical implementation changed. Regression test pending. |
| SEC-02 | Duplicate `PIICategory.API_KEY` key in `security/pii_redaction.py`; AWS matcher overwrote generic matcher | Medium | One combined API-key matcher for generic and AWS formats. | Implemented in source; tests pending. |
| SEC-03 | `PIIAwareLLMWrapper` only redacted user string content; nested data was not consistently traversed; `PIIMatch` has no `metadata` field | Medium | Redact user/tool message content recursively across strings, dicts, lists and tuples; remove invalid mutation of match objects. | Implemented in source; tests pending. System/developer messages remain untouched by policy. |
| SEC-04 | `security/audit.py`: incorrect column indexes, timestamp-based chain ordering, incomplete hash coverage, process-local chain tip | Medium | Verify in insertion order; correct SQLite column mapping; hash all event fields and metadata; serialize writers with `BEGIN IMMEDIATE` and read the tip inside the transaction. | Implemented in source; integrity/tamper and concurrency tests pending. Existing database chains created with the old hash definition may require migration/re-baselining. |
| SEC-05 | `security/rbac.py`: role map referenced enum attributes that do not exist; OWNER/ADMIN bypassed ACL tenant boundary | Medium | Build role sets explicitly; validate stored user identity/team and ACL tenant before privileged bypass. | Implemented in source; import and cross-tenant tests pending. |
| SEC-06 | `security/rbac.py`: public JWT fallback secret | Medium | Fail closed if `SOLVENS_SECRET_KEY` is absent. | Implemented in source; environment/configuration test pending. |
| SEC-07 | `solvens/api/main.py`: `structlog` referenced without import; wildcard CORS with credentials | Medium/Low | Import logger dependency; default to no allowed origins and require explicit `SOLVENS_CORS_ORIGINS`. Restrict methods/headers. | Implemented in source; app startup/CORS tests pending. |
| SEC-08 | `solvens/api/main.py`: API routes have no authentication/authorization boundary | Medium | Requires an explicit identity/authentication contract, token issuer, protected-route policy, and health/docs exceptions. | OPEN. Not patched with a fabricated or bypassable auth mechanism. |
| SEC-09 | RBAC mutators lack actor authorization contract | Medium | Add actor-aware authorization at service boundary; define bootstrap/owner-transfer semantics before changing signatures. | OPEN. Existing APIs do not supply a trustworthy actor context. |
| SEC-10 | `cosmos/visualizer/dag_renderer.py`: unescaped node/edge labels and graph title enter SVG/HTML | Low | HTML/XML escape untrusted labels and metadata before interpolation. | Implemented in source; injection regression test pending. |
| SEC-11 | Cosmos parser mutates collections during iteration; forward references/parent edges incomplete | Low | Rework parser in a dedicated change with fixtures for forward refs, duplicate edges and malformed graphs. | OPEN; exact current parser path and behavior need test-backed confirmation. |
| SEC-12 | Temporal/cycle validation has last-value-wins and incomplete destination matching | Low | Replace global overwrite with per-node/per-edge validation and exhaustive reference parsing. | OPEN; needs fixtures and semantic contract. |
| SEC-13 | Dashboard API/WebSocket lacks auth and tenant scoping; wildcard CORS | Low | Apply same identity and tenant boundary as SEC-08; do not ship isolated route-level checks. | OPEN, coupled to SEC-08. |
| SEC-14 | API copy under `AUDIT_PACKAGE/SOURCE_CODE` is a duplicate snapshot, not the runtime source | Medium | Regenerate or explicitly mark snapshot as archival after canonical changes; scan canonical runtime tree separately. | OPEN; package provenance and regeneration workflow need confirmation. |

## Ordered intervention

1. Remove code execution from provider parsing (SEC-01).
2. Restore authorization invariants and remove insecure signing defaults (SEC-05, SEC-06).
3. Repair PII coverage and fail-safe behavior (SEC-02, SEC-03).
4. Restore audit-chain integrity and serialized writes (SEC-04).
5. Restore API module startup and tighten cross-origin defaults (SEC-07), then design authentication as a separate contract (SEC-08, SEC-09, SEC-13).
6. Escape rendered graph data (SEC-10).
7. Repair parser and temporal validation with fixture-driven tests (SEC-11, SEC-12).
8. Reconcile the audit snapshot and run full regression plus a fresh independent scan (SEC-14).

## Verification rule

No item is marked accepted until a regression test demonstrates the intended behavior. Static edits alone are not proof of exploitability removed. Runtime tests, migration compatibility, and a fresh scan are still required before merge or deployment.
