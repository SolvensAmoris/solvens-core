"""
solvens/cosmos/moat_executor.py
==============================

COSMOS EXECUTOR v0.2
====================

Executor paralelo para Cosmos DAG.
El motor que hace plata ejecutando workflows como motor de física computacional.

Features:
- Topological parallel execution
- Layer-based scheduling
- Temporal constraints
- Provider fusion (consensus)
- Self-optimize loop

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from solvens.cosmos.moat_parser import CosmosDAG, CosmosNode, NodeType
from solvens.router.smart_router import SmartRouter, TaskType

logger = logging.getLogger("solvens.cosmos.executor")


# ============================================================
# RESULT TYPES
# ============================================================

@dataclass
class ExecutionResult:
    """Resultado de ejecución de un nodo."""
    node_id: str
    status: str  # success, failed, skipped
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    provider: str = ""
    tokens_used: int = 0
    cost: float = 0


@dataclass
class ExecutionStats:
    """Estadísticas de ejecución."""
    total_nodes: int = 0
    executed_nodes: int = 0
    failed_nodes: int = 0
    skipped_nodes: int = 0
    total_duration_ms: float = 0
    total_cost: float = 0
    total_tokens: int = 0
    layers_executed: int = 0
    parallelization_factor: float = 0  # nodes/layers
    
    @property
    def success_rate(self) -> float:
        if self.executed_nodes == 0:
            return 0
        return (self.executed_nodes - self.failed_nodes) / self.executed_nodes * 100


# ============================================================
# CONSTRAINTS HANDLER
# ============================================================

class ConstraintHandler:
    """Maneja restricciones temporales y de recursos."""
    
    def __init__(self):
        self._timers: Dict[str, asyncio.Task] = {}
        self._suspended: Set[str] = set()
    
    async def check_constraints(
        self,
        node: CosmosNode,
        context: Dict[str, Any]
    ) -> bool:
        """
        Verifica si un nodo puede ejecutarse.
        
        Returns:
            True si puede ejecutar, False si debe esperar
        """
        # Check suspended state
        if node.id in self._suspended:
            return False
        
        # Check temporal constraints
        if node.constraints:
            # Check start_after
            if "start_after" in node.constraints:
                start_after = node.constraints["start_after"]
                if isinstance(start_after, str):
                    start_after = datetime.fromisoformat(start_after)
                if datetime.now() < start_after:
                    logger.debug(f"Node {node.id} waiting for start_after: {start_after}")
                    return False
            
            # Check end_before
            if "end_before" in node.constraints:
                end_before = node.constraints["end_before"]
                if isinstance(end_before, str):
                    end_before = datetime.fromisoformat(end_before)
                if datetime.now() > end_before:
                    logger.debug(f"Node {node.id} past end_before: {end_before}")
                    return False
        
        return True
    
    def suspend(self, node_id: str):
        """Suspende un nodo."""
        self._suspended.add(node_id)
        logger.info(f"Node {node_id} suspended")
    
    def resume(self, node_id: str):
        """Reanuda un nodo."""
        self._suspended.discard(node_id)
        logger.info(f"Node {node_id} resumed")
    
    def cleanup(self):
        """Limpia recursos."""
        for task in self._timers.values():
            task.cancel()
        self._timers.clear()


# ============================================================
# COSMOS EXECUTOR
# ============================================================

class CosmosExecutor:
    """
    Executor paralelo para Cosmos DAG.
    
    Ejecuta workflows en parallel donde es posible,
    optimizando por costo y latencia.
    
    Usage:
        executor = CosmosExecutor(router)
        result = await executor.execute(dag, input_data)
    """
    
    def __init__(
        self,
        router: Optional[SmartRouter] = None,
        enable_consensus: bool = False,
        consensus_providers: List[str] = None
    ):
        self.router = router
        self.enable_consensus = enable_consensus
        self.consensus_providers = consensus_providers or ["grok", "claude"]
        
        self.constraints = ConstraintHandler()
        
        # Execution state
        self._results: Dict[str, ExecutionResult] = {}
        self._execution_times: Dict[str, float] = {}
        self._stats = ExecutionStats()
        
        # Node handlers
        self._handlers: Dict[NodeType, Callable] = {
            NodeType.SUN: self._handle_sun,
            NodeType.PLANET: self._handle_planet,
            NodeType.STAR: self._handle_star,
            NodeType.GALAXY: self._handle_galaxy,
        }
        
        # Cache for canonical DAGs
        self._dag_cache: Dict[str, CosmosDAG] = {}
        
        logger.info(f"CosmosExecutor initialized (consensus={enable_consensus})")
    
    async def execute(
        self,
        dag: CosmosDAG,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ExecutionResult]:
        """
        Ejecuta un DAG Cosmos en paralelo.
        
        Args:
            dag: CosmosDAG a ejecutar
            input_data: Datos de entrada
            context: Contexto compartido entre nodos
            
        Returns:
            Dict[node_id -> ExecutionResult]
        """
        logger.info(f"Executing DAG: {dag.universe}")
        logger.info(f"Layers: {len(dag.layers)}")
        
        # Reset state
        self._results = {}
        self._execution_times = {}
        context = context or {}
        
        start_time = time.time()
        
        # Execute layer by layer
        for layer_idx, layer in enumerate(dag.layers):
            logger.info(f"Executing layer {layer_idx + 1}/{len(dag.layers)}: {layer}")
            
            # Filter available nodes
            available = []
            for node_id in layer:
                if node_id not in dag.nodes:
                    continue
                
                node = dag.nodes[node_id]
                
                # Check if all parents are done
                if node.parents:
                    all_done = all(
                        pid in self._results and 
                        self._results[pid].status == "success"
                        for pid in node.parents
                    )
                    if not all_done:
                        continue
                
                # Check constraints
                can_execute = await self.constraints.check_constraints(node, context)
                if not can_execute:
                    self._results[node_id] = ExecutionResult(
                        node_id=node_id,
                        status="skipped",
                        error="Constraint not met"
                    )
                    self._stats.skipped_nodes += 1
                    continue
                
                available.append(node_id)
            
            if not available:
                continue
            
            # Execute layer in parallel
            tasks = []
            for node_id in available:
                node = dag.nodes[node_id]
                handler = self._handlers.get(node.node_type, self._handle_default)
                task = asyncio.create_task(
                    self._execute_node(node, dag, input_data, context, handler)
                )
                tasks.append((node_id, task))
            
            # Wait for layer completion
            for node_id, task in tasks:
                try:
                    await task
                except Exception as e:
                    logger.error(f"Node {node_id} failed: {e}")
                    self._results[node_id] = ExecutionResult(
                        node_id=node_id,
                        status="failed",
                        error=str(e)
                    )
        
        # Compute stats
        self._stats.total_nodes = len(dag.nodes)
        self._stats.total_duration_ms = (time.time() - start_time) * 1000
        self._stats.layers_executed = len(dag.layers)
        
        if self._stats.layers_executed > 0:
            self._stats.parallelization_factor = (
                self._stats.total_nodes / self._stats.layers_executed
            )
        
        for result in self._results.values():
            if result.status == "success":
                self._stats.executed_nodes += 1
                self._stats.total_cost += result.cost
                self._stats.total_tokens += result.tokens_used
            elif result.status == "failed":
                self._stats.failed_nodes += 1
        
        logger.info(f"Execution complete: {self._stats}")
        
        return self._results
    
    async def _execute_node(
        self,
        node: CosmosNode,
        dag: CosmosDAG,
        input_data: Dict,
        context: Dict,
        handler: Callable
    ) -> ExecutionResult:
        """Ejecuta un nodo individual."""
        node_start = time.time()
        
        try:
            logger.debug(f"Executing node: {node.id} ({node.node_type.value})")
            
            # Execute with handler
            result = await handler(node, dag, input_data, context)
            
            node_duration = (time.time() - node_start) * 1000
            self._execution_times[node.id] = node_duration
            
            execution_result = ExecutionResult(
                node_id=node.id,
                status="success",
                output=result,
                duration_ms=node_duration,
                provider=node.properties.get("model", "unknown")
            )
            
        except Exception as e:
            logger.error(f"Node {node.id} error: {e}")
            execution_result = ExecutionResult(
                node_id=node.id,
                status="failed",
                error=str(e),
                duration_ms=(time.time() - node_start) * 1000
            )
        
        self._results[node.id] = execution_result
        return execution_result
    
    async def _handle_sun(
        self,
        node: CosmosNode,
        dag: CosmosDAG,
        input_data: Dict,
        context: Dict
    ) -> Any:
        """Maneja nodo SUN (entry point)."""
        logger.info(f"Sun node: {node.name}")
        return {"status": "orchestrator_started", "input": input_data}
    
    async def _handle_planet(
        self,
        node: CosmosNode,
        dag: CosmosDAG,
        input_data: Dict,
        context: Dict
    ) -> Any:
        """
        Maneja nodo PLANET (task/agent).
        
        Usa el router para seleccionar provider.
        """
        logger.info(f"Planet: {node.name}, model={node.properties.get('model')}")
        
        # Get parent results for context
        parent_outputs = {}
        for parent_id in node.parents:
            if parent_id in self._results:
                parent_outputs[parent_id] = self._results[parent_id].output
        
        # If consensus enabled, run multiple providers
        if self.enable_consensus and self.router:
            return await self._run_consensus(node, parent_outputs)
        
        # Normal execution via router
        if self.router:
            task_type = self._infer_task_type(node)
            prompt = self._build_prompt(node, parent_outputs)
            
            routing = await self.router.route(prompt, task_type=task_type)
            
            result = await self.router.execute(
                prompt,
                preferred_provider=routing.provider
            )
            
            return {
                "response": result.get("content"),
                "provider": routing.provider.value,
                "model": routing.model,
                "tokens": result.get("usage", {}).get("total_tokens", 0)
            }
        
        # Fallback: simple echo
        return {
            "response": f"Executed {node.name}",
            "provider": "mock",
            "model": "mock"
        }
    
    async def _run_consensus(
        self,
        node: CosmosNode,
        parent_outputs: Dict
    ) -> Dict[str, Any]:
        """
        Ejecuta consensus: múltiples providers y vota resultado.
        
        Reduce alucinaciones ejecutando el mismo prompt en
        múltiples providers y seleccionando el resultado
        por mayoría o calidad.
        """
        logger.info(f"Running consensus for {node.name}")
        
        prompt = self._build_prompt(node, parent_outputs)
        
        # Execute in parallel
        tasks = []
        for provider_name in self.consensus_providers:
            if hasattr(provider_name, 'value'):
                provider_name = provider_name.value
            task = asyncio.create_task(
                self.router.execute(prompt, preferred_provider=provider_name)
            )
            tasks.append((provider_name, task))
        
        # Gather results
        results = []
        for provider_name, task in tasks:
            try:
                result = await task
                results.append({
                    "provider": provider_name,
                    "response": result.get("content", ""),
                    "tokens": result.get("usage", {}).get("total_tokens", 0)
                })
            except Exception as e:
                logger.warning(f"Consensus provider {provider_name} failed: {e}")
        
        # Simple consensus: return first valid result
        # TODO: Implement voting/quality scoring
        if results:
            best = results[0]
            return {
                "response": best["response"],
                "provider": best["provider"],
                "consensus": len(results),
                "all_responses": [r["response"] for r in results]
            }
        
        return {"error": "No consensus reached"}
    
    async def _handle_star(
        self,
        node: CosmosNode,
        dag: CosmosDAG,
        input_data: Dict,
        context: Dict
    ) -> Any:
        """Maneja nodo STAR (provider/llm)."""
        logger.info(f"Star: {node.name}")
        return {"provider": node.name, "model": node.properties.get("model")}
    
    async def _handle_galaxy(
        self,
        node: CosmosNode,
        dag: CosmosDAG,
        input_data: Dict,
        context: Dict
    ) -> Any:
        """Maneja nodo GALAXY (sub-DAG)."""
        logger.info(f"Galaxy: {node.name}")
        # TODO: Execute sub-DAG
        return {"status": "subdag_pending"}
    
    async def _handle_default(
        self,
        node: CosmosNode,
        dag: CosmosDAG,
        input_data: Dict,
        context: Dict
    ) -> Any:
        """Handler por defecto."""
        return {"node": node.name, "type": node.node_type.value}
    
    def _infer_task_type(self, node: CosmosNode) -> TaskType:
        """Infiere tipo de task basado en propiedades."""
        name = node.name.lower()
        props = str(node.properties).lower()
        
        if "code" in name or "coder" in name or "python" in props:
            return TaskType.CODE
        elif "legal" in name or "law" in name or "court" in props:
            return TaskType.LEGAL
        elif "research" in name or "analyze" in name:
            return TaskType.RESEARCH
        elif "creative" in name or "write" in name:
            return TaskType.CREATIVE
        else:
            return TaskType.FAST
    
    def _build_prompt(self, node: CosmosNode, parent_outputs: Dict) -> str:
        """Construye prompt para el nodo."""
        # Combine parent outputs as context
        context = "\n".join(
            f"[{pid}]: {out.get('response', str(out))}"
            for pid, out in parent_outputs.items()
        )
        
        # Base prompt from node properties
        base_prompt = node.properties.get("prompt", node.name)
        
        if context:
            return f"{base_prompt}\n\nContext:\n{context}"
        return base_prompt
    
    def get_stats(self) -> ExecutionStats:
        """Obtiene estadísticas de ejecución."""
        return self._stats
    
    def optimize_dag(self, dag: CosmosDAG) -> CosmosDAG:
        """
        Auto-optimiza DAG basándose en historial de ejecución.
        
        Reordena nodos y ajusta paralelismo basándose en
        tiempos de ejecución históricos.
        """
        logger.info("Optimizing DAG...")
        
        # This is where we would:
        # 1. Analyze execution times
        # 2. Identify bottlenecks
        # 3. Reorder for better parallelization
        # 4. Cache similar sub-DAGs
        
        # For now, just canonicalize
        return dag.canonicalize()


# ============================================================
# CACHE
# ============================================================

class DAGCache:
    """Cache para DAGs canónicos."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: Dict[str, CosmosDAG] = {}
        self._access_times: Dict[str, float] = {}
    
    def get(self, dag: CosmosDAG) -> Optional[CosmosDAG]:
        """Obtiene DAG del cache."""
        key = dag.graph_hash
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return None
    
    def put(self, dag: CosmosDAG):
        """Guarda DAG en cache."""
        key = dag.graph_hash
        
        # Evict if full
        if len(self._cache) >= self.max_size:
            oldest = min(self._access_times.items(), key=lambda x: x[1])
            del self._cache[oldest[0]]
            del self._access_times[oldest[0]]
        
        self._cache[key] = dag
        self._access_times[key] = time.time()
    
    def clear(self):
        """Limpia cache."""
        self._cache.clear()
        self._access_times.clear()


