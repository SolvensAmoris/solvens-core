"""Cosmos Parser module.

Transforms natural language or DSL Cosmos into an AST.
Supports multiple input formats: DSL, JSON, and future importers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from solvens.cosmos.ast import (
    CosmosAST,
    CosmosNode,
    CosmosNodeType,
    CosmosEntity,
)


class InputFormat(Enum):
    """Supported input formats for the parser."""
    
    DSL = "dsl"              # Cosmos DSL syntax
    JSON = "json"           # JSON representation
    NATURAL = "natural"     # Natural language (future)
    YAML = "yaml"          # YAML representation (future)


@dataclass
class ParseResult:
    """Result of parsing operation."""
    
    success: bool
    ast: CosmosAST | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "ast": self.ast.to_dict() if self.ast else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class CosmosParser:
    """Parser for Cosmos language.
    
    Transforms input text into a Cosmos AST.
    Supports DSL syntax, JSON format, and natural language (future).
    """
    
    # DSL Keywords
    TASK_KW = "task"
    AGENT_KW = "agent"
    TOOL_KW = "tool"
    PROVIDER_KW = "provider"
    WHEN_KW = "when"
    SEQUENCE_KW = "sequence"
    PARALLEL_KW = "parallel"
    IF_KW = "if"
    
    def __init__(self):
        self.current_pos = 0
        self.source = ""
        self.tokens: list[str] = []
    
    def parse(self, source: str, format: InputFormat = InputFormat.DSL) -> ParseResult:
        """Parse source text into a Cosmos AST.
        
        Args:
            source: The source text to parse
            format: The format of the source (DSL, JSON, etc.)
            
        Returns:
            ParseResult containing the AST or errors
        """
        self.source = source
        self.current_pos = 0
        
        try:
            if format == InputFormat.JSON:
                return self._parse_json(source)
            elif format == InputFormat.DSL:
                return self._parse_dsl(source)
            elif format == InputFormat.NATURAL:
                return self._parse_natural(source)
            else:
                return ParseResult(
                    success=False,
                    errors=[f"Unsupported format: {format}"]
                )
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"Parse error: {str(e)}"]
            )
    
    def _parse_json(self, source: str) -> ParseResult:
        """Parse JSON format."""
        try:
            data = json.loads(source)
            ast = self._json_to_ast(data)
            return ParseResult(success=True, ast=ast)
        except json.JSONDecodeError as e:
            return ParseResult(success=False, errors=[f"JSON parse error: {e}"])
    
    def _json_to_ast(self, data: dict[str, Any]) -> CosmosAST:
        """Convert JSON data to Cosmos AST."""
        ast = CosmosAST()
        
        if "root" in data:
            root_node = self._json_node_to_cosmos(data["root"])
            ast.add_node(root_node)
        
        return ast
    
    def _json_node_to_cosmos(self, data: dict[str, Any]) -> CosmosNode:
        """Convert a JSON node to CosmosNode."""
        node_type = CosmosNodeType(data.get("type", "expression"))
        node = CosmosNode(node_type=node_type)
        
        # Set properties
        if "properties" in data:
            node.properties.update(data["properties"])
        
        # Set metadata
        if "metadata" in data:
            node.metadata.update(data["metadata"])
        
        # Process children
        if "relations" in data:
            for relation, children in data["relations"].items():
                for child_data in children:
                    child = self._json_node_to_cosmos(child_data)
                    ast.add_node(child, node, relation)
        
        return node
    
    def _parse_dsl(self, source: str) -> ParseResult:
        """Parse Cosmos DSL syntax."""
        ast = CosmosAST()
        errors: list[str] = []
        warnings: list[str] = []
        
        lines = source.strip().split("\n")
        current_block: CosmosNode | None = None
        block_stack: list[tuple[CosmosNode, str]] = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Check for block start
            if line.endswith(":"):
                block_type, block_name = self._parse_block_header(line)
                
                if block_type == self.TASK_KW:
                    node = CosmosNode(
                        node_type=CosmosNodeType.TASK,
                        properties={"name": block_name}
                    )
                    ast.add_node(node, current_block, "tasks")
                    current_block = node
                    block_stack.append((current_block, "tasks"))
                
                elif block_type == self.AGENT_KW:
                    node = CosmosNode(
                        node_type=CosmosNodeType.AGENT,
                        properties={"name": block_name}
                    )
                    ast.add_node(node, current_block, "agents")
                    current_block = node
                    block_stack.append((current_block, "agents"))
                
                elif block_type in (self.SEQUENCE_KW, self.PARALLEL_KW):
                    node_type = CosmosNodeType.SEQUENCE if block_type == self.SEQUENCE_KW else CosmosNodeType.PARALLEL
                    node = CosmosNode(
                        node_type=node_type,
                        properties={"name": block_name}
                    )
                    ast.add_node(node, current_block, "blocks")
                    current_block = node
                    block_stack.append((current_block, "blocks"))
            
            # Check for block end
            elif line == "end" and block_stack:
                parent, relation = block_stack.pop()
                current_block = parent if block_stack else None
            
            # Parse key-value pairs
            elif "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                
                if current_block:
                    if key == "provider":
                        current_block.properties["provider"] = value
                    elif key == "tool":
                        current_block.properties["tool"] = value
                    elif key == "priority":
                        try:
                            current_block.properties["priority"] = int(value)
                        except ValueError:
                            warnings.append(f"Line {line_num}: Invalid priority value")
                    else:
                        current_block.properties[key] = value
        
        # Validate AST
        is_valid, validation_errors = ast.validate()
        if not is_valid:
            errors.extend(validation_errors)
        
        return ParseResult(
            success=len(errors) == 0,
            ast=ast if len(errors) == 0 else None,
            errors=errors,
            warnings=warnings,
            metadata={"format": "dsl", "lines": len(lines)}
        )
    
    def _parse_block_header(self, line: str) -> tuple[str, str]:
        """Parse a block header like 'task: my_task'."""
        header = line[:-1].strip()  # Remove trailing colon
        parts = header.split(None, 1)
        
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]
    
    def _parse_natural(self, source: str) -> ParseResult:
        """Parse natural language input (simplified).
        
        This is a simplified implementation. A full natural language
        parser would use ML/NLP techniques.
        """
        warnings = ["Natural language parsing is experimental"]
        
        # Simple pattern matching for common patterns
        ast = CosmosAST()
        
        # Detect task patterns
        task_patterns = [
            r"(?:create|build|make|develop)\s+(?:a\s+)?(.+)",
            r"(?:analyze|review|examine)\s+(?:the\s+)?(.+)",
            r"(?:fix|resolve|debug)\s+(?:the\s+)?(.+)",
            r"(?:write|document|describe)\s+(?:the\s+)?(.+)",
        ]
        
        for pattern in task_patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                task_name = match.group(1).strip()
                task_node = CosmosNode(
                    node_type=CosmosNodeType.TASK,
                    properties={
                        "name": task_name,
                        "original_text": source,
                    }
                )
                task_node.metadata["intent"] = "detected"
                ast.add_node(task_node)
                break
        
        # If no pattern matched, create a generic task
        if len(ast.nodes) == 1:
            ast.root.properties["fallback_task"] = source
        else:
            # Create task from entire input
            task_node = CosmosNode(
                node_type=CosmosNodeType.TASK,
                properties={
                    "name": "natural_language_task",
                    "original_text": source,
                }
            )
            ast.add_node(task_node)
            warnings.append("Created generic task from natural language input")
        
        return ParseResult(
            success=True,
            ast=ast,
            warnings=warnings,
            metadata={"format": "natural"}
        )
    
    def parse_file(self, filepath: str) -> ParseResult:
        """Parse a Cosmos file.
        
        Automatically detects format from extension.
        """
        with open(filepath, "r") as f:
            content = f.read()
        
        # Detect format from extension
        if filepath.endswith(".json"):
            return self.parse(content, InputFormat.JSON)
        elif filepath.endswith((".cosmos", ".cml")):
            return self.parse(content, InputFormat.DSL)
        else:
            return self.parse(content, InputFormat.DSL)


# Example DSL:
"""
task: create_report
    provider = anthropic
    priority = 80
    
    sequence: research
        tool = web_search
        provider = google
        
    parallel: analysis
        task: data_processing
            tool = python
        task: visualization
            tool = matplotlib
"""

# Example JSON:
"""
{
    "root": {
        "type": "program",
        "properties": {"name": "create_report"},
        "relations": {
            "tasks": [
                {
                    "type": "task",
                    "properties": {"name": "research", "provider": "google"}
                }
            ]
        }
    }
}
"""
