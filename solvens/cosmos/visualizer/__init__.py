"""
Cosmos Visualizer - DAG Renderer for Cosmos AST/DAG
====================================================

Genera representaciones visuales de grafos Cosmos:
- SVG estático
- HTML interactivo con hover/click
- Terminal output con ASCII art

Autor: Luis Alberto Burciaga Miker
Version: 0.5.0
"""

from .dag_renderer import DAGRenderer, NodeStyle, EdgeStyle
from .timeline_view import TimelineView
from .web_preview import WebPreview

__all__ = [
    "DAGRenderer",
    "NodeStyle", 
    "EdgeStyle",
    "TimelineView",
    "WebPreview",
]

__version__ = "0.5.0"
