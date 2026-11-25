"""
cosmos/compiler/validators/topology.py
======================================

Topology validation (RFC-0004-F rewritten 2026-11-25).

This is the phase that did not exist: the old compiler checked only
parsing + schema + temporal expiry, and printed VALID on a corrupt AST.
Every rule here is ported from the Rust implementation
(cosmos-topology, src/lib.rs) with the same constants and the same
geometry: polar positions, cartesian distances, bands derived from
radius, max_reach = 1000.0 / mass.

Constants (RFC-0004-F section 4.3):
- EPSILON = 0.5            (node collision distance, E002)
- GALACTIC_EPSILON = 1.0   (galaxy separation, E002)
- SATELLITE_MASS_RATIO = 0.5 (satellite mass cap, E111)
- BASE_CONSTANT = 1000.0   (reach: max_reach = 1000.0 / mass, E003)
- TENSION_THRESHOLD = 10   (max light crossings, E004 warning)
- SUN_MASS = 10            (the Sun's reach is 100, the whole universe)

Checks run in three phases so one broken reference does not cascade
into a dozen phantom errors:
  A. structural (no resolution): E108, E112, E101, E005, E007, E107,
     E110, E002, E111, E106 (satellite band).
  B. resolution: E103, E105.
  C. relational: E403, E001 (usa rule, Interface->Core), E003, E109,
     E006, E404, E004 (warning).
In strict mode the validator returns at the first failing phase; in
lax mode every finding is reported with severity WARNING.
"""

import math
from typing import Any, Dict, List, Optional

from cosmos.compiler.errors import CompileError

EPSILON = 0.5
GALACTIC_EPSILON = 1.0
SATELLITE_MASS_RATIO = 0.5
BASE_CONSTANT = 1000.0
TENSION_THRESHOLD = 10
SUN_MASS = 10


# ============================================================
# Geometry (ported from PolarPosition / OrbitBand in lib.rs)
# ============================================================

def band_of(radius: float) -> Optional[int]:
    """Orbit number from radius. None = DeepSpace (no orbit)."""
    if radius <= 10.0:
        return 5
    if radius <= 50.0:
        return 4
    if radius <= 100.0:
        return 3
    return None


def to_cartesian(radius: float, theta: float) -> tuple:
    return (radius * math.cos(theta), radius * math.sin(theta))


def distance(p1: tuple, p2: tuple) -> float:
    (x1, y1) = to_cartesian(*p1)
    (x2, y2) = to_cartesian(*p2)
    return math.hypot(x2 - x1, y2 - y1)


# ============================================================
# Flow matrix (ported from flow_allowed in lib.rs)
# ============================================================

FLOW_ALLOWED = {
    ("Storage", "Operation"),
    ("Storage", "Compute"),
    ("Operation", "Compute"),
    ("Operation", "Interface"),
    ("Compute", "Interface"),
}

TYPE_ORBITS = {
    "Storage": {4},
    "Operation": {4},
    "Compute": {4},
    "Interface": {3},
}


# ============================================================
# Node index
# ============================================================

