"""
cosmos/compiler/__main__.py
===========================

Cosmos topology compiler (RFC-0004-F rewritten 2026-11-25).

Grammar (Lark, LALR). Changes vs the old grammar:
- Comments // and /* */ are ignored.
- References use AT_ID ("@id" attached). The Sun is referenced by its
  bare name (the single G-002 exception: it is unique).
- Added: star, nebula, satellite (inside its parent planet), type,
  usa. mass and type are required (grammar enforces presence).
- sun* / galaxy* / metadata? are optional in the grammar so a missing
  Sun / galaxy / metadata is reported with its proper code (P005 /
  E112 / P004) instead of a generic parse error.

Pipeline: PARSE -> SCHEMA -> TOPOLOGY -> TEMPORAL -> VALID.
- strict (default): the first phase with REJECT errors stops the
  compilation (exit 1). Warnings (E004, and everything in lax mode)
  never block.
- lax (--lax): all findings are warnings; compilation continues and
  exits 0 unless parsing itself fails.
Exit codes: 0 = VALID, 1 = rejected, 2 = parse/internal error.
"""

import json
import sys

from lark import Lark, UnexpectedEOF, UnexpectedInput

from cosmos.compiler.errors import InternalCompileError, ParseFailure
from cosmos.compiler.schema import validate_ast_schema
from cosmos.compiler.transformer import CosmosTransformer
from cosmos.compiler.validators.temporal import verify_temporal_restrictions
from cosmos.compiler.validators.topology import verify_topology

GRAMMAR = r"""
start: universe
universe: "universe" STRING "{" metadata? sun* star* galaxy* light* "}"
metadata: "metadata" "{" version? author? standard? "}"
version: "version:" STRING
author: "author:" STRING
standard: "standard:" STRING
sun: "sun" IDENTIFIER
   | "sun" IDENTIFIER "{" position "}"
star: "star" STRING AT_ID "{" "value:" value "}"
value: STRING | NUMBER
galaxy: "galaxy" STRING AT_ID "{" position planet* nebula* "}"
nebula: "nebula" STRING "{" planet* "}"
planet: "planet" STRING AT_ID "{" position mass type usa* satellite* "}"
satellite: "satellite" STRING AT_ID "{" position mass usa* "}"
position: "position:" "(" NUMBER "," NUMBER ")"
mass: "mass:" NUMBER
type: "type:" PLANET_TYPE
usa: "usa" AT_ID
light: "light" "{" from_clause to_clause flow_clause expiry_clause? "}"
from_clause: "from:" (AT_ID | IDENTIFIER)
to_clause: "to:" (AT_ID | IDENTIFIER)
flow_clause: "flow:" FLOW_TYPE
expiry_clause: "restringido_hasta:" DATE
PLANET_TYPE: "Storage" | "Operation" | "Compute" | "Interface"
FLOW_TYPE: "Primary" | "Asynchronous" | "Read"
DATE: /\d{4}-\d{2}-\d{2}/
AT_ID: /@[a-zA-Z_][a-zA-Z0-9_]*/
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"[^"]*"/
NUMBER: /-?\d+(\.\d+)?/
%import common.WS
%ignore WS
%ignore /\/\/[^\n]*/
%ignore /\/\*.*?\*\//s
"""


def _print(errors, prefix="Error"):
    for err in errors:
        loc = f" at {err.location}" if err.location else ""
        print(f"{prefix} {err.code} [{err.phase}] [{err.severity}]{loc}: {err.message}")


def compile_cosmos(filepath: str, strict: bool = True, dump_ast: bool = False):
    with open(filepath) as f:
        source = f.read()

    # ---- PARSE ---------------------------------------------------
    try:
        parser = Lark(GRAMMAR, parser="lalr")
        tree = parser.parse(source)
        ast = CosmosTransformer().transform(tree)
    except ParseFailure as e:
        loc = f" at {e.location}" if e.location else ""
        print(f"Error {e.code} [PARSER] [REJECT]{loc}: {e.message}")
        return 2
    except InternalCompileError as e:
        print(f"Error {e.code} [{e.phase}] [INTERNAL]: {e.message}")
        return 2
    except UnexpectedEOF as e:
        print(f"Error P002 [PARSER] [REJECT]: Unexpected end of file "
              f"(line {e.line}, column {e.column})")
        return 2
    except UnexpectedInput as e:
        expected = getattr(e, "expected", set()) or set()
        if "UNIVERSE" in expected:
            print("Error P003 [PARSER] [REJECT]: Missing 'universe' declaration")
        elif expected:
            print(f"Error P001 [PARSER] [REJECT]: Unexpected token "
                  f"(line {e.line}, column {e.column}; "
                  f"expected one of: {', '.join(sorted(expected)[:6])})")
        else:
            print(f"Error P001 [PARSER] [REJECT]: Unexpected input "
                  f"(line {e.line}, column {e.column})")
        return 2
    except Exception as e:  # noqa: BLE001 - last resort, must not crash
        print(f"Error E998 [PARSER] [INTERNAL]: {e}")
        return 2

    if dump_ast:
        print("=== AST DUMP ===")
        print(json.dumps(ast, indent=2))
        print("================")

    warnings = []

    # ---- Phase 0: SCHEMA -----------------------------------------
    schema_errors = validate_ast_schema(ast)
    if schema_errors:
        if strict:
            _print(schema_errors)
            return 1
        warnings.extend(schema_errors)

    # ---- Phase 1: TOPOLOGY ---------------------------------------
    topo_errors = verify_topology(ast, strict=strict)
    if topo_errors:
        rejects = [e for e in topo_errors if e.severity == "REJECT"]
        if strict and rejects:
            _print(topo_errors)
            return 1
        warnings.extend(topo_errors)

    # ---- Phase 2: TEMPORAL ---------------------------------------
    temporal_errors = verify_temporal_restrictions(ast, strict=strict)
    if temporal_errors:
        rejects = [e for e in temporal_errors if e.severity == "REJECT"]
        if strict and rejects:
            _print(temporal_errors)
            print("Compilation halted.")
            return 1
        warnings.extend(temporal_errors)

    if warnings:
        _print(warnings, prefix="Warning")
    print("VALID ✓")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m cosmos.compiler <file.cosmos> [--strict|--lax] [--dump-ast]")
        sys.exit(2)

    filepath = sys.argv[1]
    # Strict is the default (RFC-0004-C section 2). --lax opts out.
    strict = "--lax" not in sys.argv
    dump_ast = "--dump-ast" in sys.argv
    sys.exit(compile_cosmos(filepath, strict=strict, dump_ast=dump_ast))
