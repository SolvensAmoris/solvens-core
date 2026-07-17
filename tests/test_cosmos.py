"""
Tests for COSMOS Parser, AST, DAG, and Router
"""

import pytest
from cosmos.parser.lexer import Lexer, TokenType
from cosmos.parser.parser import Parser
from cosmos.parser.grammar import Grammar
from cosmos.ast import Program, TaskDecl, Property
from cosmos.dag import DAG, build_dag_from_ast, CycleError
from cosmos.router import Provider, ProviderCapability, ProviderRouter, RouteRequest, RoutingPolicy


class TestLexer:
    """Tests for the Lexer."""
    
    def test_identifiers(self):
        lexer = Lexer("task my_task")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.TASK
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "my_task"
    
    def test_strings(self):
        lexer = Lexer('provider = "openai"')
        tokens = lexer.tokenize()
        assert tokens[2].type == TokenType.STRING
        assert tokens[2].value == "openai"
    
    def test_numbers(self):
        lexer = Lexer("retry = 3")
        tokens = lexer.tokenize()
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == "3"
    
    def test_braces(self):
        lexer = Lexer("task test {}")
        tokens = lexer.tokenize()
        assert tokens[2].type == TokenType.LBRACE
        assert tokens[3].type == TokenType.RBRACE
    
    def test_keywords(self):
        lexer = Lexer("task agent provider dag depends_on retry timeout")
        tokens = lexer.tokenize()
        assert all(t.type != TokenType.IDENTIFIER for t in tokens[:-1])


class TestParser:
    """Tests for the Parser."""
    
    def test_parse_empty_program(self):
        parser = Parser("")
        ast = parser.parse()
        assert isinstance(ast, Program)
        assert len(ast.statements) == 0
    
    def test_parse_single_task(self):
        source = '''
        task process_data {
            provider = "openai"
        }
        '''
        parser = Parser(source)
        ast = parser.parse()
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], TaskDecl)
        assert ast.statements[0].name == "process_data"
    
    def test_parse_task_with_dependencies(self):
        source = '''
        task analyze {
            provider = "claude"
            depends_on = [fetch_data, validate]
        }
        '''
        parser = Parser(source)
        ast = parser.parse()
        task = ast.statements[0]
        assert task.name == "analyze"
        
        deps = next(p for p in task.properties if p.name == "depends_on")
        assert deps.value == ["fetch_data", "validate"]
    
    def test_parse_task_with_retry(self):
        source = '''
        task backup {
            retry = 5
            timeout = 60
        }
        '''
        parser = Parser(source)
        ast = parser.parse()
        task = ast.statements[0]
        
        retry = next(p for p in task.properties if p.name == "retry")
        timeout = next(p for p in task.properties if p.name == "timeout")
        assert retry.value == 5
        assert timeout.value == 60


class TestGrammar:
    """Tests for Grammar."""
    
    def test_validate_balanced_braces(self):
        assert Grammar.validate_syntax("task test {}") == True
        assert Grammar.validate_syntax("task test {") == False
    
    def test_validate_balanced_brackets(self):
        assert Grammar.validate_syntax("depends_on = [a, b]") == True
        assert Grammar.validate_syntax("depends_on = [a, b") == False
    
    def test_validate_balanced_parens(self):
        assert Grammar.validate_syntax("fn() {}") == True
        assert Grammar.validate_syntax("fn( {}") == False


