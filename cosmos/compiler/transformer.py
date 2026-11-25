"""
cosmos/compiler/transformer.py
==============================

Lark Transformer: parse tree -> dict AST (RFC-0004-F rewritten 2026-11-25).

Fixes vs the old transformer (which silently dropped every planet and
kept quoted strings):
- Every node returns a TAGGED dict ({"planet": {...}}, {"galaxy": {...}},
  {"light": {...}}, ...). Dispatch is by tag, never by guessing from
  keys. The old bug: a planet dict contains "position", so the galaxy
  handler mistook it for the galaxy's own position and discarded it.
- STRING tokens are unquoted, NUMBER tokens become floats, AT_ID tokens
  lose the "@". The old string()/number() methods never ran: Lark only
  calls transformer methods for RULES, and STRING/NUMBER are terminals.
  Conversion happens here, at the point of use.
- Positions are {"radius": ..., "theta": ...} (polar), not {"x", "y"}.
- Suns are a list (grammar allows sun* so a second Sun is E108, not a
  parse error). Planets inside nebulas are flattened into their galaxy
  with a "nebula" tag.
"""

from lark import Transformer, v_args

from cosmos.compiler.errors import ParseFailure


def _str(tok) -> str:
    """Unquote a STRING token."""
    s = str(tok)
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _num(tok) -> float:
    """Convert a NUMBER token to float."""
    return float(tok)


def _id(tok) -> str:
    """Plain identifier (no @)."""
    return str(tok)


def _at(tok) -> str:
    """@-identifier with the @ stripped. "@foo" -> "foo"."""
    s = str(tok)
    return s[1:] if s.startswith("@") else s


@v_args(inline=True)
class CosmosTransformer(Transformer):
    # ---- leaves -------------------------------------------------
    def version(self, token):
        return {"version": _str(token)}

    def author(self, token):
        return {"author": _str(token)}

    def standard(self, token):
        return {"standard": _str(token)}

    def position(self, x, y):
        return {"position": {"radius": _num(x), "theta": _num(y)}}

    def mass(self, token):
        value = _num(token)
        if value != int(value) or value < 1:
            raise ParseFailure(
                "P010",
                f"mass must be a positive integer, got {token}",
            )
        return {"mass": int(value)}

    def type(self, token):
        return {"type": str(token)}

    def usa(self, token):
        return {"usa": _at(token)}

    def value(self, token):
        s = str(token)
        if s.startswith('"'):
            return _str(token)
        return _num(token)

    # ---- clauses ------------------------------------------------
    def from_clause(self, token):
        is_at = getattr(token, "type", None) == "AT_ID"
        return {
            "from": _at(token) if is_at else _id(token),
            "from_is_at": is_at,
        }

    def to_clause(self, token):
        is_at = getattr(token, "type", None) == "AT_ID"
        return {
            "to": _at(token) if is_at else _id(token),
            "to_is_at": is_at,
        }

    def flow_clause(self, token):
        return {"flow": str(token)}

    def expiry_clause(self, token):
        return {"restringido_hasta": str(token)}

    # ---- declarations -------------------------------------------
    def sun(self, name, *args):
        return {
            "sun": {
                "name": _id(name),
                "has_position": len(args) > 0,
            }
        }

    def star(self, name, orbit_id, value):
        return {
            "star": {
                "name": _str(name),
                "orbit_id": _at(orbit_id),
                "value": value,
            }
        }

    def satellite(self, name, orbit_id, *args):
        node: dict = {
            "name": _str(name),
            "orbit_id": _at(orbit_id),
            "uses": [],
        }
        for arg in args:
            if isinstance(arg, dict):
                if "position" in arg:
                    node["position"] = arg["position"]
                elif "mass" in arg:
                    node["mass"] = arg["mass"]
                elif "usa" in arg:
                    node["uses"].append(arg["usa"])
        if "position" not in node:
            raise ParseFailure(
                "P006",
                f"satellite '{node['name']}' is missing position",
            )
        if "mass" not in node:
            raise ParseFailure(
                "P007",
                f"satellite '{node['name']}' is missing mass",
            )
        return {"satellite": node}

    def planet(self, name, orbit_id, *args):
        node: dict = {
            "name": _str(name),
            "orbit_id": _at(orbit_id),
            "uses": [],
            "satellites": [],
        }
        for arg in args:
            if isinstance(arg, dict):
                if "position" in arg:
                    node["position"] = arg["position"]
                elif "mass" in arg:
                    node["mass"] = arg["mass"]
                elif "type" in arg:
                    node["type"] = arg["type"]
                elif "usa" in arg:
                    node["uses"].append(arg["usa"])
                elif "satellite" in arg:
                    node["satellites"].append(arg["satellite"])
        for field, code in (("position", "P006"), ("mass", "P007"), ("type", "P008")):
            if field not in node:
                raise ParseFailure(
                    code,
                    f"planet '{node['name']}' is missing {field}",
                )
        return {"planet": node}

    def nebula(self, name, *args):
        planets = []
        for arg in args:
            if isinstance(arg, dict) and "planet" in arg:
                planet = dict(arg["planet"])
                planet["nebula"] = _str(name)
                planets.append(planet)
        return {"nebula": {"name": _str(name), "planets": planets}}

    def galaxy(self, name, orbit_id, *args):
        node: dict = {
            "name": _str(name),
            "orbit_id": _at(orbit_id),
            "planets": [],
        }
        for arg in args:
            if isinstance(arg, dict):
                if "position" in arg and "planet" not in arg and "nebula" not in arg:
                    node["position"] = arg["position"]
                elif "planet" in arg:
                    node["planets"].append(arg["planet"])
                elif "nebula" in arg:
                    node["planets"].extend(arg["nebula"]["planets"])
        if "position" not in node:
            raise ParseFailure(
                "P006",
                f"galaxy '{node['name']}' is missing position",
            )
        return {"galaxy": node}

    def light(self, *args):
        node: dict = {"restringido_hasta": None}
        for arg in args:
            if isinstance(arg, dict):
                node.update(arg)
        return {"light": node}

    def metadata(self, *args):
        meta: dict = {}
        for arg in args:
            if isinstance(arg, dict):
                meta.update(arg)
        return {"metadata": meta}

    def universe(self, name, *args):
        ast: dict = {
            "universe": _str(name),
            "metadata": {},
            "suns": [],
            "stars": [],
            "galaxies": [],
            "lights": [],
        }
        for arg in args:
            if not isinstance(arg, dict):
                continue
            if "metadata" in arg:
                ast["metadata"] = arg["metadata"]
            elif "sun" in arg:
                ast["suns"].append(arg["sun"])
            elif "star" in arg:
                ast["stars"].append(arg["star"])
            elif "galaxy" in arg:
                ast["galaxies"].append(arg["galaxy"])
            elif "light" in arg:
                ast["lights"].append(arg["light"])
        return ast

    def start(self, *args):
        for arg in args:
            if isinstance(arg, dict) and "universe" in arg:
                return arg
        return {}
