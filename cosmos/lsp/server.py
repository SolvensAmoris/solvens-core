"""
cosmos/lsp/server.py
====================

Cosmos Language Server Protocol (LSP) Implementation
====================================================

Features:
- Syntax highlighting
- Autocomplete
- Hover documentation
- Inline diagnostics (E401, E402, etc.)
- Go to definition
- Document symbols

Usage:
    python -m cosmos.lsp.server

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cosmos.solvens_agent import CosmosCompilerAgent, Status

logger = logging.getLogger("cosmos.lsp")

MESSAGE_TYPE_INFO = 1
MESSAGE_TYPE_WARNING = 2
MESSAGE_TYPE_ERROR = 3
COMPLETION_KIND_TEXT = 1
COMPLETION_KIND_CLASS = 5
COMPLETION_KIND_KEYWORD = 6
COMPLETION_KIND_VALUE = 12
DIAGNOSTIC_SEVERITY_ERROR = 1

COSMOS_KEYWORDS = [
    "cosmos", "end", "sun", "planet", "galaxy", "light", "star",
    "model", "connects_to", "from", "to", "duration",
    "start_after", "end_before", "parallel", "sequential"
]

COSMOS_NODE_TYPES = ["sun", "planet", "galaxy", "light", "star"]

COSMOS_MODELS = [
    "claude-3-sonnet", "claude-3-opus", "gpt-4", "gpt-4-turbo",
    "gemini-pro", "llama3", "mistral", "grok-2"
]

ERROR_DESCRIPTIONS = {
    "E401": "TemporalConstraintViolation: start_after >= end_before",
    "E402": "TemporalCycleDetected: circular dependency",
    "E403": "InvalidTemporalOrder: constraints violate DAG ordering",
    "E100": "SyntaxError: invalid Cosmos syntax",
    "E101": "InvalidUniverse: missing cosmos block",
    "E200": "DuplicateNode: node name already exists",
    "E201": "UndefinedReference: referenced node does not exist",
}


@dataclass
class LSPDocument:
    uri: str
    content: str
    version: int = 0
    diagnostics: List[Dict] = field(default_factory=list)


class CosmosLSPServer:
    def __init__(self):
        self.documents: Dict[str, LSPDocument] = {}
        self.agent = CosmosCompilerAgent(fail_fast=True)
        logger.info("Cosmos LSP Server initialized")
    
    async def handle_request(self, method: str, params: Any) -> Any:
        handlers = {
            "initialize": self._handle_initialize,
            "textDocument/didOpen": self._handle_did_open,
            "textDocument/didChange": self._handle_did_change,
            "textDocument/hover": self._handle_hover,
            "textDocument/completion": self._handle_completion,
            "textDocument/documentSymbol": self._handle_document_symbol,
            "shutdown": self._handle_shutdown,
        }
        
        handler = handlers.get(method)
        return await handler(params) if handler else None
    
    async def _handle_initialize(self, params: Dict) -> Dict:
        return {
            "capabilities": {
                "textDocument": {
                    "hover": {"dynamicRegistration": True},
                    "completion": {
                        "dynamicRegistration": True,
                        "completionItem": {"snippetSupport": True}
                    },
                    "documentSymbol": {"dynamicRegistration": True},
                },
                "workspace": {"applyEdit": True}
            },
            "serverInfo": {"name": "cosmos-lsp", "version": "0.4.5-rc1"}
        }
    
    async def _handle_did_open(self, params: Dict) -> None:
        text_doc = params.get("textDocument", {})
        uri = text_doc.get("uri")
        content = text_doc.get("text", "")
        version = text_doc.get("version", 0)
        
        self.documents[uri] = LSPDocument(uri=uri, content=content, version=version)
        await self._validate_document(uri)
    
    async def _handle_did_change(self, params: Dict) -> None:
        text_doc = params.get("textDocument", {})
        uri = text_doc.get("uri")
        version = text_doc.get("version", 0)
        
        changes = params.get("contentChanges", [])
        if uri in self.documents and changes:
            doc = self.documents[uri]
            doc.content = changes[-1].get("text", doc.content)
            doc.version = version
            await self._validate_document(uri)
    
    async def _handle_hover(self, params: Dict) -> Optional[Dict]:
        position = params.get("position", {})
        uri = params.get("textDocument", {}).get("uri")
        
        if uri not in self.documents:
            return None
        
        doc = self.documents[uri]
        line_num = position.get("line", 0)
        character = position.get("character", 0)
        
        lines = doc.content.split("\n")
        if line_num >= len(lines):
            return None
        
        line_content = lines[line_num]
        word = self._extract_word_at(line_content, character)
        
        if not word:
            return None
        
        doc_text = self._get_documentation(word)
        if not doc_text:
            return None
        
        return {
            "contents": {"kind": "markdown", "value": doc_text},
            "range": self._get_word_range(line_content, word, line_num)
        }
    
    async def _handle_completion(self, params: Dict) -> Dict:
        completions = []
        
        for keyword in COSMOS_KEYWORDS:
            completions.append({
                "label": keyword,
                "kind": COMPLETION_KIND_KEYWORD,
                "detail": "Cosmos keyword",
                "insertText": keyword
            })
        
        for node_type in COSMOS_NODE_TYPES:
            completions.append({
                "label": node_type,
                "kind": COMPLETION_KIND_CLASS,
                "detail": "Cosmos node type",
                "insertText": f"{node_type} ",
                "insertTextFormat": 2  # Snippet
            })
        
        for model in COSMOS_MODELS:
            completions.append({
                "label": model,
                "kind": COMPLETION_KIND_VALUE,
                "detail": "LLM Model"
            })
        
        return {"isIncomplete": False, "items": completions}
    
    async def _handle_document_symbol(self, params: Dict) -> List[Dict]:
        uri = params.get("textDocument", {}).get("uri")
        if uri not in self.documents:
            return []
        
        return self._extract_symbols(self.documents[uri].content)
    
    async def _handle_shutdown(self, params: Dict) -> None:
        return None
    
    async def _validate_document(self, uri: str) -> None:
        if uri not in self.documents:
            return
        
        doc = self.documents[uri]
        result = await self.agent.run(doc.content)
        
        diagnostics = []
        
        if result.status != Status.APPROVED:
            error_code = result.metadata.get("error_code", "E100")
            error_desc = ERROR_DESCRIPTIONS.get(error_code, result.content)
            
            line_num = 0
            for i, line in enumerate(doc.content.split("\n")):
                if "start_after" in line or "end_before" in line:
                    line_num = i
                    break
            
            diagnostics.append({
                "range": {
                    "start": {"line": line_num, "character": 0},
                    "end": {"line": line_num, "character": len(lines[line_num]) if (lines := doc.content.split("\n")) and line_num < len(lines) else 0}
                },
                "severity": DIAGNOSTIC_SEVERITY_ERROR,
                "code": error_code,
                "source": "cosmos-lsp",
                "message": f"[{error_code}] {error_desc}"
            })
        
        doc.diagnostics = diagnostics
    
    def _extract_word_at(self, line: str, character: int) -> Optional[str]:
        if character >= len(line):
            return None
        start = character
        end = character
        while start > 0 and line[start - 1].isalnum():
            start -= 1
        while end < len(line) and line[end].isalnum():
            end += 1
        return line[start:end] if start < end else None
    
    def _get_word_range(self, line: str, word: str, line_num: int) -> Dict:
        start = line.find(word)
        if start == -1:
            start = 0
        return {
            "start": {"line": line_num, "character": start},
            "end": {"line": line_num, "character": start + len(word)}
        }
    
    def _get_documentation(self, word: str) -> Optional[str]:
        docs = {
            "cosmos": "**cosmos** `name` { ... }\nDefines a new Cosmos universe.",
            "planet": "**planet** `name` { ... }\nDefines a task node in the DAG.",
            "sun": "**sun** `name`\nDefines the entry point/orchestrator.",
            "galaxy": "**galaxy** `name` { ... }\nDefines a cluster of nodes.",
            "model": "**model**: `model-name`\nSpecifies the LLM model.",
            "connects_to": "**connects_to**: `node`\nSpecifies dependencies.",
            "duration": "**duration**: `seconds`\nExpected task duration.",
            "start_after": "**start_after**: `time`\nMinimum start time (temporal constraint).",
            "end_before": "**end_before**: `time`\nMaximum end time (temporal constraint).",
        }
        return docs.get(word)
    
    def _extract_symbols(self, content: str) -> List[Dict]:
        import re
        symbols = []
        lines = content.split("\n")
        
        for i, line in enumerate(lines):
            match = re.match(r'cosmos\s+(\w+)', line)
            if match:
                symbols.append({
                    "name": match.group(1),
                    "kind": 11,
                    "range": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}}
                })
            
            for node_type in COSMOS_NODE_TYPES:
                pattern = rf'{node_type}\s+(\w+)'
                match = re.match(pattern, line)
                if match:
                    symbols.append({
                        "name": match.group(1),
                        "kind": 5 if node_type == "sun" else 6,
                        "detail": node_type,
                        "range": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}}
                    })
        
        return symbols


class JSONRPCServer:
    def __init__(self):
        self.lsp = CosmosLSPServer()
        self.running = True
    
    async def handle_message(self, message: Dict) -> Optional[Dict]:
        method = message.get("method")
        params = message.get("params")
        msg_id = message.get("id")
        
        if method == "exit":
            self.running = False
            return None
        
        if msg_id is None:
            await self.lsp.handle_request(method, params)
            return None
        
        try:
            result = await self.lsp.handle_request(method, params)
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}
    
    async def run(self):
        logger.info("Cosmos LSP Server starting...")
        
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                message = json.loads(line)
                response = await self.handle_message(message)
                if response:
                    print(json.dumps(response), flush=True)
            except Exception as e:
                logger.error(f"Server error: {e}")
        
        logger.info("Cosmos LSP Server stopped")


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    server = JSONRPCServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
