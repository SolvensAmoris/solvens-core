"""
cosmos/compiler/errors.py
========================

Error definitions for Cosmos compiler.
RFC-0004-F: Temporal Constraint Validation

Error codes:
- E1xx: Syntax errors
- E2xx: Semantic errors
- E4xx: Temporal constraint errors (RFC-0004-F)
- E5xx: Validation errors
"""

from dataclasses import dataclass
from typing import Literal
from enum import Enum


# ============================================================
# ERROR CODES
# ============================================================

class ErrorCode(str, Enum):
    """Códigos de error para Cosmos compiler."""
    
    # Syntax errors (E1xx)
    E100 = "SyntaxError"
    E101 = "InvalidUniverse"
    E102 = "InvalidNodeType"
    E103 = "UnclosedBlock"
    E104 = "InvalidProperty"
    
    # Semantic errors (E2xx)
    E200 = "DuplicateNode"
    E201 = "UndefinedReference"
    E202 = "CircularDependency"
    E203 = "InvalidConnection"
    
    # Temporal constraint errors (E4xx) - RFC-0004-F
    E400 = "TemporalConstraintError"
    E401 = "TemporalConstraintViolation"  # FAIL-FAST REQUIRED
    E402 = "TemporalCycleDetected"
    E403 = "InvalidTemporalOrder"
    E404 = "DurationExceeded"
    E405 = "TemporalInconsistency"
    
    # Validation errors (E5xx)
    E500 = "ValidationError"
    E501 = "SchemaViolation"
    E502 = "TypeMismatch"
    
    # Internal errors (E9xx)
    E900 = "InternalError"
    E901 = "CompilerError"
    E902 = "ParserError"


# Error code constants for convenience
E100 = ErrorCode.E100.value
E101 = ErrorCode.E101.value
E102 = ErrorCode.E102.value
E103 = ErrorCode.E103.value
E200 = ErrorCode.E200.value
E201 = ErrorCode.E201.value
E202 = ErrorCode.E202.value
E400 = ErrorCode.E400.value
E401 = ErrorCode.E401.value  # RFC-0004-F: FAIL-FAST
E402 = ErrorCode.E402.value
E403 = ErrorCode.E403.value
E500 = ErrorCode.E500.value
E501 = ErrorCode.E501.value


# ============================================================
# ERROR CLASSES
# ============================================================

@dataclass
class CompileError:
    code: str
    phase: Literal["PARSER", "AST", "TEMPORAL", "TOPOLOGY", "FLOW", "CYCLE", "ENGINE"]
    severity: Literal["REJECT", "INTERNAL", "WARNING"]
    message: str
    location: str = ""


class InternalCompileError(Exception):
    """Error interno del compilador. No es culpa del cosmos."""
    def __init__(self, code: str, phase: str, message: str):
        self.code = code
        self.phase = phase
        self.message = message
        super().__init__(f"[{code}] [{phase}] {message}")


class TemporalConstraintViolation(Exception):
    """
    Violación de restricción temporal.
    
    RFC-0004-F: Fail-Fast
    
    Esta excepción indica una violación de las restricciones
    temporales definidas en el código Cosmos.
    """
    def __init__(
        self,
        message: str,
        start_after: int = None,
        end_before: int = None,
        duration: int = None,
        details: dict = None
    ):
        self.error_code = E401
        self.start_after = start_after
        self.end_before = end_before
        self.duration = duration
        self.details = details or {}
        
        full_message = f"[{E401}] {message}"
        if start_after and end_before:
            full_message += f" (start_after={start_after}, end_before={end_before})"
        
        super().__init__(full_message)
