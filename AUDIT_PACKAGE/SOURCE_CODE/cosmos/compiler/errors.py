from dataclasses import dataclass
from typing import Literal


@dataclass
class CompileError:
    code: str
    phase: Literal["PARSER", "AST", "TEMPORAL", "TOPOLOGY", "FLOW", "CYCLE", "ENGINE"]
    severity: Literal["REJECT", "INTERNAL", "WARNING"]
    message: str
    location: str = ""


class InternalCompileError(Exception):
    """Error interno del compilador. No es culpa del.cosmos"""
    def __init__(self, code: str, phase: str, message: str):
        self.code = code
        self.phase = phase
        self.message = message
        super().__init__(f"[{code}] [{phase}] {message}")
