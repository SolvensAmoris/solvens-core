"""
dag_renderer.py - DAG Renderer for Cosmos AST/DAG
================================================

Genera visualizaciones SVG y HTML de grafos Cosmos.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from html import escape


class NodeType(Enum):
    """Tipos de nodos en Cosmos DAG."""
    UNIVERSE = "universe"
    CELESTIAL_BODY = "celestial_body"
    LIGHT = "light"
    EVENT = "event"
    CONSTRAINT = "constraint"
    TASK = "task"
    PROVIDER = "provider"
    INPUT = "input"
    OUTPUT = "output"


class NodeStyle:
    """Estilos para nodos SVG."""
    
    COLORS = {
        NodeType.UNIVERSE: "#6366F1",      # Indigo
        NodeType.CELESTIAL_BODY: "#8B5CF6",  # Purple
        NodeType.LIGHT: "#F59E0B",           # Amber
        NodeType.EVENT: "#EF4444",           # Red
        NodeType.CONSTRAINT: "#EC4899",      # Pink
        NodeType.TASK: "#10B981",            # Emerald
        NodeType.PROVIDER: "#3B82F6",       # Blue
        NodeType.INPUT: "#06B6D4",           # Cyan
        NodeType.OUTPUT: "#84CC16",          # Lime
    }
    
    ICONS = {
        NodeType.UNIVERSE: "🌌",
        NodeType.CELESTIAL_BODY: "🪐",
        NodeType.LIGHT: "💡",
        NodeType.EVENT: "⚡",
        NodeType.CONSTRAINT: "🔒",
        NodeType.TASK: "📋",
        NodeType.PROVIDER: "🔌",
        NodeType.INPUT: "📥",
        NodeType.OUTPUT: "📤",
    }
    
    @classmethod
    def get_color(cls, node_type: NodeType) -> str:
        return cls.COLORS.get(node_type, "#6B7280")
    
    @classmethod
    def get_icon(cls, node_type: NodeType) -> str:
        return cls.ICONS.get(node_type, "●")


class EdgeStyle:
    """Estilos para aristas SVG."""
    
    COLORS = {
        "default": "#9CA3AF",
        "flow": "#3B82F6",
        "constraint": "#EF4444",
        "dependency": "#10B981",
        "temporal": "#F59E0B",
    }
    
    @classmethod
    def get_color(cls, edge_type: str = "default") -> str:
        return cls.COLORS.get(edge_type, cls.COLORS["default"])


@dataclass
class DAGNode:
    """Nodo del DAG para renderizado."""
    id: str
    label: str
    node_type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)
    x: float = 0
    y: float = 0


@dataclass
class DAGEdge:
    """Arista del DAG para renderizado."""
    source: str
    target: str
    label: str = ""
    edge_type: str = "default"


@dataclass
class DAGGraph:
    """Grafo completo para renderizado."""
    nodes: List[DAGNode] = field(default_factory=list)
    edges: List[DAGEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DAGRenderer:
    """
    Renderer para generar visualizaciones de DAG Cosmos.
    
    Usage:
        renderer = DAGRenderer()
        svg = renderer.render_svg(graph)
        html = renderer.render_html(graph)
        ascii_art = renderer.render_ascii(graph)
    """
    
    def __init__(
        self,
        width: int = 1200,
        height: int = 800,
        node_radius: int = 30,
        padding: int = 60
    ):
        self.width = width
        self.height = height
        self.node_radius = node_radius
        self.padding = padding
    
    def layout(self, graph: DAGGraph) -> DAGGraph:
        """
        Calcula posiciones de nodos usando layout de niveles.
        
        Algoritmo: Topological sort + level assignment
        """
        # Construcción de grafo de adyacencia
        adj: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
        in_degree: Dict[str, int] = {n.id: 0 for n in graph.nodes}
        
        for edge in graph.edges:
            adj[edge.source].append(edge.target)
            in_degree[edge.target] += 1
        
        # Topological sort
        levels: Dict[str, int] = {}
        queue = [n.id for n in graph.nodes if in_degree[n.id] == 0]
        level = 0
        
        while queue:
            next_queue = []
            for node_id in queue:
                levels[node_id] = level
                for neighbor in adj[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue
            level += 1
        
        # Nodos sin conexiones = nivel 0
        for node in graph.nodes:
            if node.id not in levels:
                levels[node.id] = 0
        
        # Asignar posiciones
        level_nodes: Dict[int, List[str]] = {}
        for node_id, lvl in levels.items():
            level_nodes.setdefault(lvl, []).append(node_id)
        
        node_width = (self.width - 2 * self.padding) / max(len(level_nodes), 1)
        
        for node in graph.nodes:
            lvl = levels.get(node.id, 0)
            nodes_at_level = level_nodes[lvl]
            idx = nodes_at_level.index(node.id)
            count = len(nodes_at_level)
            
            node.x = self.padding + idx * node_width + node_width / 2
            node.y = self.padding + lvl * 120 + 60
        
        return graph
    
    def render_svg(self, graph: DAGGraph) -> str:
        """Genera SVG del grafo."""
        graph = self.layout(graph)
        
        # Construcción de SVG
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" width="{self.width}" height="{self.height}">',
            '<defs>',
            '  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
            '    <polygon points="0 0, 10 3.5, 0 7" fill="#9CA3AF"/>',
            '  </marker>',
            '</defs>',
            '<style>',
            '.node-label { font-family: system-ui, sans-serif; font-size: 12px; text-anchor: middle; fill: white; }',
            '.node-icon { font-size: 16px; text-anchor: middle; fill: white; }',
            '.edge-label { font-family: system-ui, sans-serif; font-size: 10px; fill: #6B7280; }',
            '.graph-bg { fill: #1F2937; }',
            '.title { font-family: system-ui, sans-serif; font-size: 18px; fill: #F9FAFB; }',
            '.subtitle { font-family: system-ui, sans-serif; font-size: 12px; fill: #9CA3AF; }',
            '</style>',
            f'<rect width="100%" height="100%" class="graph-bg" rx="12"/>',
        ]
        
        # Título
        title = escape(str(graph.metadata.get("name", "Cosmos DAG")))
        svg_lines.append(f'<text x="20" y="35" class="title">{title}</text>')
        svg_lines.append(f'<text x="20" y="52" class="subtitle">{len(graph.nodes)} nodes, {len(graph.edges)} edges</text>')
        
        # Aristas
        node_map = {n.id: n for n in graph.nodes}
        for edge in graph.edges:
            if edge.source in node_map and edge.target in node_map:
                src = node_map[edge.source]
                tgt = node_map[edge.target]
                color = EdgeStyle.get_color(edge.edge_type)
                
                # Línea con flecha
                svg_lines.append(
                    f'<line x1="{src.x}" y1="{src.y}" x2="{tgt.x}" y2="{tgt.y}" '
                    f'stroke="{color}" stroke-width="2" marker-end="url(#arrowhead)"/>'
                )
                
                # Label si existe
                if edge.label:
                    mid_x = (src.x + tgt.x) / 2
                    mid_y = (src.y + tgt.y) / 2 - 5
                    svg_lines.append(
                        f'<text x="{mid_x}" y="{mid_y}" class="edge-label" text-anchor="middle">{escape(str(edge.label))}</text>'
                    )
        
        # Nodos
        for node in graph.nodes:
            color = NodeStyle.get_color(node.node_type)
            icon = NodeStyle.get_icon(node.node_type)
            
            # Círculo
            svg_lines.append(
                f'<circle cx="{node.x}" cy="{node.y}" r="{self.node_radius}" '
                f'fill="{color}" stroke="{color}" stroke-width="2" opacity="0.9"/>'
            )
            
            # Icono
            svg_lines.append(
                f'<text x="{node.x}" y="{node.y + 5}" class="node-icon" dominant-baseline="middle">{icon}</text>'
            )
            
            # Label debajo
            svg_lines.append(
                f'<text x="{node.x}" y="{node.y + self.node_radius + 15}" class="node-label" fill="#D1D5DB">{escape(str(node.label))}</text>'
            )
        
        svg_lines.append('</svg>')
        return '\n'.join(svg_lines)
    
    def render_html(self, graph: DAGGraph, dark_mode: bool = True) -> str:
        """Genera HTML interactivo."""
        svg = self.render_svg(graph)
        
        bg_color = "#0F172A" if dark_mode else "#FFFFFF"
        text_color = "#F9FAFB" if dark_mode else "#1F2937"
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(str(graph.metadata.get("name", "Cosmos DAG")))}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: {bg_color};
            color: {text_color};
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 2rem;
        }}
        h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #6366F1, #EC4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            color: #9CA3AF;
        }}
        .stats {{
            display: flex;
            gap: 2rem;
            margin: 1.5rem 0;
        }}
        .stat {{
            background: rgba(99, 102, 241, 0.1);
            padding: 1rem 1.5rem;
            border-radius: 8px;
            border: 1px solid rgba(99, 102, 241, 0.2);
        }}
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #6366F1;
        }}
        .stat-label {{
            font-size: 0.875rem;
            color: #9CA3AF;
        }}
        .graph-container {{
            background: #1F2937;
            border-radius: 12px;
            padding: 1rem;
            overflow-x: auto;
        }}
        .graph-container svg {{
            display: block;
            margin: 0 auto;
        }}
        .legend {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }}
        footer {{
            margin-top: 2rem;
            text-align: center;
            color: #6B7280;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌌 {escape(str(graph.metadata.get("name", "Cosmos DAG")))}</h1>
            <p class="subtitle">Cosmos Language Visualization</p>
        </header>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(graph.nodes)}</div>
                <div class="stat-label">Nodes</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(graph.edges)}</div>
                <div class="stat-label">Edges</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(set(n.node_type for n in graph.nodes))}</div>
                <div class="stat-label">Node Types</div>
            </div>
        </div>
        
        <div class="graph-container">
            {svg}
        </div>
        
        <div class="legend">
            {"".join(self._legend_item(nt) for nt in NodeType)}
        </div>
        
        <footer>
            Generated by Cosmos Visualizer v0.5.0 | Solvens Core
        </footer>
    </div>
</body>
</html>'''
        return html
    
    def _legend_item(self, node_type: NodeType) -> str:
        color = NodeStyle.get_color(node_type)
        icon = NodeStyle.get_icon(node_type)
        return f'<div class="legend-item"><div class="legend-color" style="background:{color}"></div>{icon} {node_type.value.replace("_", " ").title()}</div>'
    
    def render_ascii(self, graph: DAGGraph) -> str:
        """Genera representación ASCII art."""
        graph = self.layout(graph)
        
        node_map = {n.id: n for n in graph.nodes}
        lines = []
        
        # Header
        lines.append("╔══════════════════════════════════════════════════════╗")
        lines.append(f"║  🌌 {graph.metadata.get('name', 'Cosmos DAG'):<46}║")
        lines.append("╠══════════════════════════════════════════════════════╣")
        
        # Group by level
        levels: Dict[float, List[DAGNode]] = {}
        for node in graph.nodes:
            levels.setdefault(node.y, []).append(node)
        
        for y in sorted(levels.keys()):
            level_nodes = sorted(levels[y], key=lambda n: n.x)
            row = "║  "
            for node in level_nodes:
                icon = NodeStyle.get_icon(node.node_type)
                row += f"[{icon} {node.label[:10]:<10}] "
            row += " " * (55 - len(row) + 2) + "║"
            lines.append(row)
            
            # Aristas como líneas
            for edge in graph.edges:
                if edge.source in node_map and node_map[edge.source].y == y:
                    src = node_map[edge.source]
                    tgt = node_map.get(edge.target)
                    if tgt and tgt.y == y + 120:
                        lines.append(f"║       │ {edge.label or '→':<40}║")
        
        lines.append("╚══════════════════════════════════════════════════════╝")
        lines.append(f"  Nodes: {len(graph.nodes)} | Edges: {len(graph.edges)}")
        
        return '\n'.join(lines)
    
    def save(self, graph: DAGGraph, path: str, format: str = "auto") -> str:
        """
        Guarda el grafo en archivo.
        
        Args:
            graph: DAG a renderizar
            path: Ruta de salida (sin extensión)
            format: "svg", "html", "ascii", o "auto"
        
        Returns:
            Ruta del archivo guardado
        """
        path = Path(path)
        
        if format == "auto":
            format = path.suffix.lstrip(".") or "html"
        
        if format == "svg":
            content = self.render_svg(graph)
            path = path.with_suffix(".svg")
        elif format == "html":
            content = self.render_html(graph)
            path = path.with_suffix(".html")
        elif format == "ascii":
            content = self.render_ascii(graph)
            path = path.with_suffix(".txt")
        else:
            raise ValueError(f"Unknown format: {format}")
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        
        return str(path)


# ============================================================
# Demo
# ============================================================

def demo():
    """Demo del visualizador."""
    print("=" * 60)
    print("COSMOS VISUALIZER DEMO")
    print("=" * 60)
    
    # Crear grafo de ejemplo
    graph = DAGGraph(
        metadata={"name": "Research Agent Workflow"},
        nodes=[
            DAGNode("1", "Researcher", NodeType.TASK, {"model": "claude"}),
            DAGNode("2", "Coder", NodeType.TASK, {"model": "gpt-4"}),
            DAGNode("3", "Reviewer", NodeType.TASK, {"model": "gemini"}),
            DAGNode("4", "Claude", NodeType.PROVIDER, {"cost": "$0.01/1K"}),
            DAGNode("5", "GPT-4", NodeType.PROVIDER, {"cost": "$0.03/1K"}),
            DAGNode("6", "Gemini", NodeType.PROVIDER, {"cost": "$0.001/1K"}),
            DAGNode("7", "Query", NodeType.INPUT),
            DAGNode("8", "Result", NodeType.OUTPUT),
        ],
        edges=[
            DAGEdge("7", "1", "research", "flow"),
            DAGEdge("1", "2", "code", "flow"),
            DAGEdge("2", "3", "review", "flow"),
            DAGEdge("3", "8", "final", "flow"),
            DAGEdge("4", "1", "provider", "dependency"),
            DAGEdge("5", "2", "provider", "dependency"),
            DAGEdge("6", "3", "provider", "dependency"),
        ]
    )
    
    renderer = DAGRenderer()
    
    # ASCII
    print("\n[ASCII ART]")
    print(renderer.render_ascii(graph))
    
    # Guardar HTML
    html_path = renderer.save(graph, "cosmos_dag_demo", format="html")
    print(f"\n[HTML] Saved to: {html_path}")
    
    # Guardar SVG
    svg_path = renderer.save(graph, "cosmos_dag_demo", format="svg")
    print(f"[SVG] Saved to: {svg_path}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
