"""
cosmos/explainer.py
==================

LLMExplainerAgent - AI-powered error explanation for Cosmos
==========================================================

Uses LLM to explain E401 and other Cosmos errors in natural language.

Features:
- Context-aware explanations
- Knowledge Graph integration for relationship context
- Solution suggestions
- Markdown/JSON output formats

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
RFC: RFC-0004-F
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cosmos.explainer")

# ============================================================
# IMPORTS FOR LLM
# ============================================================

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ============================================================
# ENUMS
# ============================================================

class Severity(str, Enum):
    """Severity level of explanation."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class OutputFormat(str, Enum):
    """Output format for explanations."""
    MARKDOWN = "markdown"
    JSON = "json"
    PLAIN = "plain"
    HTML = "html"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ErrorContext:
    """Contexto del error."""
    error_code: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    related_nodes: List[str] = field(default_factory=list)
    cosmos_source: Optional[str] = None
    dag_snapshot: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Explanation:
    """Explicación generada por el LLM."""
    summary: str
    cause: str
    affected_nodes: List[str]
    solution_steps: List[str]
    severity: Severity
    confidence: float  # 0.0 - 1.0
    references: List[str] = field(default_factory=list)
    raw_llm_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """Convierte a formato Markdown."""
        md = f"""# 🔴 Cosmos Error: {self.severity.value.upper()}

## Summary
{self.summary}

## Cause
{self.cause}

## Affected Nodes
"""
        for node in self.affected_nodes:
            md += f"- `{node}`\n"
        
        md += "\n## Solution Steps\n"
        for i, step in enumerate(self.solution_steps, 1):
            md += f"{i}. {step}\n"
        
        if self.references:
            md += "\n## References\n"
            for ref in self.references:
                md += f"- {ref}\n"
        
        md += f"\n---\n*Confidence: {self.confidence:.0%} | Generated: {datetime.utcnow().isoformat()}*\n"
        return md
    
    def to_json(self) -> str:
        """Convierte a JSON."""
        return json.dumps({
            "summary": self.summary,
            "cause": self.cause,
            "affected_nodes": self.affected_nodes,
            "solution_steps": self.solution_steps,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "references": self.references,
            "metadata": self.metadata
        }, indent=2, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "summary": self.summary,
            "cause": self.cause,
            "affected_nodes": self.affected_nodes,
            "solution_steps": self.solution_steps,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "references": self.references,
            "metadata": self.metadata
        }


# ============================================================
# LLM PROVIDERS
# ============================================================

class LLMProvider:
    """Base class for LLM providers."""
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion."""
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1"
    ):
        self.base_url = base_url
        self.model = model
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using Ollama."""
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required for Ollama. Install: pip install httpx")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                }
            )
            response.raise_for_status()
            return response.json()["response"]


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using OpenAI."""
        if not self.api_key:
            raise RuntimeError("OpenAI API key required")
        
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required for OpenAI")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


class GrokProvider(LLMProvider):
    """xAI Grok provider."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-2"
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.model = model
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using Grok."""
        if not self.api_key:
            raise RuntimeError("xAI API key required")
        
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required for Grok")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


# ============================================================
# LLM EXPLAINER AGENT
# ============================================================

class LLMExplainerAgent:
    """
    Agente que explica errores de Cosmos usando LLM.
    
    Features:
    - Explicaciones en lenguaje natural
    - Integración con Knowledge Graph
    - Sugerencias de solución
    - Múltiples formatos de salida
    
    Usage:
        agent = LLMExplainerAgent()
        explanation = await agent.explain(error_context)
        print(explanation.to_markdown())
    """
    
    name: str = "LLMExplainerAgent"
    version: str = "0.4.5-rc1"
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        knowledge_graph: Optional[Any] = None,
        default_format: OutputFormat = OutputFormat.MARKDOWN
    ):
        """
        Inicializa el agente.
        
        Args:
            llm_provider: Provider de LLM (Ollama, OpenAI, Grok)
            knowledge_graph: Knowledge Graph para contexto adicional
            default_format: Formato de salida por defecto
        """
        self.llm = llm_provider or self._auto_detect_provider()
        self.kg = knowledge_graph
        self.default_format = default_format
        
        logger.info(f"LLMExplainerAgent initialized with {type(self.llm).__name__}")
    
    def _auto_detect_provider(self) -> LLMProvider:
        """Detecta el mejor provider disponible."""
        # Try Ollama first (local, fast)
        try:
            if HTTPX_AVAILABLE:
                provider = OllamaProvider()
                # Quick test
                return provider
        except:
            pass
        
        # Try OpenAI
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider()
        
        # Try Grok
        if os.getenv("XAI_API_KEY"):
            return GrokProvider()
        
        raise RuntimeError("No LLM provider available. Set OLLAMA_URL, OPENAI_API_KEY, or XAI_API_KEY")
    
    async def explain(
        self,
        error_context: ErrorContext,
        format: Optional[OutputFormat] = None,
        include_kg_context: bool = True
    ) -> Explanation:
        """
        Genera explicación para un error de Cosmos.
        
        Args:
            error_context: Contexto del error
            format: Formato de salida
            include_kg_context: Incluir contexto del Knowledge Graph
            
        Returns:
            Explanation con análisis detallado
        """
        format = format or self.default_format
        
        # Build context for LLM
        context_prompt = self._build_context(error_context, include_kg_context)
        
        # Generate explanation
        try:
            llm_response = await self.llm.complete(context_prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._fallback_explanation(error_context)
        
        # Parse response
        explanation = self._parse_llm_response(llm_response, error_context)
        
        return explanation
    
    def _build_context(
        self,
        error_context: ErrorContext,
        include_kg_context: bool
    ) -> str:
        """Construye el prompt de contexto."""
        
        prompt = f"""# Cosmos Error Analysis

