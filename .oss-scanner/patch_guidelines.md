# SOLVENS CORE patch guidelines

## Patch scope

- Prefer the smallest complete fix for the demonstrated root cause.
- Fix the shared enforcement point when multiple call sites rely on the same unsafe behavior.
- Avoid unrelated refactoring, public API changes, dependency upgrades, or formatting churn.
- Preserve documented behavior and compatibility unless the vulnerability requires a breaking change; explain any unavoidable change.

## Security properties

- Enforce validation and authorization at the server-side trust boundary, not only in callers or UI code.
- Fail closed for security decisions. Do not convert malformed or unverifiable input into an authorized/success state.
- Avoid logging credentials, tokens, raw sensitive payloads, or unnecessary personal data.
- Do not add new network calls or runtime dependencies unless essential to the fix.

## Tests

- Add a deterministic regression test that fails before the fix and passes after it.
- Test both the malicious input and relevant benign behavior.
- Cover authorization boundaries and negative cases where applicable.
- Keep tests runnable offline with the repository's existing test command: python -m pytest tests/ -q.
- Do not weaken, skip, or delete existing tests to make a patch pass.

## Delivery

- Keep each patch focused on one root cause.
- Explain the security invariant restored and list the tests run.
- Do not include secrets, generated binaries, unrelated lockfile churn, or broad cleanup.
