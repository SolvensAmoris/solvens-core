#!/usr/bin/env python3
"""
run_tests.py — Cosmos topology compiler test suite.

Usage:
    python run_tests.py [--root <package-root>]

--root is the directory that contains the `cosmos` package
(default: the parent of this tests/ directory, i.e. the workspace
copy). Runs `python -m cosmos.compiler <file>` for every .cosmos
file in this directory and checks the expected outcome.

Expected outcomes are declared in EXPECTED below:
- "VALID"        -> exit 0 and "VALID" in stdout, no E004
- "VALID+E004"   -> exit 0, "VALID" in stdout and E004 present
- "E###"         -> exit 1 and the code present in stdout
- "P###:parse"   -> exit 2 (parse error) and the code present

Requires: lark (pip install lark).
"""

import argparse
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

EXPECTED = {
    # valid files
    "valid-sistema-hibrido.cosmos": "VALID",
    "valid-basico.cosmos": "VALID",
    "valid-star.cosmos": "VALID",
    "valid-nebula.cosmos": "VALID",
    # topology rejections
    "e001-usa-outward.cosmos": "E001",
    "e002-mass-collision.cosmos": "E002",
    "e003-light-too-long.cosmos": "E003",
    "e004-tension.cosmos": "VALID+E004",
    "e005-invalid-coords.cosmos": "E005",
    "e006-bidirectional.cosmos": "E006",
    "e007-deepspace.cosmos": "E007",
    "e101-duplicate-id.cosmos": "E101",
    "e102-missing-metadata-field.cosmos": "E102",
    "e103-bad-reference.cosmos": "E103",
    "e103-usa-star.cosmos": "E103",
    "e104-bad-metadata.cosmos": "E104",
    "e105-sun-receiver.cosmos": "E105",
    "e106-satellite-scope.cosmos": "E106",
    "e107-galaxy-in-core.cosmos": "E107",
    "e108-two-suns.cosmos": "E108",
    "e109-matrix.cosmos": "E109",
    "e110-type-orbit.cosmos": "E110",
    "e111-satellite-ratio.cosmos": "E111",
    "e112-empty-universe.cosmos": "E112",
    "e401-expired.cosmos": "E401",
    "e403-cross-galaxy.cosmos": "E403",
    "e404-usa-cycle.cosmos": "E404",
    "e404-light-cycle.cosmos": "E404",
    # parser rejections
    "p001-bare-usa.cosmos": "P001:parse",
    "p012-sun-position.cosmos": "P012",
}


def find_root(start):
    """Walk up from the tests dir to the directory containing the
    `cosmos` package (cosmos/compiler/__main__.py). Works both in
    the workspace copy (tests/cosmos-topology/ -> workspace/cosmos)
    and in the repo (tests/cosmos-topology/ -> repo root)."""
    d = start.resolve()
    while True:
        if (d / "cosmos" / "compiler" / "__main__.py").exists():
            return d
        if d.parent == d:
            return start.parent
        d = d.parent


def run_one(python, root, path):
    result = subprocess.run(
        [python, "-m", "cosmos.compiler", str(path)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode, result.stdout + result.stderr


def check(name, expected, code, output):
    if expected == "VALID":
        return code == 0 and "VALID" in output and "E004" not in output
    if expected == "VALID+E004":
        return code == 0 and "VALID" in output and "E004" in output
    if expected.endswith(":parse"):
        want = expected.split(":")[0]
        return code == 2 and want in output
    return code == 1 and expected in output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None,
                        help="directory containing the cosmos package "
                             "(default: walk up to the package root)")
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else find_root(TESTS_DIR)
    python = sys.executable

    files = sorted(TESTS_DIR.glob("*.cosmos"))
    unknown = [f.name for f in files if f.name not in EXPECTED]
    if unknown:
        print(f"WARNING: no expected outcome declared for: {', '.join(unknown)}")

    passed, failed = 0, 0
    rows = []
    for path in files:
        expected = EXPECTED.get(path.name)
        if expected is None:
            continue
        code, output = run_one(python, root, path)
        ok = check(path.name, expected, code, output)
        rows.append((path.name, expected, code, ok))
        if ok:
            passed += 1
        else:
            failed += 1

    width = max(len(r[0]) for r in rows)
    for name, expected, code, ok in rows:
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  {name:<{width}}  expected {expected:<12} exit={code}")
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
