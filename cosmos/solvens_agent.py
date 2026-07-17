"""
cosmos/solvens_agent.py
======================

CosmosCompilerAgent - Agente compilador de Cosmos DSL
=====================================================

Implementa la interfaz solvens.agents.base.Agent

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
RFC: RFC-0004-F
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger("cosmos.agent")


# ============================================================
# STATUS ENUM
# ============================================================

class Status(str, Enum):
    """Status de respuesta del agente."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"


# ============================================================
# MESSAGE RESPONSE
# ============================================================

@dataclass
class Message:
    """
    Mensaje de respuesta del agente.
    
    Attributes:
        content: Contenido de la respuesta
        status: APPROVED, REJECTED, PARTIAL, ERROR
        metadata: Metadatos adicionales
    """
    content: str
    status: Status
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "status": self.status.value,
            "metadata": self.metadata
        }


# ============================================================
# TASK PROTOCOL
# ============================================================

@runtime_checkable
class Task(Protocol):
    """Protocolo para Task."""
    name: str
    input: Any
    metadata: Dict[str, Any]


# ============================================================
# BASE AGENT INTERFACE (from solvens.agents.base)
# ============================================================

class BaseAgent:
    """Base class para agentes."""
    
    name: str = "BaseAgent"
    version: str = "0.1.0"
    
    async def run(self, task: Any) -> Message:
        """Ejecuta el agente con una tarea."""
        raise NotImplementedError
    
    async def validate(self, input: Any) -> bool:
        """Valida el input antes de procesar."""
        return True


# ============================================================
# ERROR CODES
# ============================================================

class ErrorCode:
    """Códigos de error para Cosmos."""
    
    # Syntax errors
    E100 = "SyntaxError"
    E101 = "InvalidUniverse"
    E102 = "InvalidNodeType"
    E103 = "UnclosedBlock"
    
    # Semantic errors
    E200 = "DuplicateNode"
    E201 = "UndefinedReference"
    E202 = "CircularDependency"
    
    # Temporal constraint errors (RFC-0004-F)
    E400 = "TemporalConstraintError"
    E401 = "TemporalConstraintViolation"  # FAIL-FAST
    E402 = "TemporalCycleDetected"
    E403 = "InvalidTemporalOrder"
    
    # Validation errors
    E500 = "ValidationError"
    E501 = "SchemaViolation"


# ============================================================
# COSMOS COMPILER AGENT
# ============================================================

