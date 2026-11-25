"""
cosmos/compiler/errors.py
=========================

Canonical error catalog for the Cosmos compiler.
RFC-0004-F (rewritten 2026-11-25), section 8.

One code, one meaning, everywhere. The old enum reused codes with
different meanings (E101 was "InvalidUniverse" here and
"DuplicateIdentifier" in the RFC; E401 was "TemporalConstraintViolation"
here and "FlowAuthorizationExpired" in the RFC). That is gone.

Codes:
- P001-P015: parser errors (RFC-0005, as defined in cosmos-topology lib.rs)
- E001-E007: topology errors
- E101-E112: structural errors
- E401, E403-E405: temporal / cycle errors
- W001:     temporal warning (lax mode)
- CT001-CT005: contract errors (RFC-0008)
- C001-C010: CIR errors (reserved, RFC-0007 pending)
- E998:     internal compiler error (not a user error)
"""

from dataclasses import dataclass
from typing import Literal


# ============================================================
# CANONICAL CODE TABLES (name -> code)
# ============================================================

PARSER_ERRORS = {
    "UnexpectedToken": "P001",
    "UnexpectedEOF": "P002",
    "MissingUniverse": "P003",
    "MissingMetadata": "P004",
    "MissingSun": "P005",
    "MissingPosition": "P006",
    "MissingMass": "P007",
    "MissingType": "P008",
    "InvalidIdentifier": "P009",
    "InvalidNumber": "P010",
    "InvalidString": "P011",
    "SunPositionOverride": "P012",
    "DuplicateEntity": "P013",
    "UnknownBlock": "P014",
    "InvalidFlowType": "P015",
}

TOPOLOGY_ERRORS = {
    "OrbitViolation": "E001",
    "MassCollision": "E002",
    "LightPathTooLong": "E003",
    "SpaghettiTensionExceeded": "E004",
    "InvalidCoordinates": "E005",
    "BidirectionalLightForbidden": "E006",
    "DeepSpaceViolation": "E007",
}

STRUCTURAL_ERRORS = {
    "DuplicateIdentifier": "E101",
    "MissingRequiredField": "E102",
    "InvalidEntityReference": "E103",
    "InvalidMetadata": "E104",
    "SunOrStarAsReceiver": "E105",
    "SatelliteScopeViolation": "E106",
    "GalaxyInCore": "E107",
    "MultipleSun": "E108",
    "FlowMatrixViolation": "E109",
    "OrbitTypeMismatch": "E110",
    "SatelliteMassRatioExceeded": "E111",
    "EmptyUniverse": "E112",
}

TEMPORAL_ERRORS = {
    "FlowAuthorizationExpired": "E401",
    "CrossGalaxyAccess": "E403",
    "FlowCycle": "E404",
    "MalformedDate": "E405",
    "TemporalAccessExpired": "W001",
}

CONTRACT_ERRORS = {
    "ContractNotFound": "CT001",
    "ContractMismatch": "CT002",
    "PurityViolation": "CT003",
    "SignatureMismatch": "CT004",
    "ImportWithoutContract": "CT005",
}


# ============================================================
# ERROR CLASSES
# ============================================================

@dataclass
class CompileError:
    code: str
    phase: Literal["PARSER", "AST", "TOPOLOGY", "TEMPORAL"]
    severity: Literal["REJECT", "WARNING"]
    message: str
    location: str = ""


class InternalCompileError(Exception):
    """Internal compiler error. Not the user's fault (E998)."""

    def __init__(self, code: str, phase: str, message: str):
        self.code = code
        self.phase = phase
        self.message = message
        super().__init__(f"[{code}] [{phase}] {message}")


class ParseFailure(Exception):
    """A parser-class failure found after Lark parsing (P-code)."""

    def __init__(self, code: str, message: str, location: str = ""):
        self.code = code
        self.message = message
        self.location = location
        super().__init__(f"[{code}] {message}")


class TemporalConstraintViolation(Exception):
    """
    Temporal constraint violation (E401).

    RFC-0004-F section 6: a flow whose restringido_hasta has passed
    is blocked. Kept for compatibility with GatedCosmosExecutor,
    which raises E401Block from this code.
    """

    def __init__(self, message: str, details: dict | None = None):
        self.error_code = "E401"
        self.details = details or {}
        super().__init__(f"[E401] {message}")
