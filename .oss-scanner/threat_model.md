# SOLVENS CORE threat model

## Project purpose and security boundary

SOLVENS CORE is a Python-based orchestration platform for AI agents and workflows. Its repository also contains the Cosmos DSL/compiler, DAG and task execution components, provider integrations, API/CLI surfaces, security utilities, SDKs, and web/dashboard components.

The security-relevant boundary is any path by which externally controlled data can influence parsing, validation, workflow planning, routing, execution, provider requests, persistence, authorization, or returned output.

## Untrusted inputs and attacker positions

Treat the following as adversarial unless validation is demonstrated in the code:

- Cosmos DSL files, workflow definitions, serialized state, and imported project artifacts.
- HTTP request bodies, query/path parameters, headers, callback values, and task descriptions.
- Data returned by LLM providers, plugins, tools, web services, and other external integrations.
- User-controlled configuration, environment-derived values, file paths, identifiers, and metadata.
- Inputs supplied by authenticated low-privilege users or users in another tenant/team.
- Malformed, oversized, deeply nested, or intentionally ambiguous data.

Consider unauthenticated remote attackers where a network-facing route is reachable without an authentication layer, authenticated users attempting privilege escalation, malicious workflow authors, compromised providers/plugins, and cross-tenant attackers.

## Components in scope

Review the complete checked-out repository. Prioritize:

1. cosmos/: lexer/parser, AST, compiler, validators, canonicalization, serialization, execution/runtime and DSL boundaries.
2. solvens/: API, CLI, orchestrator, agents, router, provider adapters, task lifecycle, configuration and state handling.
3. security/ and cosmos/security/: RBAC, API-key/token handling, audit logging, PII redaction and security helpers.
4. tests/: use existing tests and add focused regression tests when practical.
5. sdk/, dashboard/, studio/, web/, cosmos-web/, vscode-extension/, enterprise/, hub/, and deployment/configuration files: inspect security boundaries and unsafe integration patterns. These are not all built by the Python test command.
6. Dockerfiles, Compose files, GitHub Actions, scripts, examples, and configuration templates.

The root Docker build installs the Python API/storage/test dependencies. The optional vector/ML extra is not installed because it pulls a large model stack; its source remains in scope for static analysis, but runtime tests that require that extra cannot be assumed available. Frontend subprojects have their own package manifests and are not built by the root Python test command.

## High-value vulnerability classes

Look for exploitable issues including:

- Unauthenticated or incorrectly authorized operations, broken role/scope checks, privilege escalation, and tenant isolation failures.
- Command/code injection, unsafe dynamic evaluation, arbitrary file read/write, path traversal, unsafe deserialization, and arbitrary code execution.
- SSRF, unsafe URL/callback handling, request smuggling, insecure provider/plugin boundaries, and credential leakage.
- Secrets exposed in logs, errors, telemetry, API responses, audit records, or generated artifacts.
- PII leakage or redaction bypasses, including malformed and Unicode inputs.
- Resource exhaustion through unbounded recursion, payload size, concurrency, retries, graph expansion, or expensive parsing.
- Integrity failures in workflow validation, execution gating, audit chains, and security-relevant state transitions.

## Severity guidance

- Critical: unauthenticated or broadly reachable compromise, arbitrary code execution, or cross-tenant compromise with severe impact.
- High: reliable privilege escalation, sensitive data/credential exposure, significant authorization bypass, or remotely triggerable code execution requiring limited preconditions.
- Medium: meaningful confidentiality, integrity, or availability impact with material preconditions or restricted reachability.
- Low: limited impact, defense-in-depth weakness, or issue requiring unusually strong preconditions.
- Informational: hardening advice without a demonstrated security impact.

State the attacker position, prerequisites, reachable entry point, affected configuration/version, impact, and evidence. Do not inflate severity based only on a theoretical worst case.

## Testing and proof

The maintained Python regression suite is python -m pytest tests/ -q. The Docker build also compiles cosmos, solvens, and security. The image is intended to support repeat execution with networking disabled.

Prefer minimal, deterministic proof-of-concept inputs that run locally and do not contact third-party systems. Add regression tests for confirmed findings. Distinguish a demonstrated exploit from a plausible but unverified hypothesis.

## Scope discipline

Audit first-party code in this repository. Do not report an upstream dependency vulnerability as a SOLVENS CORE vulnerability unless first-party code introduces the unsafe use or a reachable vulnerable configuration. Avoid duplicate findings for archived snapshots or generated copies when the same root cause is already reported in the canonical implementation. Do not treat stylistic issues, missing features, or deployment assumptions as vulnerabilities without a concrete security consequence.

Do not assume that a control is effective merely because it is named RBAC, audit logging, PII redaction, sandboxing, or verification. Verify the actual enforcement path.
