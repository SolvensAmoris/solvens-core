"""
SOLVENS Integration Tests

Tests the complete workflow: init -> compile -> validate -> simulate -> explain
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos.parser.parser import Parser


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_workflow():
    return '''
provider claude {
  type = "anthropic"
  model = "claude-3-5-sonnet"
}

task hello {
  provider = "claude"
  depends_on = []
}

task world {
  provider = "claude"
  depends_on = [hello]
}
'''


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# =============================================================================
# PARSER TESTS
# =============================================================================

class TestParser:
    """Test Cosmos parser."""
    
    def test_parse_provider(self, sample_workflow):
        """Test parsing a provider declaration."""
        parser = Parser(sample_workflow)
        ast = parser.parse()
        assert ast is not None
        assert len(ast.statements) >= 1
    
    def test_parse_empty(self):
        """Test parsing empty source."""
        parser = Parser("")
        ast = parser.parse()
        assert ast.statements == []
    
    def test_parse_comments(self):
        """Test parsing comments."""
        parser = Parser("# This is a comment")
        ast = parser.parse()
        assert len(ast.statements) == 0


# =============================================================================
# CLI TESTS
# =============================================================================

class TestCLI:
    """Test CLI commands."""
    
    def test_cli_module(self):
        """Test that CLI module exists."""
        import solvens.cli
        assert solvens.cli is not None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_workflow_parse_and_validate(self, sample_workflow):
        """Test complete workflow parsing and validation."""
        parser = Parser(sample_workflow)
        ast = parser.parse()
        
        # Should have provider + 2 tasks
        assert len(ast.statements) == 3
        
        # Should not raise errors
        assert ast is not None


# =============================================================================
# COST SAFETY TESTS
# =============================================================================

class TestCostSafety:
    """Test cost safety mechanisms."""
    
    def test_cost_estimator_import(self):
        """Test cost estimator can be imported."""
        from cosmos.runtime.cost_safety import CostEstimator
        assert CostEstimator is not None
    
    def test_cost_estimation(self):
        """Test cost estimation."""
        from cosmos.runtime.cost_safety import CostEstimator
        
        estimator = CostEstimator()
        estimate = estimator.estimate_workflow(
            workflow_name="test",
            tasks=[
                {"provider": "anthropic", "model": "claude-3-5-sonnet", "complexity": "medium"}
            ],
            dag_depth=1,
        )
        
        assert estimate.estimated_cost_usd > 0
        assert estimate.estimated_time_ms > 0


# =============================================================================
# RBAC TESTS
# =============================================================================

class TestRBAC:
    """Test RBAC system."""
    
    def test_rbac_import(self):
        """Test RBAC can be imported."""
        from cosmos.security.rbac import rbac, Role, Permission
        assert rbac is not None
        assert len(Role) == 6
    
    def test_role_hierarchy(self):
        """Test role hierarchy."""
        from cosmos.security.rbac import Role
        
        # OWNER should be highest
        assert Role.OWNER is not None
        assert Role.VIEWER is not None
    
    def test_api_key_creation(self):
        """Test API key creation."""
        from cosmos.security.rbac import RBAC, Role
        
        import os
        os.environ["SOLVENS_RBAC_BOOTSTRAP_TOKEN"] = "test-bootstrap-secret"
        rbac = RBAC()
        team = rbac.create_team("Test Team", bootstrap_token="test-bootstrap-secret")
        owner = rbac.create_user("owner@example.com", team.id, Role.OWNER, bootstrap_token="test-bootstrap-secret")
        user = rbac.create_user("test@example.com", team.id, Role.DEVELOPER, actor_id=owner.id)
        
        api_key, raw_key = rbac.create_api_key(
            user_id=user.id,
            name="Test Key",
            scopes=["workflow:run", "provider:view"],
            actor_id=user.id,
        )
        
        assert api_key is not None
        assert raw_key.startswith("sk_solvens_")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