# ============================================================
# DEMO
# ============================================================

async def demo():
    """Demo del executor."""
    print("=" * 60)
    print("COSMOS EXECUTOR v0.2 - PARALLEL EXECUTION")
    print("=" * 60)
    
    from solvens.cosmos.moat_parser import CosmosParser
    
    cosmos_code = """
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
    
    print("\n[Parsing DAG...]")
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    print(dag.visualize_text())
    
    print("\n[Executing DAG...]")
    executor = CosmosExecutor(enable_consensus=False)
    
    results = await executor.execute(dag, {"query": "Research AI trends"})
    
    print("\n[Results]")
    for node_id, result in results.items():
        status_icon = {"success": "✓", "failed": "✗", "skipped": "○"}.get(result.status, "?")
        print(f"  {status_icon} {node_id}: {result.status} ({result.duration_ms:.0f}ms)")
        if result.output:
            resp = str(result.output.get("response", result.output))[:50]
            print(f"      → {resp}...")
    
    print("\n[Stats]")
    stats = executor.get_stats()
    print(f"  Total nodes: {stats.total_nodes}")
    print(f"  Executed: {stats.executed_nodes}")
    print(f"  Failed: {stats.failed_nodes}")
    print(f"  Duration: {stats.total_duration_ms:.0f}ms")
    print(f"  Parallelization: {stats.parallelization_factor:.1f}x")
    
    print("\n" + "=" * 60)
    print("COSMOS EXECUTOR MOAT ACTIVE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
