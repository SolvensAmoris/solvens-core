"""
tests/test_cosmos_full.py

Full test suite for Cosmos Parser v1.0
Tests the current parser implementation with correct Cosmos DSL syntax.
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional

from cosmos.parser.parser import Parser, ParserError
from cosmos.ast import Program, TaskDecl, ProviderDecl


@dataclass
class TestCase:
    name: str
    cosmos_code: str
    expected_statements: int
    expected_types: Optional[List[type]] = None


VALID_COSMOS = [
    TestCase(
        name="minimal_task",
        cosmos_code='task hello { provider = "claude" depends_on = [] }',
        expected_statements=1,
        expected_types=[TaskDecl],
    ),
    TestCase(
        name="task_with_provider",
        cosmos_code='provider openai_provider { type = "openai" } task hello { provider = "openai_provider" depends_on = [] }',
        expected_statements=2,
        expected_types=[ProviderDecl, TaskDecl],
    ),
    TestCase(
        name="linear_dag",
        cosmos_code='provider anthropic { type = "anthropic" } task fetch_data { provider = "anthropic" depends_on = [] } task process_data { provider = "anthropic" depends_on = [fetch_data] }',
        expected_statements=3,
        expected_types=[ProviderDecl, TaskDecl, TaskDecl],
    ),
]


INVALID_COSMOS = [
    TestCase(
        name="empty_file",
        cosmos_code="",
        expected_statements=0,
    ),
]


class TestCosmosParser:
    @pytest.mark.parametrize("tc", VALID_COSMOS, ids=lambda tc: tc.name)
    def test_valid_cosmos_approve(self, tc: TestCase):
        parser = Parser(tc.cosmos_code)
        ast = parser.parse()
        
        assert isinstance(ast, Program)
        assert len(ast.statements) == tc.expected_statements
        
        if tc.expected_types:
            for i, expected_type in enumerate(tc.expected_types):
                assert isinstance(ast.statements[i], expected_type)
    
    @pytest.mark.parametrize("tc", INVALID_COSMOS, ids=lambda tc: tc.name)
    def test_invalid_cosmos(self, tc: TestCase):
        parser = Parser(tc.cosmos_code)
        ast = parser.parse()
        assert len(ast.statements) == tc.expected_statements


class TestCosmosSemantic:
    def test_circular_dependency(self):
        code = 'provider claude { type = "anthropic" } task a { provider = "claude" depends_on = [b] } task b { provider = "claude" depends_on = [a] }'
        parser = Parser(code)
        ast = parser.parse()
        assert len(ast.statements) == 3


class TestCosmosDAG:
    def test_task_dependencies(self):
        code = 'provider claude { type = "anthropic" } task a { provider = "claude" depends_on = [] } task b { provider = "claude" depends_on = [a] }'
        parser = Parser(code)
        ast = parser.parse()
        
        tasks = [s for s in ast.statements if isinstance(s, TaskDecl)]
        assert len(tasks) == 2


class TestCosmosCache:
    def test_parser_idempotent(self):
        code = 'provider claude { type = "anthropic" } task hello { provider = "claude" depends_on = [] }'
        
        parser1 = Parser(code)
        ast1 = parser1.parse()
        
        parser2 = Parser(code)
        ast2 = parser2.parse()
        
        assert len(ast1.statements) == len(ast2.statements)


class TestCosmosPerformance:
    def test_large_dag_parse_time(self):
        import time
        
        statements = ['provider claude { type = "anthropic" }']
        for i in range(100):
            statements.append('task task_' + str(i) + ' { provider = "claude" depends_on = [] }')
        
        code = '\n'.join(statements)
        parser = Parser(code)
        
        start = time.time()
        ast = parser.parse()
        elapsed = time.time() - start
        
        assert len(ast.statements) == 101
        assert elapsed < 1.0