class _Index:
    """Every addressable entity in the universe, keyed by @id."""

    def __init__(self, ast: Dict[str, Any]):
        self.sun = None
        self.suns = ast.get("suns") or []
        self.galaxies: Dict[str, dict] = {}
        self.nodes: Dict[str, dict] = {}   # @id -> planet / satellite / star
        self.planets: Dict[str, dict] = {}
        self.satellites: Dict[str, dict] = {}
        self.stars: Dict[str, dict] = {}
        # Every declared @id, in order (dicts lose duplicates by
        # overwriting, so E101 needs this list).
        self.id_list: List[tuple] = []     # (orbit_id, kind)

        if self.suns:
            sun = self.suns[0]
            self.sun = {
                "kind": "sun",
                "name": sun.get("name"),
                "position": (0.0, 0.0),
                "mass": SUN_MASS,
                "band": 5,
                "galaxy": None,
            }

        for galaxy in ast.get("galaxies") or []:
            gid = galaxy.get("orbit_id")
            pos = galaxy.get("position") or {}
            self.galaxies[gid] = {
                "kind": "galaxy",
                "id": gid,
                "name": galaxy.get("name"),
                "position": (pos.get("radius"), pos.get("theta")),
                "band": band_of(pos.get("radius", 0.0)),
            }
            self.id_list.append((gid, "galaxy"))
            for planet in galaxy.get("planets") or []:
                pid = planet.get("orbit_id")
                ppos = planet.get("position") or {}
                node = {
                    "kind": "planet",
                    "id": pid,
                    "name": planet.get("name"),
                    "galaxy": gid,
                    "position": (ppos.get("radius"), ppos.get("theta")),
                    "mass": planet.get("mass"),
                    "type": planet.get("type"),
                    "band": band_of(ppos.get("radius", 0.0)),
                    "uses": list(planet.get("uses") or []),
                    "nebula": planet.get("nebula"),
                }
                self.planets[pid] = node
                self.nodes[pid] = node
                self.id_list.append((pid, "planet"))
                for sat in planet.get("satellites") or []:
                    sid = sat.get("orbit_id")
                    spos = sat.get("position") or {}
                    abs_r = ppos.get("radius", 0.0) + spos.get("radius", 0.0)
                    abs_t = ppos.get("theta", 0.0) + spos.get("theta", 0.0)
                    snode = {
                        "kind": "satellite",
                        "id": sid,
                        "name": sat.get("name"),
                        "galaxy": gid,
                        "parent": pid,
                        "position": (abs_r, abs_t),
                        "rel_position": (spos.get("radius"), spos.get("theta")),
                        "mass": sat.get("mass"),
                        "band": band_of(abs_r),
                        "uses": list(sat.get("uses") or []),
                    }
                    self.satellites[sid] = snode
                    self.nodes[sid] = snode
                    self.id_list.append((sid, "satellite"))

        for star in ast.get("stars") or []:
            sid = star.get("orbit_id")
            snode = {
                "kind": "star",
                "id": sid,
                "name": star.get("name"),
                "value": star.get("value"),
                "galaxy": None,
                "position": None,
                "band": None,
            }
            self.stars[sid] = snode
            self.nodes[sid] = snode
            self.id_list.append((sid, "star"))


# ============================================================
# Validator
# ============================================================

def _err(code, message, location="", strict=True, warning=False):
    severity = "WARNING" if (warning or not strict) else "REJECT"
    return CompileError(
        code=code, phase="TOPOLOGY", severity=severity,
        message=message, location=location,
    )


