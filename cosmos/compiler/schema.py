from typing import Dict, Any, List
from cosmos.compiler.errors import CompileError


REQUIRED_TOP_LEVEL = {
    "universe": str,
    "metadata": dict,
    "sun": str,
}


def validate_ast_schema(ast: Dict[str, Any]) -> List[CompileError]:
    errors = []
    for key, expected_type in REQUIRED_TOP_LEVEL.items():
        if key not in ast:
            errors.append(CompileError(
                code="E001",
                phase="AST",
                severity="REJECT",
                message=f"Missing required field: {key}"
            ))
            continue
        if not isinstance(ast[key], expected_type):
            errors.append(CompileError(
                code="E002",
                phase="AST",
                severity="REJECT",
                message=f"Invalid type for {key}: expected {expected_type.__name__}"
            ))
    return errors
