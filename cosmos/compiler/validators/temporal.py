import datetime
from typing import Dict, Any, List
from cosmos.compiler.errors import CompileError


def verify_temporal_restrictions(ast: Dict[str, Any], strict: bool = True) -> List[CompileError]:
    errors = []
    lights = ast.get("lights", [])
    current_date = datetime.date(2026, 7, 13)


    for index, light in enumerate(lights):
        expiry_str = light.get("restringido_hasta")
        if expiry_str:
            try:
                expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
                if current_date > expiry_date:
                    error_msg = f"Flow validity period has expired. Limit was {expiry_str}, current reference is 2026-07-13."
                    loc_path = f"universe.light_{index}[{light.get('from')}->{light.get('to')}]"
                    errors.append(CompileError(
                        code="E401",
                        phase="TEMPORAL",
                        severity="REJECT",
                        message=error_msg,
                        location=loc_path
                    ))
                    if strict:
                        return errors
            except ValueError:
                errors.append(CompileError(
                    code="E405",
                    phase="TEMPORAL",
                    severity="REJECT",
                    message=f"Malformed date signature target '{expiry_str}' encountered.",
                    location=f"universe.light_{index}"
                ))
                if strict:
                    return errors
    return errors