def verify_topology(ast: Dict[str, Any], strict: bool = True) -> List[CompileError]:
    idx = _Index(ast)
    errors: List[CompileError] = []

    # ---- Phase A: structural (no resolution) -------------------
    if len(idx.suns) > 1:
        names = ", ".join(s.get("name", "?") for s in idx.suns)
        errors.append(_err("E108", f"Multiple Sun declared: {names}", "universe", strict))
    if not idx.galaxies:
        errors.append(_err("E112", "Empty universe: no galaxies declared", "universe", strict))
    if errors:
        return errors

    # E101: duplicate identifiers (from the ordered id list: dicts
    # overwrite duplicates, so the dicts alone cannot see them)
    seen: Dict[str, str] = {}
    for oid, kind in idx.id_list:
        if oid in seen:
            errors.append(_err("E101", f"Duplicate identifier @{oid} ({kind}, first seen as {seen[oid]})", f"{kind} @{oid}", strict))
        else:
            seen[oid] = kind
    if idx.sun and idx.sun["name"] in seen:
        errors.append(_err("E101", f"Sun name '{idx.sun['name']}' collides with @identifier @{idx.sun['name']} (ambiguous reference)", "universe.sun", strict))
    if errors:
        return errors

    # E005 / E007: positions (galaxies, planets, satellites)
    def _check_position(pos, what, loc):
        radius, theta = pos
        if radius is None or theta is None:
            errors.append(_err("E102", f"{what} is missing a valid position", loc, strict))
            return
        if radius < 0.0 or not math.isfinite(theta):
            errors.append(_err("E005", f"{what} has invalid coordinates (radius={radius}, theta={theta})", loc, strict))
        elif radius > 100.0:
            errors.append(_err("E007", f"{what} is in DeepSpace (radius={radius} > 100.0)", loc, strict))

    for gid, gal in idx.galaxies.items():
        _check_position(gal["position"], f"galaxy @{gid}", f"galaxy @{gid}")
        if gal["position"][0] is not None and gal["position"][0] <= 10.0:
            errors.append(_err("E107", f"galaxy @{gid} is in Core (radius={gal['position'][0]} <= 10.0)", f"galaxy @{gid}", strict))
    for pid, planet in idx.planets.items():
        _check_position(planet["position"], f"planet @{pid}", f"planet @{pid}")
    for sid, sat in idx.satellites.items():
        _check_position(sat["position"], f"satellite @{sid}", f"satellite @{sid}")
    if errors:
        return errors

    # E110: planet type must admit its band (also: no planet in Core)
    for pid, planet in idx.planets.items():
        allowed = TYPE_ORBITS.get(planet["type"], set())
        if planet["band"] not in allowed:
            errors.append(_err(
                "E110",
                f"PlanetType '{planet['type']}' incompatible with orbit band {planet['band']} "
                f"(planet @{pid}, radius={planet['position'][0]})",
                f"planet @{pid}", strict,
            ))
    if errors:
        return errors

    # E002: mass collisions (same galaxy, distance < 0.5; galaxies < 1.0)
    for gid, gal in idx.galaxies.items():
        members = [n for n in list(idx.planets.values()) + list(idx.satellites.values())
                   if n["galaxy"] == gid]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                d = distance(a["position"], b["position"])
                if d < EPSILON:
                    errors.append(_err(
                        "E002",
                        f"Mass collision: @{a['id']} and @{b['id']} are {d:.4f} apart (< {EPSILON})",
                        f"galaxy @{gid}", strict,
                    ))
    gals = list(idx.galaxies.values())
    for i in range(len(gals)):
        for j in range(i + 1, len(gals)):
            a, b = gals[i], gals[j]
            d = distance(a["position"], b["position"])
            if d < GALACTIC_EPSILON:
                errors.append(_err(
                    "E002",
                    f"Mass collision: galaxies @{a['id']} and @{b['id']} are {d:.4f} apart (< {GALACTIC_EPSILON})",
                    "universe", strict,
                ))
    if errors:
        return errors

    # E111: satellite mass ratio (sum <= 50% of planet mass)
    for pid, planet in idx.planets.items():
        sats = [s for s in idx.satellites.values() if s["parent"] == pid]
        total = sum(s["mass"] or 0 for s in sats)
        max_allowed = int((planet["mass"] or 0) * SATELLITE_MASS_RATIO)
        if total > max_allowed:
            errors.append(_err(
                "E111",
                f"Satellite mass {total} exceeds 50% of planet @{pid} mass "
                f"{planet['mass']} (max {max_allowed})",
                f"planet @{pid}", strict,
            ))
    if errors:
        return errors

    # E106: satellite outside its parent's band
    for sid, sat in idx.satellites.items():
        parent = idx.planets.get(sat["parent"])
        if parent and sat["band"] != parent["band"]:
            errors.append(_err(
                "E106",
                f"Satellite @{sid} is in orbit band {sat['band']} but its parent "
                f"planet @{sat['parent']} is in band {parent['band']}",
                f"satellite @{sid}", strict,
            ))
    if errors:
        return errors

    # ---- Phase B: resolution ------------------------------------
    lights = ast.get("lights") or []
    resolved = []  # (light dict, from_node or None, to_node or None)
    for n, light in enumerate(lights):
        loc = f"light_{n}[{light.get('from')}->{light.get('to')}]"
        # from
        from_node = None
        if light.get("from_is_at"):
            from_node = idx.nodes.get(light.get("from"))
            if from_node is None:
                errors.append(_err("E103", f"Invalid entity reference: @{light.get('from')} does not exist", loc, strict))
                continue
            if from_node["kind"] in ("galaxy", "star"):
                errors.append(_err("E103", f"Invalid flow source: @{light.get('from')} is a {from_node['kind']}, not a node", loc, strict))
                continue
        else:
            if idx.sun and light.get("from") == idx.sun["name"]:
                from_node = idx.sun
            else:
                errors.append(_err("E103", f"Invalid entity reference: '{light.get('from')}' is not the Sun and has no @", loc, strict))
                continue
        # to
        to_node = None
        if light.get("to_is_at"):
            to_node = idx.nodes.get(light.get("to"))
            if to_node is None:
                errors.append(_err("E103", f"Invalid entity reference: @{light.get('to')} does not exist", loc, strict))
                continue
            if to_node["kind"] == "star":
                errors.append(_err("E105", f"Star @{light.get('to')} cannot be a flow receiver", loc, strict))
                continue
            if to_node["kind"] == "galaxy":
                errors.append(_err("E103", f"Invalid flow target: @{light.get('to')} is a galaxy, not a node", loc, strict))
                continue
        else:
            if idx.sun and light.get("to") == idx.sun["name"]:
                errors.append(_err("E105", f"Sun '{light.get('to')}' cannot be a flow receiver", loc, strict))
                continue
            errors.append(_err("E103", f"Invalid entity reference: '{light.get('to')}' is not the Sun and has no @", loc, strict))
            continue
        resolved.append((light, from_node, to_node, loc))

    # usa references (planets and satellites)
    for nid, node in {**idx.planets, **idx.satellites}.items():
        for target_id in node.get("uses") or []:
            target = idx.nodes.get(target_id)
            if target is None:
                errors.append(_err("E103", f"Invalid entity reference: @{target_id} does not exist (used by @{nid})", f"@{nid}", strict))
            elif target["kind"] == "star":
                errors.append(_err("E103", f"Invalid entity reference: @{target_id} is a Star, not a valid dependency target (used by @{nid})", f"@{nid}", strict))
    if errors:
        return errors

    # ---- Phase C: relational ------------------------------------
    def _key(node):
        return node["name"] if node["kind"] == "sun" else node["id"]

    # E403: cross-galaxy (light) / E106: satellite usa outside galaxy
    for light, fnode, tnode, loc in resolved:
        fg, tg = fnode.get("galaxy"), tnode.get("galaxy")
        if fg is not None and tg is not None and fg != tg:
            errors.append(_err("E403", f"Cross-galaxy access: {_key(fnode)} (galaxy @{fg}) -> {_key(tnode)} (galaxy @{tg})", loc, strict))
    for nid, node in {**idx.planets, **idx.satellites}.items():
        for target_id in node.get("uses") or []:
            target = idx.nodes.get(target_id)
            if target is None or target["kind"] == "star":
                continue
            if target.get("galaxy") is not None and target["galaxy"] != node["galaxy"]:
                if node["kind"] == "satellite":
                    errors.append(_err("E106", f"Satellite @{nid} accesses @{target_id} outside its galaxy", f"@{nid}", strict))
                else:
                    errors.append(_err("E403", f"Cross-galaxy access: @{nid} -> @{target_id}", f"@{nid}", strict))

    # E001: usa must point inward (target band number >= source band)
    for nid, node in {**idx.planets, **idx.satellites}.items():
        for target_id in node.get("uses") or []:
            target = idx.nodes.get(target_id)
            if target is None or target["kind"] == "star" or target.get("band") is None:
                continue
            if node["band"] is not None and target["band"] < node["band"]:
                errors.append(_err(
                    "E001",
                    f"Orbit violation: @{nid} (orbit {node['band']}) depends on @{target_id} "
                    f"(orbit {target['band']}) — dependencies point inward",
                    f"@{nid}", strict,
                ))

    # Light rules: E003 reach, E001 Interface->Core, E109 matrix
    for light, fnode, tnode, loc in resolved:
        d = distance(fnode["position"], tnode["position"])
        reach = BASE_CONSTANT / max(fnode["mass"] or 1, 1)
        if d > reach:
            errors.append(_err(
                "E003",
                f"Light path too long: {d:.2f} > reach {reach:.2f} "
                f"(emitter {_key(fnode)}, mass {fnode['mass']})",
                loc, strict,
            ))
        if fnode["band"] == 3 and tnode["band"] == 5:
            errors.append(_err(
                "E001",
                f"Orbit violation: Interface -> Core direct flow {_key(fnode)} -> {_key(tnode)}",
                loc, strict,
            ))
        if fnode["kind"] == "planet" and tnode["kind"] == "planet":
            if (fnode["type"], tnode["type"]) not in FLOW_ALLOWED:
                errors.append(_err(
                    "E109",
                    f"Flow matrix violation: {fnode['type']} -> {tnode['type']} "
                    f"(@{fnode['id']} -> @{tnode['id']})",
                    loc, strict,
                ))

    # E006: bidirectional lights
    pairs = {}
    for light, fnode, tnode, loc in resolved:
        pairs.setdefault((_key(fnode), _key(tnode)), loc)
    reported = set()
    for (a, b), loc in list(pairs.items()):
        if (b, a) in pairs and frozenset((a, b)) not in reported:
            errors.append(_err(
                "E006",
                f"Bidirectional light forbidden: {a} -> {b} and {b} -> {a} both declared",
                loc, strict,
            ))
            reported.add(frozenset((a, b)))

    # E404: cycles (light graph and usa graph)
    def _find_cycle(edges):
        graph: Dict[str, List[str]] = {}
        for a, b in edges:
            graph.setdefault(a, []).append(b)
        visited, stack, path = set(), set(), []

        def dfs(node):
            if node in stack:
                pos = path.index(node)
                return path[pos:] + [node]
            if node in visited:
                return None
            visited.add(node)
            stack.add(node)
            path.append(node)
            for child in graph.get(node, []):
                cycle = dfs(child)
                if cycle:
                    return cycle
            stack.discard(node)
            path.pop()
            return None

        for start in graph:
            cycle = dfs(start)
            if cycle:
                return cycle
        return None

    light_edges = [(_key(f), _key(t)) for _, f, t, _ in resolved]
    cycle = _find_cycle(light_edges)
    if cycle:
        errors.append(_err("E404", f"Flow cycle detected: {' -> '.join(cycle)}", "lights", strict))
    usa_edges = []
    for nid, node in {**idx.planets, **idx.satellites}.items():
        for target_id in node.get("uses") or []:
            if target_id in idx.nodes:
                usa_edges.append((nid, target_id))
    cycle = _find_cycle(usa_edges)
    if cycle:
        errors.append(_err("E404", f"Dependency cycle detected: {' -> '.join(cycle)}", "usa", strict))

    # E004: tension (warning, never blocks)
    segments = []
    for light, fnode, tnode, loc in resolved:
        segments.append((fnode["position"], tnode["position"]))
    crossings = _count_crossings(segments)
    if crossings > TENSION_THRESHOLD:
        errors.append(_err(
            "E004",
            f"Spaghetti tension exceeded: {crossings} crossings > threshold {TENSION_THRESHOLD}",
            "lights", strict, warning=True,
        ))

    return errors


def _lines_intersect(a1, a2, b1, b2) -> bool:
    """Ported from CosmosTopology::lines_intersect (lib.rs)."""
    (x1, y1) = to_cartesian(*a1)
    (x2, y2) = to_cartesian(*a2)
    (x3, y3) = to_cartesian(*b1)
    (x4, y4) = to_cartesian(*b2)
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if abs(denom) < 1e-9:
        return False
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
    return ua > 1e-9 and ua < 1.0 - 1e-9 and ub > 1e-9 and ub < 1.0 - 1e-9


def _count_crossings(segments) -> int:
    total = 0
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            if _lines_intersect(*segments[i], *segments[j]):
                total += 1
    return total
