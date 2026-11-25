"""
cosmos/compiler/schema.py
=========================

Schema phase (RFC-0004-F rewritten 2026-11-25).

Fixes vs the old schema:
- The old schema reused E001/E002 (OrbitViolation / MassCollision) for
  "missing field" and "wrong type". Those codes mean something else.
  Schema failures now report the parser codes that name them:
  P003 MissingUniverse, P004 MissingMetadata, P005 MissingSun,
  P012 SunPositionOverride, E104 InvalidMetadata.
- The old schema required "sun" to be a str. Suns are now a list
  (grammar allows sun* so a second Sun is E108 in the topology phase).
"""

from typing import Any, Dict, List

from cosmos.compiler.errors import CompileError


def validate_ast_schema(ast: Dict[str, Any]) -> List[CompileError]:
    errors: List[CompileError] = []

    if not ast.get("universe"):
        errors.append(CompileError(
            code="P003",
            phase="AST",
            severity="REJECT",
            message="Missing 'universe' declaration",
        ))
        return errors

    metadata = ast.get("metadata") or {}
    if not metadata:
        errors.append(CompileError(
            code="P004",
            phase="AST",
            severity="REJECT",
            message="Missing 'metadata' block",
        ))
    else:
        for field in ("version", "author", "standard"):
            if field not in metadata:
                errors.append(CompileError(
                    code="E102",
                    phase="AST",
                    severity="REJECT",
                    message=f"Missing required metadata field: '{field}'",
                ))
        if metadata.get("standard") not in (None, "Cosmos"):
            errors.append(CompileError(
                code="E104",
                phase="AST",
                severity="REJECT",
                message=(
                    f"Invalid metadata: standard must be \"Cosmos\", "
                    f"got \"{metadata.get('standard')}\""
                ),
            ))

    suns = ast.get("suns") or []
    if not suns:
        errors.append(CompileError(
            code="P005",
            phase="AST",
            severity="REJECT",
            message="Missing 'sun' declaration",
        ))
    for sun in suns:
        if sun.get("has_position"):
            errors.append(CompileError(
                code="P012",
                phase="AST",
                severity="REJECT",
                message=f"Sun '{sun.get('name')}' cannot have a declared position (G-001)",
            ))

    return errors
