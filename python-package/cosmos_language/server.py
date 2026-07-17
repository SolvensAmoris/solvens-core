"""
Cosmos Language Server
======================

LSP implementation for Cosmos DSL.
Based on pygls library for Python LSP support.
"""

import logging
from typing import Optional
from pygls.server import LanguageServer
from pygls.capabilities import get_capability

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cosmos DSL keywords
COSMOS_KEYWORDS = [
    "universe", "planet", "light", "moon", "orbit",
    "start_on", "end_on", "expired_on", "duration",
    "depends_on", "parallel", "sequential", "fail_fast"
]

COSMOS_TYPES = [
    "string", "number", "boolean", "date", "duration"
]

# Diagnostic codes
DIAGNOSTIC_CODES = {
    "E001": "SyntaxError",
    "E401": "TemporalConstraintViolation",
    "E402": "DependencyCycle",
    "E403": "MissingRequiredField",
}


class CosmosLanguageServer(LanguageServer):
    """Cosmos DSL Language Server Protocol implementation."""
    
    def __init__(self):
        super().__init__()
        self.compile_results = {}
        
    def initialize(self, params=None):
        """Initialize the language server."""
        logger.info("Cosmos Language Server v1.0.0 initializing...")
        

def compile_cosmos(content: str) -> dict:
    """
    Compile Cosmos DSL content and return diagnostics.
    
    Args:
        content: Cosmos DSL source code
        
    Returns:
        Dictionary with diagnostics and AST
    """
    diagnostics = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Check for expired dates
        if 'expired_on:' in line:
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
            if date_match:
                from datetime import datetime
                try:
                    date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    if date < datetime.now():
                        diagnostics.append({
                            "range": {
                                "start": {"line": i - 1, "character": 0},
                                "end": {"line": i - 1, "character": len(line)}
                            },
                            "severity": 1,  # Error
                            "code": "E401",
                            "source": "cosmos-language",
                            "message": f"TemporalConstraintViolation: '{date_match.group(1)}' is in the past"
                        })
                except ValueError:
                    pass
                    
        # Check for syntax issues
        if line.strip().startswith('}') and not content[:content.find(line)].count('{') > content[:content.find(line)].count('}'):
            diagnostics.append({
                "range": {
                    "start": {"line": i - 1, "character": 0},
                    "end": {"line": i - 1, "character": len(line)}
                },
                "severity": 2,  # Warning
                "code": "E001",
                "source": "cosmos-language",
                "message": "Unmatched closing brace"
            })
    
    return {
        "diagnostics": diagnostics,
        "valid": len([d for d in diagnostics if d["severity"] == 1]) == 0
    }


# Create the server instance
server = CosmosLanguageServer()


@server.feature('textDocument/didOpen')
def did_open(params):
    """Handle document open."""
    text_doc = params['textDocument']
    uri = text_doc['uri']
    content = text_doc['text']
    
    logger.info(f"Document opened: {uri}")
    
    result = compile_cosmos(content)
    server.publish_diagnostics(uri, result['diagnostics'])


@server.feature('textDocument/didChange')
def did_change(params):
    """Handle document change."""
    text_doc = params['textDocument']
    uri = text_doc['uri']
    content = text_doc['text']
    
    result = compile_cosmos(content)
    server.publish_diagnostics(uri, result['diagnostics'])


@server.feature('textDocument/completion')
def completion(params):
    """Provide completion items."""
    return [
        {
            "label": kw,
            "kind": 14,  # Keyword
            "insertText": kw
        }
        for kw in COSMOS_KEYWORDS
    ] + [
        {
            "label": t,
            "kind": 7,  # Variable
            "insertText": t
        }
        for t in COSMOS_TYPES
    ]


@server.feature('textDocument/hover')
def hover(params):
    """Provide hover information."""
    pos = params['position']
    return {
        "contents": {
            "kind": "markdown",
            "value": "## Cosmos DSL\n\nCosmos is a domain-specific language for infrastructure with temporal constraints.\n\n### Keywords\n- `universe` - Root scope\n- `planet` - Resource definition\n- `light` - Dependency\n- `start_on` / `end_on` - Temporal bounds\n- `expired_on` - Expiration date"
        }
    }


def main():
    """Entry point for the language server."""
    logger.info("Starting Cosmos Language Server...")
    server.start()


if __name__ == "__main__":
    main()
