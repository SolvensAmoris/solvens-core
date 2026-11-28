#!/usr/bin/env python3
"""
SOLVENS CORE - Official Smoke Test
=================================

This smoke test validates the core functionality of SOLVENS CORE
in a quick, non-exhaustive manner.

Run with: python tests/smoke/smoke_test.py

Exit codes:
    0 - PASS
    1 - FAIL
"""

import sys
import subprocess
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def test_result(name: str, passed: bool, details: str = "") -> bool:
    """Print test result and return status."""
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    if details:
        print(f"         {details}")
    return passed


def main():
    """Run all smoke tests."""
    print("\n" + "=" * 50)
    print("  SOLVENS CORE - Official Smoke Test")
    print("=" * 50)
    
    all_passed = True
    results = []
    
    # ===========================================
    # TEST 1: Installation
    # ===========================================
    print("\n[1] Installation")
    
    # Check Python version
    version = sys.version_info
    version_ok = version >= (3, 10)
    results.append(test_result(
        f"Python >= 3.10 (current: {version.major}.{version.minor})",
        version_ok
    ))
    all_passed = all_passed and version_ok
    
    # Check required packages
    required_packages = ["rich", "pydantic", "httpx"]
    for pkg in required_packages:
        try:
            __import__(pkg)
            results.append(test_result(f"Package '{pkg}' installed", True))
        except ImportError:
            results.append(test_result(f"Package '{pkg}' installed", False))
            all_passed = False
    
    # ===========================================
    # TEST 2: CLI
    # ===========================================
    print("\n[2] CLI")
    
    try:
        from solvens.cli import main as cli_main
        results.append(test_result("CLI module imports", True))
    except ImportError as e:
        results.append(test_result("CLI module imports", False, str(e)))
        all_passed = False
        cli_main = None
    
    # ===========================================
    # TEST 3: Parser
    # ===========================================
    print("\n[3] Parser")
    
    try:
        from cosmos.parser.parser import Parser
        test_code = '''
provider openai {
    type = "openai"
}

task hello {
    provider = "openai"
    depends_on = []
}
'''
        parser = Parser(test_code)
        ast = parser.parse()
        results.append(test_result("Parser - Basic workflow", True))
        results.append(test_result("Parser - AST generation", len(ast.statements) > 0))
        all_passed = all_passed and len(ast.statements) > 0
    except Exception as e:
        results.append(test_result("Parser - Basic workflow", False, str(e)))
        results.append(test_result("Parser - AST generation", False))
        all_passed = False
    
    # ===========================================
    # TEST 4: DAG
    # ===========================================
    print("\n[4] DAG")
    
    try:
        from cosmos.dag import DAG, build_dag_from_ast
        from cosmos.parser.parser import Parser
        
        dag_code = '''
provider openai { type = "openai" }

task a { provider = "openai" }
task b { provider = "openai" depends_on = [a] }
task c { provider = "openai" depends_on = [b] }
'''
        parser = Parser(dag_code)
        ast = parser.parse()
        dag = build_dag_from_ast(ast.statements)
        
        results.append(test_result("DAG - Build from AST", True))
        results.append(test_result("DAG - Has nodes", len(dag.nodes) >= 3))
        results.append(test_result("DAG - Has edges", len(dag.edges) >= 2))
        
        topo = dag.topological_sort()
        results.append(test_result("DAG - Topological sort", len(topo) >= 3))
        
        all_passed = all_passed and len(dag.nodes) >= 3
    except Exception as e:
        results.append(test_result("DAG - Build from AST", False, str(e)))
        all_passed = False
    
    # ===========================================
    # TEST 5: Compiler
    # ===========================================
    print("\n[5] Compiler")
    
    try:
        from cosmos.compiler.errors import CompileError
        results.append(test_result("Compiler - Error types", True))
    except ImportError as e:
        results.append(test_result("Compiler - Error types", False, str(e)))
        all_passed = False
    
    # ===========================================
    # TEST 6: Security
    # ===========================================
    print("\n[6] Security")
    
    try:
        from cosmos.security.rbac import RBAC
        # RBAC should work without secret in test mode
        rbac = RBAC()
        results.append(test_result("Security - RBAC initializes", True))
    except Exception as e:
        results.append(test_result("Security - RBAC initializes", False, str(e)))
        all_passed = False
    
    # ===========================================
    # TEST 7: Executor (Mock)
    # ===========================================
    print("\n[7] Executor")
    
    try:
        from cosmos.dag import DAG
        dag = DAG()
        dag.add_node("test_node", {"provider": "mock"})
        
        results.append(test_result("Executor - DAG creation", True))
        results.append(test_result("Executor - Node added", "test_node" in dag.nodes))
        
        all_passed = all_passed and "test_node" in dag.nodes
    except Exception as e:
        results.append(test_result("Executor - DAG creation", False, str(e)))
        all_passed = False
    
    # ===========================================
    # TEST 8: Visualizer
    # ===========================================
    print("\n[8] Visualizer")
    
    try:
        from cosmos.visualizer.dag_renderer import DAGRenderer
        results.append(test_result("Visualizer - Renderer imports", True))
    except ImportError as e:
        results.append(test_result("Visualizer - Renderer imports", False, str(e)))
        all_passed = False
    
    # ===========================================
    # TEST 9: Demo File
    # ===========================================
    print("\n[9] Demo")
    
    demo_path = Path("demo/demo.cosmos")
    if demo_path.exists():
        results.append(test_result("Demo file exists", True))
        try:
            content = demo_path.read_text()
            results.append(test_result("Demo file readable", len(content) > 0))
            results.append(test_result("Demo has provider", "provider" in content.lower()))
            results.append(test_result("Demo has task", "task" in content.lower()))
            all_passed = all_passed and len(content) > 0
        except Exception as e:
            results.append(test_result("Demo file readable", False, str(e)))
            all_passed = False
    else:
        results.append(test_result("Demo file exists", False, "demo/demo.cosmos not found"))
        all_passed = False
    
    # ===========================================
    # TEST 10: Tests Suite
    # ===========================================
    print("\n[10] Tests Suite")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no", "-x"],
            capture_output=True,
            text=True,
            timeout=60
        )
        tests_passed = result.returncode == 0
        results.append(test_result(
            "Unit tests pass",
            tests_passed,
            "run 'pytest tests/' for details" if not tests_passed else ""
        ))
        all_passed = all_passed and tests_passed
    except Exception as e:
        results.append(test_result("Unit tests pass", False, str(e)))
        all_passed = False
    
    # ===========================================
    # SUMMARY
    # ===========================================
    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r)
    total = len(results)
    
    if all_passed:
        print(f"  {GREEN}SMOKE TEST: PASS{RESET}")
        print(f"  {passed}/{total} checks passed")
    else:
        print(f"  {RED}SMOKE TEST: FAIL{RESET}")
        print(f"  {passed}/{total} checks passed")
    
    print("=" * 50 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