You are a Cosmos DSL expert. Analyze the following error and provide a detailed explanation.

## Error Details
- **Error Code**: {error_context.error_code}
- **Message**: {error_context.error_message}
- **File**: {error_context.file_path or 'Unknown'}
- **Line**: {error_context.line_number or 'Unknown'}
"""
        
        if error_context.related_nodes:
            prompt += f"- **Related Nodes**: {', '.join(error_context.related_nodes)}\n"
        
        if error_context.cosmos_source:
            prompt += f"\n## Cosmos Source\n```cosmos\n{error_context.cosmos_source}\n```\n"
        
        # Knowledge Graph context
        if include_kg_context and self.kg:
            kg_context = self._get_kg_context(error_context)
            if kg_context:
                prompt += f"\n## Knowledge Graph Context\n{kg_context}\n"
        
        prompt += """
## Task
Provide a detailed explanation with:
1. **Summary**: Brief overview of the problem (1-2 sentences)
2. **Cause**: Root cause analysis
3. **Affected Nodes**: List of nodes impacted
4. **Solution Steps**: Numbered list of fixes
5. **Severity**: critical/error/warning/info

Format your response as a JSON object:
```json
{
  "summary": "...",
  "cause": "...",
  "affected_nodes": ["node1", "node2"],
  "solution_steps": ["step1", "step2", "step3"],
  "severity": "error",
  "confidence": 0.95
}
```
"""
        
        return prompt
    
    def _get_kg_context(self, error_context: ErrorContext) -> Optional[str]:
        """Obtiene contexto del Knowledge Graph."""
        if not self.kg:
            return None
        
        try:
            context_parts = []
            
            # Query for related nodes
            for node in error_context.related_nodes[:5]:
                if hasattr(self.kg, 'get_subgraph'):
                    subgraph = self.kg.get_subgraph(node, depth=1)
                    if subgraph:
                        context_parts.append(f"Node {node}: {subgraph}")
            
            # Get recent errors
            if hasattr(self.kg, 'query'):
                results = self.kg.query(error_context.error_code, k=3)
                if results:
                    context_parts.append(f"Similar errors: {results}")
            
            return "\n".join(context_parts) if context_parts else None
            
        except Exception as e:
            logger.warning(f"KG context failed: {e}")
            return None
    
    def _parse_llm_response(
        self,
        llm_response: str,
        error_context: ErrorContext
    ) -> Explanation:
        """Parsea la respuesta del LLM."""
        
        # Try to extract JSON
        json_match = None
        try:
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return Explanation(
                    summary=data.get("summary", "Error analysis"),
                    cause=data.get("cause", "Unknown cause"),
                    affected_nodes=data.get("affected_nodes", error_context.related_nodes),
                    solution_steps=data.get("solution_steps", ["Review the error details"]),
                    severity=Severity(data.get("severity", "error")),
                    confidence=float(data.get("confidence", 0.5)),
                    references=[],
                    raw_llm_response=llm_response,
                    metadata={
                        "error_code": error_context.error_code,
                        "file_path": error_context.file_path,
                        "llm_provider": type(self.llm).__name__
                    }
                )
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback: parse as text
        return Explanation(
            summary=llm_response[:200],
            cause=llm_response[200:500] if len(llm_response) > 200 else "",
            affected_nodes=error_context.related_nodes,
            solution_steps=["Review the full explanation"],
            severity=Severity.ERROR,
            confidence=0.3,
            raw_llm_response=llm_response,
            metadata={"fallback": True}
        )
    
    def _fallback_explanation(self, error_context: ErrorContext) -> Explanation:
        """Explicación fallback cuando LLM no está disponible."""
        
        # Generate basic explanation based on error code
        explanations = {
            "E401": {
                "summary": "Temporal constraint violation detected in Cosmos DAG",
                "cause": "start_after value is greater than or equal to end_before value",
                "solution_steps": [
                    "Check the temporal constraints in the affected node",
                    "Ensure start_after < end_before",
                    "Verify duration doesn't exceed the time window",
                    "Remove or adjust conflicting temporal constraints"
                ]
            },
            "E402": {
                "summary": "Temporal cycle detected in Cosmos DAG",
                "cause": "Circular dependency found in temporal constraints",
                "solution_steps": [
                    "Identify the nodes involved in the cycle",
                    "Remove one of the temporal dependencies",
                    "Restructure the DAG to break the cycle"
                ]
            },
            "E403": {
                "summary": "Invalid temporal order",
                "cause": "Temporal constraints violate DAG ordering",
                "solution_steps": [
                    "Review the temporal ordering of nodes",
                    "Ensure parent nodes have earlier temporal constraints"
                ]
            }
        }
        
        exp = explanations.get(
            error_context.error_code,
            {
                "summary": f"Cosmos error: {error_context.error_code}",
                "cause": error_context.error_message,
                "solution_steps": ["Review the error details and fix the issue"]
            }
        )
        
        return Explanation(
            summary=exp["summary"],
            cause=exp["cause"],
            affected_nodes=error_context.related_nodes,
            solution_steps=exp["solution_steps"],
            severity=Severity.ERROR,
            confidence=0.5,
            metadata={"fallback": True, "error_code": error_context.error_code}
        )
    
    async def explain_file(
        self,
        file_path: str,
        format: OutputFormat = OutputFormat.MARKDOWN
    ) -> Explanation:
        """
        Explica los errores en un archivo Cosmos.
        
        Args:
            file_path: Path al archivo .cosmos
            format: Formato de salida
            
        Returns:
            Explanation para el archivo
        """
        try:
            with open(file_path, 'r') as f:
                source = f.read()
        except Exception as e:
            raise ValueError(f"Cannot read file {file_path}: {e}")
        
        # Compile to get errors
        from cosmos.solvens_agent import CosmosCompilerAgent
        
        agent = CosmosCompilerAgent()
        result = await agent.run(source)
        
        if result.status.value == "APPROVED":
            return Explanation(
                summary="File compiled successfully - no errors found",
                cause="All validations passed",
                affected_nodes=[],
                solution_steps=[],
                severity=Severity.INFO,
                confidence=1.0
            )
        
        # Extract error context
        error_context = ErrorContext(
            error_code=result.metadata.get("error_code", "UNKNOWN"),
            error_message=result.content,
            file_path=file_path,
            cosmos_source=source
        )
        
        return await self.explain(error_context, format=format)
    
    async def batch_explain(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Explanation]:
        """
        Explica múltiples resultados de compilación.
        
        Args:
            results: Lista de resultados con error_code y metadata
            
        Returns:
            Lista de explanations
        """
        explanations = []
        
        for result in results:
            error_context = ErrorContext(
                error_code=result.get("error_code", "UNKNOWN"),
                error_message=result.get("content", ""),
                file_path=result.get("file_path"),
                cosmos_source=result.get("source")
            )
            
            explanation = await self.explain(error_context)
            explanations.append(explanation)
        
        return explanations


# ============================================================
# CLI INTERFACE
# ============================================================

async def main():
    """CLI for LLMExplainerAgent."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m cosmos.explainer <file.cosmos>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"Explaining errors in: {file_path}")
    print("=" * 60)
    
    agent = LLMExplainerAgent()
    
    try:
        explanation = await agent.explain_file(file_path)
        print(explanation.to_markdown())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