class CosmosCompilerAgent(BaseAgent):
    """
    Agente compilador de Cosmos DSL.
    
    Valida, parsea y compila código Cosmos a DAG ejecutable.
    
    Features:
    - Validación sintáctica
    - Validación semántica
    - Validación temporal (RFC-0004-F)
    - Fail-fast en violaciones
    - Retorno estructurado Message
    
    Usage:
        agent = CosmosCompilerAgent()
        result = await agent.run(task)
    """
    
    name: str = "CosmosCompilerAgent"
    version: str = "0.4.5-rc1"
    
    def __init__(
        self,
        strict_mode: bool = False,
        fail_fast: bool = True,
        enable_temporal_validation: bool = True
    ):
        """
        Inicializa el agente compilador.
        
        Args:
            strict_mode: Modo estricto de validación
            fail_fast: Fail-fast en la primera violación
            enable_temporal_validation: Habilitar validación temporal
        """
        self.strict_mode = strict_mode
        self.fail_fast = fail_fast
        self.enable_temporal_validation = enable_temporal_validation
        
        self._errors: List[Dict[str, Any]] = []
        self._warnings: List[Dict[str, Any]] = []
        
        logger.info(
            f"CosmosCompilerAgent initialized "
            f"(strict={strict_mode}, fail_fast={fail_fast})"
        )
    
    async def validate(self, input: Any) -> bool:
        """
        Valida el input antes de procesar.
        
        Args:
            input: Código Cosmos o path a archivo
            
        Returns:
            True si es válido, False si no
        """
        if not input:
            return False
        
        if isinstance(input, str):
            return len(input.strip()) > 0
        
        if isinstance(input, dict):
            return "cosmos" in input or "source" in input
        
        return True
    
    async def run(self, task: Any) -> Message:
        """
        Ejecuta la compilación del código Cosmos.
        
        Args:
            task: Task con código Cosmos o path
            
        Returns:
            Message con resultado de la compilación
        """
        self._errors = []
        self._warnings = []
        
        try:
            # Extract source
            source = self._extract_source(task)
            
            if not source:
                return Message(
                    content="No source code provided",
                    status=Status.REJECTED,
                    metadata={"error_code": ErrorCode.E100, "error": "Empty source"}
                )
            
            # Phase 1: Syntax validation
            syntax_result = await self._validate_syntax(source)
            if not syntax_result["valid"]:
                return self._create_error_message(
                    Status.REJECTED,
                    syntax_result["error"],
                    syntax_result.get("error_code", ErrorCode.E100)
                )
            
            # Phase 2: Semantic validation
            semantic_result = await self._validate_semantic(source)
            if not semantic_result["valid"]:
                if self.fail_fast:
                    return self._create_error_message(
                        Status.REJECTED,
                        semantic_result["error"],
                        semantic_result.get("error_code", ErrorCode.E200)
                    )
                self._warnings.append(semantic_result)
            
            # Phase 3: Temporal validation (RFC-0004-F)
            if self.enable_temporal_validation:
                temporal_result = await self._validate_temporal(source)
                if not temporal_result["valid"]:
                    # FAIL-FAST: Violación temporal es crítica
                    return self._create_error_message(
                        Status.REJECTED,
                        temporal_result["error"],
                        temporal_result.get("error_code", ErrorCode.E401),
                        details=temporal_result.get("details")
                    )
            
            # Phase 4: Compile to DAG
            dag_result = await self._compile_to_dag(source)
            
            if not dag_result["valid"]:
                return self._create_error_message(
                    Status.REJECTED,
                    dag_result["error"],
                    dag_result.get("error_code", ErrorCode.E500)
                )
            
            # Success
            return Message(
                content="Compilation successful",
                status=Status.APPROVED,
                metadata={
                    "dag": dag_result["dag"],
                    "nodes": dag_result["nodes"],
                    "layers": dag_result["layers"],
                    "warnings": self._warnings
                }
            )
            
        except Exception as e:
            logger.exception("Compilation failed")
            return Message(
                content=f"Internal error: {str(e)}",
                status=Status.ERROR,
                metadata={"error_code": "INTERNAL_ERROR", "error": str(e)}
            )
    
    def _extract_source(self, task: Any) -> str:
        """Extrae el código fuente del task."""
        if isinstance(task, str):
            return task
        
        if isinstance(task, dict):
            return task.get("source") or task.get("cosmos") or task.get("code", "")
        
        if hasattr(task, "input"):
            return str(task.input)
        
        return str(task)
    
    async def _validate_syntax(self, source: str) -> Dict[str, Any]:
        """Valida sintaxis del código Cosmos."""
        errors = []
        
        # Check for universe block
        if "cosmos" not in source.lower():
            errors.append({
                "error": "Missing 'cosmos' block",
                "error_code": ErrorCode.E101
            })
        
        # Check for balanced braces
        open_braces = source.count("{")
        close_braces = source.count("}")
        if open_braces != close_braces:
            errors.append({
                "error": f"Unbalanced braces: {open_braces} open, {close_braces} close",
                "error_code": ErrorCode.E103
            })
        
        # Check for valid node types
        valid_types = ["sun", "planet", "galaxy", "light", "star"]
        for node_type in valid_types:
            pattern = f"{node_type} "
            if pattern in source.lower():
                # Found a node, check for name
                import re
                matches = re.findall(f"{node_type}\\s+(\\w+)", source, re.IGNORECASE)
                if not matches:
                    errors.append({
                        "error": f"Invalid {node_type} declaration",
                        "error_code": ErrorCode.E102
                    })
        
        if errors:
            return {"valid": False, **errors[0]}
        
        return {"valid": True}
    
    async def _validate_semantic(self, source: str) -> Dict[str, Any]:
        """Valida semántica del código Cosmos."""
        import re
        
        # Extract node names
        nodes = set()
        node_pattern = r"(sun|planet|galaxy|light|star)\s+(\w+)"
        
        for match in re.finditer(node_pattern, source, re.IGNORECASE):
            node_name = match.group(2)
            if node_name in nodes:
                return {
                    "valid": False,
                    "error": f"Duplicate node: {node_name}",
                    "error_code": ErrorCode.E200
                }
            nodes.add(node_name)
        
        # Check for undefined references in connects_to
        connects_matches = re.findall(r"connects_to:\s*\[?([^\]\n,]+)\]?", source)
        for ref in connects_matches:
            ref = ref.strip()
            if ref not in nodes and ref not in ["none", "null", ""]:
                if self.strict_mode:
                    return {
                        "valid": False,
                        "error": f"Undefined reference: {ref}",
                        "error_code": ErrorCode.E201
                    }
        
        return {"valid": True}
    
    async def _validate_temporal(self, source: str) -> Dict[str, Any]:
        """
        Valida restricciones temporales (RFC-0004-F).
        
        Fail-fast: Retorna error inmediatamente en la primera violación.
        """
        import re
        
        # Pattern para start_after y end_before
        start_after_pattern = r"start_after:\s*(\d+)"
        end_before_pattern = r"end_before:\s*(\d+)"
        duration_pattern = r"duration:\s*(\d+)"
        
        constraints = []
        
        for match in re.finditer(start_after_pattern, source):
            time = int(match.group(1))
            constraints.append({"type": "start_after", "value": time})
        
        for match in re.finditer(end_before_pattern, source):
            time = int(match.group(1))
            constraints.append({"type": "end_before", "value": time})
        
        for match in re.finditer(duration_pattern, source):
            duration = int(match.group(1))
            constraints.append({"type": "duration", "value": duration})
        
        # Check for conflicts
        start_after = None
        end_before = None
        
        for c in constraints:
            if c["type"] == "start_after":
                start_after = c["value"]
            elif c["type"] == "end_before":
                end_before = c["value"]
        
        # E401: Temporal constraint violation
        if start_after is not None and end_before is not None:
            if start_after >= end_before:
                return {
                    "valid": False,
                    "error": f"TemporalConstraintViolation: start_after ({start_after}) >= end_before ({end_before})",
                    "error_code": ErrorCode.E401,
                    "details": {
                        "start_after": start_after,
                        "end_before": end_before,
                        "violation": "start_after must be before end_before"
                    }
                }
        
        # Check for temporal cycles
        cycle_result = self._check_temporal_cycles(source)
        if cycle_result:
            return {
                "valid": False,
                "error": f"TemporalCycleDetected: {cycle_result}",
                "error_code": ErrorCode.E402,
                "details": {"cycle": cycle_result}
            }
        
        return {"valid": True}
    
    def _check_temporal_cycles(self, source: str) -> Optional[List[str]]:
        """
        Detecta ciclos temporales en el grafo.
        
        Returns:
            Lista de nodos en el ciclo, o None si no hay ciclo
        """
        import re
        
        # Build adjacency
        edges = []
        node_pattern = r"(sun|planet|galaxy|light|star)\s+(\w+)"
        connects_pattern = r"connects_to:\s*\[?([^\]\n,]+)\]?"
        
        current_node = None
        for line in source.split("\n"):
            node_match = re.search(node_pattern, line, re.IGNORECASE)
            if node_match:
                current_node = node_match.group(2)
            
            connects_match = re.search(connects_pattern, line)
            if connects_match and current_node:
                targets = connects_match.group(1).split(",")
                for target in targets:
                    target = target.strip()
                    if target:
                        edges.append((current_node, target))
        
        # DFS para detectar ciclos
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # Find neighbors
            neighbors = [target for (source, target) in edges if source == node]
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        # Check all nodes
        nodes = set([s for (s, _) in edges] + [t for (_, t) in edges])
        for node in nodes:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle
        
        return None
    
    async def _compile_to_dag(self, source: str) -> Dict[str, Any]:
        """Compila el código Cosmos a DAG."""
        try:
            # Parse nodes
            import re
            nodes = []
            node_pattern = r"(sun|planet|galaxy|light|star)\s+(\w+)\s*\{([^}]*)\}"
            
            for match in re.finditer(node_pattern, source, re.DOTALL):
                node_type = match.group(1)
                node_name = match.group(2)
                node_content = match.group(3)
                
                nodes.append({
                    "id": node_name.lower().replace(" ", "_"),
                    "name": node_name,
                    "type": node_type.lower(),
                    "properties": self._parse_properties(node_content)
                })
            
            # Calculate layers (simple topological sort)
            layers = self._calculate_layers(nodes)
            
            return {
                "valid": True,
                "dag": {"nodes": nodes, "layers": layers},
                "nodes": len(nodes),
                "layers": len(layers)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Compilation failed: {str(e)}",
                "error_code": ErrorCode.E500
            }
    
    def _parse_properties(self, content: str) -> Dict[str, Any]:
        """Parsea propiedades de un nodo."""
        import re
        props = {}
        
        # key: value patterns
        patterns = [
            r"model:\s*(\S+)",
            r"connects_to:\s*\[?([^\]\n,]+)\]?",
            r"from:\s*\[?([^\]\n,]+)\]?",
            r"to:\s*\[?([^\]\n,]+)\]?",
            r"duration:\s*(\d+)",
            r"start_after:\s*(\d+)",
            r"end_before:\s*(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                key = pattern.split(":")[0].strip().replace("\\", "")
                props[key] = match.group(1).strip()
        
        return props
    
    def _calculate_layers(self, nodes: List[Dict[str, Any]]) -> List[List[str]]:
        """Calcula las capas de ejecución."""
        import re
        
        # Build adjacency
        node_ids = {n["name"] for n in nodes}
        connections = {}  # node -> set of nodes it connects to
        
        for node in nodes:
            node_id = node["name"]
            connects_to = node.get("properties", {}).get("connects_to", "")
            
            targets = set()
            for target in connects_to.split(","):
                target = target.strip()
                if target in node_ids:
                    targets.add(target)
            
            connections[node_id] = targets
        
        # Calculate layers
        layers = []
        remaining = set(node_ids)
        processed = set()
        
        while remaining:
            current_layer = []
            
            for node in remaining:
                deps = connections.get(node, set())
                # Node can be in current layer if all its dependencies are processed
                if deps <= processed:
                    current_layer.append(node)
            
            if not current_layer:
                # Circular dependency or error
                current_layer = list(remaining)[:1]
            
            layers.append(current_layer)
            processed.update(current_layer)
            remaining -= set(current_layer)
        
        return layers
    
    def _create_error_message(
        self,
        status: Status,
        error: str,
        error_code: str,
        details: Optional[Dict] = None
    ) -> Message:
        """Crea un mensaje de error estructurado."""
        metadata = {
            "error_code": error_code,
            "error": error,
            "fail_fast": self.fail_fast
        }
        
        if details:
            metadata["details"] = details
        
        if self._warnings:
            metadata["warnings"] = self._warnings
        
        return Message(
            content=f"[{error_code}] {error}",
            status=status,
            metadata=metadata
        )


# ============================================================
# PLUGIN ENTRY POINT
# ============================================================

def get_agent() -> CosmosCompilerAgent:
    """Factory function para el plugin system."""
    return CosmosCompilerAgent()


# ============================================================
# DEMO / TEST
# ============================================================

async def demo():
    """Demo del CosmosCompilerAgent."""
    print("=" * 60)
    print("CosmosCompilerAgent v0.4.5-rc1")
    print("=" * 60)
    
    agent = CosmosCompilerAgent(strict_mode=False, fail_fast=True)
    
    # Valid Cosmos
    valid_cosmos = """
cosmos ResearchAgent {
    sun CentralOrchestrator
    
    planet Researcher {
        model: claude-3-sonnet
        connects_to: Coder
    }
    
    planet Coder {
        model: gpt-4
        connects_to: Reviewer
    }
    
    planet Reviewer {
        model: gemini
    }
}
end
"""
    
    print("\n[Test 1: Valid Cosmos]")
    result = await agent.run(valid_cosmos)
    print(f"Status: {result.status.value}")
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
    
    # Temporal violation (E401)
    temporal_violation = """
cosmos TestAgent {
    planet Task1 {
        start_after: 100
        end_before: 50
    }
}
end
"""
    
    print("\n[Test 2: Temporal Violation (E401)]")
    result = await agent.run(temporal_violation)
    print(f"Status: {result.status.value}")
    print(f"Content: {result.content}")
    print(f"Error Code: {result.metadata.get('error_code')}")
    print(f"Fail-Fast: {result.metadata.get('fail_fast')}")
    
    # Syntax error
    bad_syntax = """
cosmos BadAgent {
    planet {
        model: claude
    }
}
end
"""
    
    print("\n[Test 3: Syntax Error]")
    result = await agent.run(bad_syntax)
    print(f"Status: {result.status.value}")
    print(f"Content: {result.content}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo())
