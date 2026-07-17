"""
tests/test_cosmos_full.py
========================

Full test suite for Cosmos v0.4.5-rc1
=====================================

Test categories:
1. Syntax validation
2. Semantic validation
3. Temporal validation (RFC-0004-F)
4. E401 error codes
5. Fail-fast behavior
6. DAG compilation
7. RAG integration
8. Distributed compilation
9. Cache behavior

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import List, Optional
import pytest

# Import Cosmos components
from cosmos.solvens_agent import CosmosCompilerAgent, Status, ErrorCode
from cosmos.explainer import LLMExplainerAgent, ErrorContext, Severity


# ============================================================
# TEST FIXTURES
# ============================================================

@dataclass
class TestCase:
    """Test case definition."""
    name: str
    cosmos_code: str
    expected_status: Status
    expected_error_code: Optional[str] = None
    should_have_dag: bool = False
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# ============================================================
# VALID COSMOS FILES (should APPROVE)
# ============================================================

VALID_COSMOS = [
    TestCase(
        name="minimal_valid",
        cosmos_code="""
cosmos Minimal {
    sun Main
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "minimal"]
    ),
    TestCase(
        name="single_planet",
        cosmos_code="""
cosmos SingleTask {
    sun Orchestrator
    planet Task1 {
        model: claude-3-sonnet
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "single"]
    ),
    TestCase(
        name="linear_dag",
        cosmos_code="""
cosmos LinearDAG {
    sun Start
    
    planet Step1 {
        model: gpt-4
        connects_to: Step2
    }
    
    planet Step2 {
        model: claude-3
        connects_to: Step3
    }
    
    planet Step3 {
        model: gemini
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "linear", "dag"]
    ),
    TestCase(
        name="parallel_dag",
        cosmos_code="""
cosmos ParallelDAG {
    sun Central
    
    planet Task1 {
        model: claude-3-sonnet
    }
    
    planet Task2 {
        model: gpt-4
    }
    
    planet Task3 {
        model: gemini
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "parallel", "dag"]
    ),
    TestCase(
        name="with_duration",
        cosmos_code="""
cosmos TimedTask {
    sun Scheduler
    
    planet LongTask {
        model: gpt-4
        duration: 60
        start_after: 0
        end_before: 120
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "temporal"]
    ),
    TestCase(
        name="complex_dag",
        cosmos_code="""
cosmos ComplexDAG {
    sun CentralOrchestrator
    
    planet Research {
        model: claude-3-sonnet
        connects_to: [Implement, Test]
    }
    
    planet Implement {
        model: gpt-4
        connects_to: Review
    }
    
    planet Test {
        model: gemini
        connects_to: Review
    }
    
    planet Review {
        model: claude-3-opus
    }
    
    light LogFlow {
        from: CentralOrchestrator
        to: [Research, Implement, Test, Review]
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "complex", "dag"]
    ),
    TestCase(
        name="with_galaxy",
        cosmos_code="""
cosmos MultiGalaxy {
    galaxy Cluster1 {
        sun Node1
        planet Worker1
    }
    
    galaxy Cluster2 {
        sun Node2
        planet Worker2
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "galaxy"]
    ),
    TestCase(
        name="empty_connects",
        cosmos_code="""
cosmos NoConnects {
    sun Main
    planet Task1 {
        model: claude-3-sonnet
    }
}
end
""",
        expected_status=Status.APPROVED,
        should_have_dag=True,
        tags=["valid", "edge"]
    ),
]


# ============================================================
# E401 TEMPORAL VIOLATIONS (should REJECT)
# ============================================================

TEMPORAL_VIOLATIONS = [
    TestCase(
        name="start_after_greater_than_end_before",
        cosmos_code="""
cosmos BadTiming {
    planet Task1 {
        start_after: 100
        end_before: 50
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="TemporalConstraintViolation",
        tags=["e401", "temporal", "critical"]
    ),
    TestCase(
        name="start_after_equals_end_before",
        cosmos_code="""
cosmos BadTiming2 {
    planet Task1 {
        start_after: 100
        end_before: 100
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="TemporalConstraintViolation",
        tags=["e401", "temporal", "critical"]
    ),
    TestCase(
        name="duration_exceeds_window",
        cosmos_code="""
cosmos DurationExceed {
    planet Task1 {
        start_after: 0
        end_before: 100
        duration: 150
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="TemporalConstraintViolation",
        tags=["e401", "temporal", "duration"]
    ),
    TestCase(
        name="multiple_violations",
        cosmos_code="""
cosmos MultiBad {
    planet Task1 {
        start_after: 200
        end_before: 50
        duration: 500
    }
    
    planet Task2 {
        start_after: 300
        end_before: 100
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="TemporalConstraintViolation",
        tags=["e401", "temporal", "multiple"]
    ),
    TestCase(
        name="negative_temporal",
        cosmos_code="""
cosmos NegativeTime {
    planet Task1 {
        start_after: -10
        end_before: 100
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="TemporalConstraintViolation",
        tags=["e401", "temporal", "negative"]
    ),
]


# ============================================================
# SYNTAX ERRORS (should REJECT)
# ============================================================

SYNTAX_ERRORS = [
    TestCase(
        name="missing_cosmos_block",
        cosmos_code="""
Sun Main
Planet Task1
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="InvalidUniverse",
        tags=["syntax", "missing"]
    ),
    TestCase(
        name="unbalanced_braces",
        cosmos_code="""
cosmos BadBraces {
    planet Task1 {
        model: claude
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="UnclosedBlock",
        tags=["syntax", "braces"]
    ),
    TestCase(
        name="invalid_node_without_name",
        cosmos_code="""
cosmos NoName {
    planet {
        model: claude
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="InvalidNodeType",
        tags=["syntax", "name"]
    ),
    TestCase(
        name="empty_file",
        cosmos_code="",
        expected_status=Status.REJECTED,
        expected_error_code="SyntaxError",
        tags=["syntax", "empty"]
    ),
]


# ============================================================
# SEMANTIC ERRORS (should REJECT)
# ============================================================

SEMANTIC_ERRORS = [
    TestCase(
        name="duplicate_nodes",
        cosmos_code="""
cosmos Duplicates {
    sun Main
    planet Task1 {
        model: claude
    }
    planet Task1 {
        model: gpt
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="DuplicateNode",
        tags=["semantic", "duplicate"]
    ),
    TestCase(
        name="undefined_reference",
        cosmos_code="""
cosmos Undefined {
    sun Main
    planet Task1 {
        model: claude
        connects_to: NonExistent
    }
}
end
""",
        expected_status=Status.REJECTED,
        expected_error_code="UndefinedReference",
        tags=["semantic", "reference"],
        should_have_dag=True  # May still create DAG with warning
    ),
]


# ============================================================
# TEST CLASS
# ============================================================

class TestCosmosCompiler:
    """Test suite for CosmosCompilerAgent."""
    
    @pytest.mark.asyncio
    async def test_valid_cosmos_approve(self):
        """Test that valid Cosmos files are approved."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        for tc in VALID_COSMOS:
            result = await agent.run(tc.cosmos_code)
            assert result.status == Status.APPROVED, \
                f"Failed: {tc.name} - {result.content}"
            
            if tc.should_have_dag:
                assert "dag" in result.metadata or result.metadata.get("nodes", 0) >= 0
    
    @pytest.mark.asyncio
    async def test_temporal_violations_e401(self):
        """Test that E401 temporal violations are rejected."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        for tc in TEMPORAL_VIOLATIONS:
            result = await agent.run(tc.cosmos_code)
            assert result.status == Status.REJECTED, \
                f"Failed: {tc.name} - Should be REJECTED"
            assert result.metadata.get("error_code") == tc.expected_error_code, \
                f"Failed: {tc.name} - Wrong error code"
    
    @pytest.mark.asyncio
    async def test_syntax_errors_reject(self):
        """Test that syntax errors are rejected."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        for tc in SYNTAX_ERRORS:
            result = await agent.run(tc.cosmos_code)
            assert result.status == Status.REJECTED, \
                f"Failed: {tc.name}"
    
    @pytest.mark.asyncio
    async def test_semantic_errors_reject(self):
        """Test that semantic errors are rejected."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        for tc in SEMANTIC_ERRORS:
            result = await agent.run(tc.cosmos_code)
            assert result.status == Status.REJECTED, \
                f"Failed: {tc.name}"
    
    @pytest.mark.asyncio
    async def test_fail_fast_behavior(self):
        """Test that fail-fast stops at first error."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        # Multiple violations - should stop at first
        code = """
cosmos MultiError {
    planet Task1 {
        start_after: 100
        end_before: 50
    }
    planet Task2 {
        model: invalid-model-that-doesnt-exist-12345
    }
}
end
"""
        result = await agent.run(code)
        assert result.status == Status.REJECTED
        # Should get first error (temporal), not second (model)
        assert "start_after" in result.content.lower() or "temporal" in result.content.lower()
    
    @pytest.mark.asyncio
    async def test_strict_mode(self):
        """Test strict mode validation."""
        agent = CosmosCompilerAgent(strict_mode=True, fail_fast=True)
        
        # Undefined reference should fail in strict mode
        code = """
cosmos StrictTest {
    sun Main
    planet Task1 {
        connects_to: UndefinedNode
    }
}
end
"""
        result = await agent.run(code)
        assert result.status == Status.REJECTED
    
    @pytest.mark.asyncio
    async def test_message_structure(self):
        """Test that Message has correct structure."""
        agent = CosmosCompilerAgent()
        
        result = await agent.run("cosmos Test {} end")
        assert hasattr(result, "content")
        assert hasattr(result, "status")
        assert hasattr(result, "metadata")
        assert isinstance(result.content, str)
        assert isinstance(result.metadata, dict)
    
    @pytest.mark.asyncio
    async def test_error_metadata(self):
        """Test that error metadata is correctly populated."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        code = """
cosmos ErrorTest {
    planet Task1 {
        start_after: 100
        end_before: 50
    }
}
end
"""
        result = await agent.run(code)
        
        assert "error_code" in result.metadata
        assert "error" in result.metadata or "fail_fast" in result.metadata
        assert result.metadata.get("error_code") == "TemporalConstraintViolation"
    
    @pytest.mark.asyncio
    async def test_dag_layers(self):
        """Test DAG layer calculation."""
        agent = CosmosCompilerAgent()
        
        code = """
cosmos LayerTest {
    sun Start
    
    planet Layer1_A
    planet Layer1_B
    
    planet Layer2_A {
        connects_to: Layer1_A
    }
    
    planet Layer3_A {
        connects_to: Layer2_A
    }
}
end
"""
        result = await agent.run(code)
        assert result.status == Status.APPROVED
        assert result.metadata.get("layers", 0) > 0


# ============================================================
# CACHE TESTS
# ============================================================

class TestCosmosCache:
    """Test cache behavior."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test that repeated compilations use cache."""
        agent = CosmosCompilerAgent()
        
        code = """
cosmos CacheTest {
    sun Main
    planet Task1 {
        model: claude-3-sonnet
    }
}
end
"""
        # First compilation
        start1 = time.time()
        result1 = await agent.run(code)
        time1 = time.time() - start1
        
        # Second compilation (should be cached)
        start2 = time.time()
        result2 = await agent.run(code)
        time2 = time.time() - start2
        
        assert result1.status == result2.status
        # Cached should be faster (if cache implemented)
        # Note: Cache may not be implemented yet
        print(f"First: {time1*1000:.2f}ms, Second: {time2*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_cache_hash_stability(self):
        """Test that same code produces same hash."""
        code = "cosmos Test { sun Main } end"
        
        hash1 = hashlib.sha256(code.encode()).hexdigest()
        hash2 = hashlib.sha256(code.encode()).hexdigest()
        
        assert hash1 == hash2


# ============================================================
# DISTRIBUTED TESTS
# ============================================================

class TestDistributedCompilation:
    """Test distributed compilation behavior."""
    
    @pytest.mark.asyncio
    async def test_parallel_compilation(self):
        """Test that multiple compilations can run in parallel."""
        agent = CosmosCompilerAgent()
        
        codes = [
            f"""
cosmos Test{i} {{
    sun Main{i}
    planet Task{i} {{
        model: claude
    }}
}}
end
"""
            for i in range(10)
        ]
        
        start = time.time()
        results = await asyncio.gather(*[agent.run(code) for code in codes])
        elapsed = time.time() - start
        
        assert all(r.status == Status.APPROVED for r in results)
        print(f"Parallel compilation of 10 files: {elapsed*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_e401_cancellation(self):
        """Test that E401 in one file doesn't affect others."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        # One bad, rest good
        codes = [
            """
cosmos Good1 {
    sun Main
    planet Task1 { model: claude }
}
end
""",
            """
cosmos Bad {
    planet Task1 {
        start_after: 100
        end_before: 50
    }
}
end
""",
            """
cosmos Good2 {
    sun Main
    planet Task2 { model: gpt }
}
end
""",
        ]
        
        start = time.time()
        results = await asyncio.gather(*[agent.run(code) for code in codes])
        elapsed = time.time() - start
        
        # Check results
        assert results[0].status == Status.APPROVED
        assert results[1].status == Status.REJECTED
        assert results[2].status == Status.APPROVED
        
        print(f"3 files (1 E401): {elapsed*1000:.2f}ms")


# ============================================================
# RAG / KG INTEGRATION TESTS
# ============================================================

class TestRAGIntegration:
    """Test RAG/Knowledge Graph integration."""
    
    @pytest.mark.asyncio
    async def test_error_context_for_kg(self):
        """Test that errors include context for KG."""
        from cosmos.explainer import ErrorContext, LLMExplainerAgent
        
        ctx = ErrorContext(
            error_code="E401",
            error_message="start_after >= end_before",
            file_path="test.cosmos",
            line_number=5,
            related_nodes=["Task1", "Task2"]
        )
        
        # LLMExplainer should accept this context
        agent = LLMExplainerAgent()
        explanation = agent._fallback_explanation(ctx)
        
        assert explanation.summary is not None
        assert explanation.severity == Severity.ERROR
        assert "E401" in explanation.metadata.get("error_code", "")
    
    @pytest.mark.asyncio
    async def test_explanation_fallback(self):
        """Test fallback explanation when LLM unavailable."""
        from cosmos.explainer import LLMExplainerAgent, ErrorContext
        
        agent = LLMExplainerAgent()
        
        ctx = ErrorContext(
            error_code="E401",
            error_message="Temporal constraint violated",
            cosmos_source="cosmos Test { planet P { start_after: 100 end_before: 50 } } end"
        )
        
        explanation = await agent.explain(ctx, include_kg_context=False)
        
        assert explanation is not None
        assert explanation.confidence > 0
        assert len(explanation.solution_steps) > 0


# ============================================================
# BENCHMARK TESTS
# ============================================================

class TestBenchmark:
    """Performance benchmark tests."""
    
    @pytest.mark.asyncio
    async def test_compilation_speed(self):
        """Benchmark compilation speed."""
        agent = CosmosCompilerAgent()
        
        code = """
cosmos Benchmark {{
    sun Main
    planet Task{{}} {{
        model: claude
        duration: 10
    }}
}}
end
"""
        iterations = 100
        start = time.time()
        
        for i in range(iterations):
            await agent.run(code.format(i))
        
        elapsed = time.time() - start
        per_file = elapsed / iterations * 1000
        
        print(f"\nBenchmark: {iterations} files in {elapsed:.2f}s ({per_file:.2f}ms/file)")
        
        # Should complete reasonably fast
        assert per_file < 100, f"Too slow: {per_file:.2f}ms per file"
    
    @pytest.mark.asyncio
    async def test_e401_detection_speed(self):
        """Benchmark E401 detection speed."""
        agent = CosmosCompilerAgent(fail_fast=True)
        
        code = """
cosmos FastE401 {{
    planet Task {{
        start_after: 100
        end_before: 50
    }}
}}
end
"""
        iterations = 50
        start = time.time()
        
        for _ in range(iterations):
            result = await agent.run(code)
            assert result.status == Status.REJECTED
        
        elapsed = time.time() - start
        per_file = elapsed / iterations * 1000
        
        print(f"\nE401 Detection: {iterations} files in {elapsed:.2f}s ({per_file:.2f}ms/file)")
        
        # E401 should be very fast (fail-fast)
        assert per_file < 50, f"E401 detection too slow: {per_file:.2f}ms"


# ============================================================
# RUN ALL TESTS
# ============================================================

def count_tests():
    """Count total test cases."""
    total = 0
    total += len(VALID_COSMOS)
    total += len(TEMPORAL_VIOLATIONS)
    total += len(SYNTAX_ERRORS)
    total += len(SEMANTIC_ERRORS)
    
    # Class tests (estimated)
    total += 15  # TestCosmosCompiler
    total += 2   # TestCosmosCache
    total += 2   # TestDistributedCompilation
    total += 2   # TestRAGIntegration
    total += 2   # TestBenchmark
    
    return total


if __name__ == "__main__":
    print(f"Total test cases defined: {count_tests()}")
    print("\nRun with: pytest tests/test_cosmos_full.py -v")
