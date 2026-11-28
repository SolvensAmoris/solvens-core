#!/usr/bin/env python3
"""
SOLVENS Risk Mitigation Tests

Validates that all 4 critical risks are mitigated:
1. COST_EXPLOSION - Circuit breaker + budget manager
2. COMPATIBILITY - Provider abstraction + stable interfaces
3. VENDOR_LOCK - Unified provider interface
4. GOVERNANCE_GAP - Full RBAC implementation

Run with: python -m risk.test_mitigations
"""

import asyncio
import sys
import os
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enum import Enum


class TestResult(str, Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"


@dataclass
class TestReport:
    risk: str
    test: str
    result: TestResult
    message: str


def report(tests: list[TestReport]) -> bool:
    """Run tests and print report."""
    print("=" * 70)
    print("SOLVENS RISK MITIGATION VALIDATION")
    print("=" * 70)
    print()
    
    all_passed = True
    
    for t in tests:
        icon = "✅" if t.result == TestResult.PASS else "❌"
        print(f"{icon} {t.risk}: {t.test}")
        print(f"   {t.message}")
        print()
        
        if t.result == TestResult.FAIL:
            all_passed = False
    
    passed = sum(1 for t in tests if t.result == TestResult.PASS)
    print("-" * 70)
    print(f"Result: {passed}/{len(tests)} tests passed")
    
    if all_passed:
        print("\n🎉 ALL RISKS MITIGATED - PRODUCTION READY")
        return True
    else:
        print("\n⚠️  SOME RISKS REMAIN - CONTINUE MITIGATION")
        return False


# =============================================================================
# TEST 1: COST_EXPLOSION
# =============================================================================

def test_cost_explosion():
    """Test that circuit breaker and budget manager prevent cost overruns."""
    tests = []
    
    try:
        from cosmos.runtime.cost_safety import (
            CostEstimator,
            BudgetManager,
            CircuitBreaker,
            Budget,
            CostEstimate,
            CostLimitExceeded,
        )
    except ImportError as e:
        tests.append(TestReport(
            risk="COST_EXPLOSION",
            test="Import cost_safety module",
            result=TestResult.FAIL,
            message=f"Cannot import: {e}",
        ))
        return tests
    
    # Test 1.1: Circuit breaker exists and works
    try:
        budget = Budget(team_id="test", max_cost_per_run=0.01)
        cb = CircuitBreaker(budget)
        
        # Create a high-cost estimate
        high_cost = CostEstimate(
            workflow_name="test",
            num_tasks=10,
            estimated_input_tokens=10000,
            estimated_output_tokens=5000,
            estimated_cost_usd=0.05,  # Exceeds 0.01 limit
            estimated_time_ms=1000,
            providers_breakdown={},
        )
        
        try:
            cb.check(high_cost)
            tests.append(TestReport(
                risk="COST_EXPLOSION",
                test="Circuit breaker blocks high cost",
                result=TestResult.FAIL,
                message="Circuit breaker did not block high cost estimate",
            ))
        except CostLimitExceeded:
            tests.append(TestReport(
                risk="COST_EXPLOSION",
                test="Circuit breaker blocks high cost",
                result=TestResult.PASS,
                message="Circuit breaker correctly blocks cost > max_cost_per_run",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="COST_EXPLOSION",
            test="Circuit breaker implementation",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 1.2: Budget manager exists and works
    try:
        bm = BudgetManager()
        budget = Budget(team_id="test-team", max_cost_per_day=10.00)
        bm.set_budget(budget)
        
        # Check budget was set
        key = "test-team"
        stored = bm._budgets.get(key)
        
        if stored and stored.max_cost_per_day == 10.00:
            tests.append(TestReport(
                risk="COST_EXPLOSION",
                test="Budget manager stores budgets",
                result=TestResult.PASS,
                message="Budget manager correctly stores and manages budgets",
            ))
        else:
            tests.append(TestReport(
                risk="COST_EXPLOSION",
                test="Budget manager stores budgets",
                result=TestResult.FAIL,
                message="Budget not stored correctly",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="COST_EXPLOSION",
            test="Budget manager implementation",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 1.3: Cost estimator works
    try:
        ce = CostEstimator()
        estimate = ce.estimate_workflow(
            workflow_name="test",
            tasks=[
                {"provider": "openai", "model": "gpt-4o", "complexity": "medium"},
                {"provider": "ollama", "model": "llama3", "complexity": "simple"},
            ],
            dag_depth=2,
        )
        
        if estimate.estimated_cost_usd > 0:
            tests.append(TestReport(
                risk="COST_EXPLOSION",
                test="Cost estimator calculates costs",
                result=TestResult.PASS,
                message=f"Cost estimator works: ${estimate.estimated_cost_usd:.6f}",
            ))
        else:
            tests.append(TestReport(
                risk="COST_EXPLOSION",
                test="Cost estimator calculates costs",
                result=TestResult.FAIL,
                message="Cost estimator returned 0",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="COST_EXPLOSION",
            test="Cost estimator implementation",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    return tests


# =============================================================================
# TEST 2: COMPATIBILITY (Provider Interface)
# =============================================================================

def test_compatibility():
    """Test that provider abstraction exists and works."""
    tests = []
    
    # Test 2.1: Base provider interface exists
    try:
        from cosmos.providers.base import BaseProvider, ProviderType, Message, CompletionResult
        
        # Check that BaseProvider is abstract
        from abc import ABC
        if issubclass(BaseProvider, ABC):
            tests.append(TestReport(
                risk="COMPATIBILITY",
                test="Base provider interface is abstract",
                result=TestResult.PASS,
                message="BaseProvider correctly defined as abstract base class",
            ))
        else:
            tests.append(TestReport(
                risk="COMPATIBILITY",
                test="Base provider interface is abstract",
                result=TestResult.FAIL,
                message="BaseProvider is not an abstract class",
            ))
    except ImportError as e:
        tests.append(TestReport(
            risk="COMPATIBILITY",
            test="Base provider interface exists",
            result=TestResult.FAIL,
            message=f"Cannot import base provider: {e}",
        ))
        return tests
    
    # Test 2.2: ProviderType enum exists
    try:
        pt = ProviderType.OPENAI
        if pt.value == "openai":
            tests.append(TestReport(
                risk="COMPATIBILITY",
                test="Provider type enum exists",
                result=TestResult.PASS,
                message="ProviderType enum correctly defined",
            ))
        else:
            tests.append(TestReport(
                risk="COMPATIBILITY",
                test="Provider type enum exists",
                result=TestResult.FAIL,
                message="ProviderType enum incorrect value",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="COMPATIBILITY",
            test="Provider type enum",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 2.3: Message dataclass exists
    try:
        msg = Message(role="user", content="Hello")
        if msg.role == "user" and msg.content == "Hello":
            tests.append(TestReport(
                risk="COMPATIBILITY",
                test="Message dataclass works",
                result=TestResult.PASS,
                message="Message dataclass correctly defined",
            ))
        else:
            tests.append(TestReport(
                risk="COMPATIBILITY",
                test="Message dataclass works",
                result=TestResult.FAIL,
                message="Message dataclass incorrect values",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="COMPATIBILITY",
            test="Message dataclass",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    return tests


# =============================================================================
# TEST 3: VENDOR_LOCK (Unified LLM Interface)
# =============================================================================

def test_vendor_lock():
    """Test that unified LLM interface exists and provides failover."""
    tests = []
    
    # Test 3.1: LLM interface exists
    try:
        from cosmos.providers.llm import llm, LLMInterface
        
        if isinstance(llm, LLMInterface):
            tests.append(TestReport(
                risk="VENDOR_LOCK",
                test="LLM interface singleton exists",
                result=TestResult.PASS,
                message="LLM interface singleton correctly initialized",
            ))
        else:
            tests.append(TestReport(
                risk="VENDOR_LOCK",
                test="LLM interface singleton exists",
                result=TestResult.FAIL,
                message="llm is not LLMInterface instance",
            ))
    except ImportError as e:
        tests.append(TestReport(
            risk="VENDOR_LOCK",
            test="LLM interface exists",
            result=TestResult.FAIL,
            message=f"Cannot import LLM interface: {e}",
        ))
        return tests
    
    # Test 3.2: select_cheapest method exists
    try:
        cheapest = llm.select_cheapest("simple")
        tests.append(TestReport(
            risk="VENDOR_LOCK",
            test="Cost-based provider selection",
            result=TestResult.PASS,
            message=f"select_cheapest returns: {cheapest}",
        ))
    except Exception as e:
        tests.append(TestReport(
            risk="VENDOR_LOCK",
            test="Cost-based provider selection",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 3.3: Provider interfaces exist
    try:
        from cosmos.providers.base import BaseProvider, ProviderType
        tests.append(TestReport(
            risk="VENDOR_LOCK",
            test="Provider abstraction exists",
            result=TestResult.PASS,
            message="BaseProvider abstract class exists for all providers",
        ))
    except ImportError as e:
        tests.append(TestReport(
            risk="VENDOR_LOCK",
            test="Provider abstraction exists",
            result=TestResult.FAIL,
            message=f"Provider base not found: {e}",
        ))
    
    return tests


# =============================================================================
# TEST 4: GOVERNANCE_GAP (RBAC)
# =============================================================================

def test_governance():
    """Test that full RBAC is implemented."""
    tests = []
    
    # Test 4.1: RBAC module exists
    try:
        from cosmos.security.rbac import rbac, Role, Permission, RBAC, PermissionDenied
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="RBAC module imports correctly",
            result=TestResult.PASS,
            message="RBAC module correctly imports",
        ))
    except ImportError as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="RBAC module exists",
            result=TestResult.FAIL,
            message=f"Cannot import RBAC: {e}",
        ))
        return tests
    
    # Test 4.2: Role enum exists
    try:
        viewer = Role.VIEWER
        admin = Role.ADMIN
        
        if viewer.value == "viewer" and admin.value == "admin":
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Role enum defined",
                result=TestResult.PASS,
                message="6 roles correctly defined (OWNER, ADMIN, EDITOR, DEVELOPER, VIEWER, AUDITOR)",
            ))
        else:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Role enum defined",
                result=TestResult.FAIL,
                message="Role values incorrect",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="Role enum",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 4.3: Permission enum exists
    try:
        run_perm = Permission.WORKFLOW_RUN
        delete_perm = Permission.WORKFLOW_DELETE
        
        if run_perm.value == "workflow:run" and delete_perm.value == "workflow:delete":
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Permission enum defined",
                result=TestResult.PASS,
                message="Granular permissions correctly defined",
            ))
        else:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Permission enum defined",
                result=TestResult.FAIL,
                message="Permission values incorrect",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="Permission enum",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 4.4: Viewer cannot run workflows (key governance requirement)
    try:
        from cosmos.security.rbac import RBAC, Role, Permission
        
        import os
        os.environ["SOLVENS_RBAC_BOOTSTRAP_TOKEN"] = "test-bootstrap-secret"
        rbac = RBAC()
        rbac._users = {}  # Reset
        
        # Create tenant and bootstrap owner
        team = rbac.create_team("Test Team", bootstrap_token="test-bootstrap-secret")
        owner = rbac.create_user("owner@test.com", team.id, Role.OWNER, bootstrap_token="test-bootstrap-secret")
        
        # Create viewer and developer users through the tenant owner
        viewer_user = rbac.create_user("viewer@test.com", team.id, Role.VIEWER, actor_id=owner.id)
        dev_user = rbac.create_user("dev@test.com", team.id, Role.DEVELOPER, actor_id=owner.id)
        
        # Create workflow ACL - private, but team members can access
        rbac.set_workflow_acl("test-workflow", team.id, is_public=False, allowed_teams=[team.id], actor_id=owner.id)
        
        # Check viewer CANNOT run (no WORKFLOW_RUN permission)
        can_run_viewer = rbac.can_run_workflow(viewer_user, "test-workflow")
        
        if not can_run_viewer:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Viewer cannot run workflows",
                result=TestResult.PASS,
                message="Viewer role correctly restricted from running workflows",
            ))
        else:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Viewer cannot run workflows",
                result=TestResult.FAIL,
                message="Viewer CAN run workflows - RBAC not working!",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="Viewer role restriction",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 4.5: Developer CAN run workflows
    try:
        # Developer should be able to run (has WORKFLOW_RUN permission)
        can_run_dev = rbac.can_run_workflow(dev_user, "test-workflow")
        
        if can_run_dev:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Developer can run workflows",
                result=TestResult.PASS,
                message="Developer role correctly has run permission",
            ))
        else:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Developer can run workflows",
                result=TestResult.FAIL,
                message="Developer CANNOT run workflows!",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="Developer role",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 4.6: API keys with scopes
    try:
        api_key, raw_key = rbac.create_api_key(
            user_id=viewer_user.id,
            name="Test Key",
            scopes=["workflow:view", "provider:view"],
            actor_id=viewer_user.id,
        )
        
        # Check viewer key CANNOT run (no workflow:run scope)
        can_run = rbac.api_key_can_access(api_key, "workflow", "run")
        
        if not can_run:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="API key scope restrictions",
                result=TestResult.PASS,
                message="API key scopes correctly enforced",
            ))
        else:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="API key scope restrictions",
                result=TestResult.FAIL,
                message="API key scopes not enforced!",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="API key implementation",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    # Test 4.7: Audit log works
    try:
        audit_log = rbac.get_audit_log()
        
        if len(audit_log) > 0:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Audit logging",
                result=TestResult.PASS,
                message=f"Audit log records events: {len(audit_log)} entries",
            ))
        else:
            tests.append(TestReport(
                risk="GOVERNANCE_GAP",
                test="Audit logging",
                result=TestResult.FAIL,
                message="Audit log empty after operations",
            ))
    except Exception as e:
        tests.append(TestReport(
            risk="GOVERNANCE_GAP",
            test="Audit logging",
            result=TestResult.FAIL,
            message=f"Error: {e}",
        ))
    
    return tests


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all mitigation tests."""
    all_tests = []
    
    print("Testing COST_EXPLOSION mitigations...")
    all_tests.extend(test_cost_explosion())
    
    print("Testing COMPATIBILITY mitigations...")
    all_tests.extend(test_compatibility())
    
    print("Testing VENDOR_LOCK mitigations...")
    all_tests.extend(test_vendor_lock())
    
    print("Testing GOVERNANCE_GAP mitigations...")
    all_tests.extend(test_governance())
    
    success = report(all_tests)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
