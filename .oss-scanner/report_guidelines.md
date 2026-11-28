# SOLVENS CORE vulnerability report guidelines

## Layout

Write one report per distinct root cause. Use these sections in order:

1. Title and severity
2. Summary
3. Affected component, file, and line range
4. Attacker position and prerequisites
5. Reachable entry point and execution path
6. Reproduction steps or a minimal proof of concept
7. Security impact and severity rationale
8. Affected versions/configurations
9. Suggested remediation
10. Regression-test recommendation

## Evidence standard

- Identify the exact first-party code path and explain how attacker-controlled data reaches the flaw.
- Separate observed behavior from assumptions. State clearly when exploitability is not demonstrated.
- Include commands and inputs needed to reproduce locally. Do not rely on access to production systems or third-party services.
- Explain whether authentication, authorization, tenant boundaries, or user interaction are required.
- Identify duplicate symptoms that share the same underlying root cause.

## Style

Use concise, technically precise language. Prefer plain text and short code blocks over large tables. Avoid generic security advice, speculative impact, and severity inflation. Do not include real secrets, personal data, or destructive proof-of-concept steps.