class TestDAG:
    """Tests for DAG."""
    
    def test_add_node(self):
        dag = DAG()
        dag.add_node("a")
        assert "a" in dag.nodes
    
    def test_add_edge(self):
        dag = DAG()
        dag.add_edge("a", "b")
        assert "b" in dag.edges["a"]
        assert "a" in dag.reverse_edges["b"]
    
    def test_topological_sort_deterministic(self):
        """Test that topological sort is deterministic."""
        dag = DAG()
        dag.add_edge("c", "a")
        dag.add_edge("b", "a")
        dag.add_edge("a", "d")
        
        result1 = dag.topological_sort()
        result2 = dag.topological_sort()
        assert result1 == result2
    
    def test_topological_sort_linear(self):
        """Test simple linear dependency."""
        dag = DAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        
        result = dag.topological_sort()
        assert result.index("a") < result.index("b") < result.index("c")
    
    def test_detect_cycle(self):
        """Test cycle detection."""
        dag = DAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        dag.add_edge("c", "a")
        
        assert dag.has_cycle() == True
    
    def test_no_cycle(self):
        """Test no false positive for cycle."""
        dag = DAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        
        assert dag.has_cycle() == False
    
    def test_topological_sort_cycle_error(self):
        """Test that topological_sort raises on cycle."""
        dag = DAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "a")
        
        with pytest.raises(CycleError):
            dag.topological_sort()
    
    def test_get_dependencies(self):
        dag = DAG()
        dag.add_edge("a", "b")  # a depends on b
        dag.add_edge("a", "c")  # a depends on c
        
        deps = dag.get_dependencies("a")
        assert "b" in deps
        assert "c" in deps
    
    def test_transitive_dependencies(self):
        dag = DAG()
        dag.add_edge("a", "b")  # a depends on b
        dag.add_edge("b", "c")  # b depends on c
        dag.add_edge("a", "d")  # a depends on d
        
        transitive = dag.get_transitive_dependencies("a")
        assert "b" in transitive
        assert "c" in transitive
        assert "d" in transitive


class TestProviderRouter:
    """Tests for Provider Router."""
    
    def test_register_provider(self):
        router = ProviderRouter()
        provider = Provider(
            name="test",
            model="test-model",
            capabilities=[ProviderCapability.TEXT],
            cost_per_1k_tokens=0.01,
            latency_ms_avg=100
        )
        router.register_provider(provider)
        
        assert router.get_provider("test") == provider
    
    def test_list_providers(self):
        router = ProviderRouter()
        providers = router.list_providers()
        assert len(providers) >= 4  # Default providers
    
    def test_route_cost_optimized(self):
        router = ProviderRouter(policy=RoutingPolicy.COST_OPTIMIZED)
        request = RouteRequest(
            task_type="text",
            required_capabilities=[ProviderCapability.TEXT]
        )
        
        result = router.route(request)
        assert result.provider is not None
        assert result.policy_used == RoutingPolicy.COST_OPTIMIZED
    
    def test_route_latency_optimized(self):
        router = ProviderRouter(policy=RoutingPolicy.LATENCY_OPTIMIZED)
        request = RouteRequest(
            task_type="text",
            required_capabilities=[ProviderCapability.TEXT]
        )
        
        result = router.route(request)
        assert result.provider is not None
        assert result.policy_used == RoutingPolicy.LATENCY_OPTIMIZED
    
    def test_route_by_capability(self):
        router = ProviderRouter()
        request = RouteRequest(
            task_type="vision",
            required_capabilities=[ProviderCapability.VISION]
        )
        
        result = router.route(request)
        assert result.provider is not None
        assert result.provider.supports(ProviderCapability.VISION)
    
    def test_route_no_capability(self):
        """Test routing when no provider has required capability."""
        # Create a router with no providers
        router = ProviderRouter()
        router.providers = {}
        
        request = RouteRequest(
            task_type="unknown",
            required_capabilities=[ProviderCapability.SPEECH]
        )
        
        result = router.route(request)
        assert result.provider is None
    
    def test_fallback(self):
        router = ProviderRouter()
        ollama = router.get_provider("ollama")
        
        fallback = router.get_fallback(ollama)
        assert fallback is not None
        assert fallback.name != "ollama"


class TestIntegration:
    """Integration tests."""
    
    def test_parse_and_build_dag(self):
        """Test parsing a COSMOS program and building a DAG."""
        source = '''
        task fetch {
            provider = "openai"
        }
        
        task process {
            provider = "claude"
            depends_on = [fetch]
        }
        
        task analyze {
            provider = "gemini"
            depends_on = [process]
        }
        '''
        
        parser = Parser(source)
        ast = parser.parse()
        
        dag = build_dag_from_ast(ast.statements)
        
        assert "fetch" in dag.nodes
        assert "process" in dag.nodes
        assert "analyze" in dag.nodes
        
        # Verify dependencies: process depends on fetch
        assert "fetch" in dag.get_dependencies("process")
        # Verify dependencies: analyze depends on process
        assert "process" in dag.get_dependencies("analyze")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
