"""
cosmos/compiler/validators/temporal.py
======================================

Temporal restriction validation (RFC-0004-F section 6, rewritten 2026-11-25).

Fix vs the old validator: the "current date" was hardcoded to
2026-07-13, so a flow expiring after that date never expired. The
comparison now uses the real current date.

- strict mode: an expired flow is E401 (REJECT, blocks compilation).
- lax mode: an expired flow is W001 (WARNING, compilation continues).
- A malformed date is E405 in strict mode, a warning in lax mode.
"""

import datetime
from typing import Any, Dict, List

from cosmos.compiler.errors import CompileError


def verify_temporal_restrictions(
    ast: Dict[str, Any], strict: bool = True
) -> List[CompileError]:
    errors: List[CompileError] = []
    lights = ast.get("lights", [])
    current_date = datetime.date.today()

    for index, light in enumerate(lights):
        expiry_str = light.get("restringido_hasta")
        if not expiry_str:
            continue
        loc = f"universe.light_{index}[{light.get('from')}->{light.get('to')}]"
        try:
            expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            errors.append(CompileError(
                code="E405",
                phase="TEMPORAL",
                severity="REJECT" if strict else "WARNING",
                message=f"Malformed date signature target '{expiry_str}' encountered.",
                location=loc,
            ))
            if strict:
                return errors
            continue
        if current_date > expiry_date:
            errors.append(CompileError(
                code="E401" if strict else "W001",
                phase="TEMPORAL",
                severity="REJECT" if strict else "WARNING",
                message=(
                    f"Flow validity period has expired. "
                    f"Limit was {expiry_str}, current date is {current_date.isoformat()}."
                ),
                location=loc,
            ))
            if strict:
                return errors
    return errors
