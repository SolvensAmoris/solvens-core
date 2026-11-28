import sys
import json
from lark import Lark
from cosmos.compiler.transformer import CosmosTransformer
from cosmos.compiler.schema import validate_ast_schema
from cosmos.compiler.validators.temporal import verify_temporal_restrictions
from cosmos.compiler.errors import InternalCompileError


GRAMMAR = r"""
start: universe
universe: "universe" STRING "{" metadata sun galaxy* light* "}"
metadata: "metadata" "{" version author standard "}"
version: "version:" STRING
author: "author:" STRING
standard: "standard:" STRING
sun: "sun" IDENTIFIER
galaxy: "galaxy" STRING IDENTIFIER "{" position planet* "}"
planet: "planet" STRING IDENTIFIER "{" position mass? "}"
position: "position:" "(" NUMBER "," NUMBER ")"
mass: "mass:" NUMBER
light: "light" "{" from_clause to_clause flow_clause expiry_clause? "}"
from_clause: "from:" IDENTIFIER
to_clause: "to:" IDENTIFIER
flow_clause: "flow:" FLOW_TYPE
expiry_clause: "restringido_hasta:" DATE
FLOW_TYPE: "Primary" | "Asynchronous" | "Read"
DATE: /\d{4}-\d{2}-\d{2}/
IDENTIFIER: /@?[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"[^"]*"/
NUMBER: /\d+(\.\d+)?/
%import common.WS
%ignore WS
"""


def compile_cosmos(filepath: str, strict: bool = True, dump_ast: bool = False):
    with open(filepath) as f:
        source = f.read()


    try:
        parser = Lark(GRAMMAR, parser="lalr")
        tree = parser.parse(source)
        transformer = CosmosTransformer()
        ast = transformer.transform(tree)
    except Exception as e:
        print(f"Error E998 [PARSER] [INTERNAL]: {e}")
        return 2


    if dump_ast:
        print("=== AST DUMP ===")
        print(json.dumps(ast, indent=2))
        print("================")


    # Fase 0: Schema
    schema_errors = validate_ast_schema(ast)
    if schema_errors:
        for err in schema_errors:
            print(f"Error {err.code} [{err.phase}] [{err.severity}]: {err.message}")
        return 1


    # Fase 1: Temporal
    temporal_errors = verify_temporal_restrictions(ast, strict=strict)
    if temporal_errors:
        for err in temporal_errors:
            print(f"Error {err.code} [{err.phase}] [{err.severity}] at {err.location}: {err.message}")
        if strict:
            print("Compilation halted.")
            return 1


    print("VALID ✓")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m cosmos.compiler <file.cosmos> [--strict] [--dump-ast]")
        sys.exit(2)


    filepath = sys.argv[1]
    strict = "--strict" in sys.argv
    dump_ast = "--dump-ast" in sys.argv
    sys.exit(compile_cosmos(filepath, strict=strict, dump_ast=dump_ast))
