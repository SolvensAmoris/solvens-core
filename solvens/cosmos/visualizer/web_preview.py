"""
web_preview.py - Interactive Web Preview Server
===============================================

Serve interactive Cosmos DAG previews in browser.
"""

import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path
from typing import Optional
import tempfile


class CosmosPreviewServer:
    """
    HTTP server for interactive Cosmos DAG preview.
    
    Usage:
        server = CosmosPreviewServer()
        server.serve(html_content="<html>...")
        # Opens browser automatically
    """
    
    def __init__(
        self,
        port: int = 8765,
        host: str = "localhost",
        open_browser: bool = True
    ):
        self.port = port
        self.host = host
        self.open_browser = open_browser
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.temp_dir: Optional[tempfile.TemporaryDirectory] = None
    
    def _create_handler(self, content: str):
        """Crea handler HTTP que sirve el contenido."""
        
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.content = content.encode() if isinstance(content, str) else content
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.send_header("Content-Length", len(self.content))
                self.end_headers()
                self.wfile.write(self.content)
            
            def log_message(self, format, *args):
                pass  # Silencia logs
        
        return Handler
    
    def serve(self, html_content: str) -> str:
        """
        Inicia el servidor y opcionalmente abre el navegador.
        
        Returns:
            URL del servidor
        """
        # Crear handler con contenido
        Handler = self._create_handler(html_content)
        
        # Crear servidor
        self.server = socketserver.TCPServer(
            (self.host, self.port),
            Handler,
            bind_and_activate=False
        )
        self.server.allow_reuse_address = True
        self.server.server_bind()
        self.server.server_activate()
        
        # Iniciar en thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        
        url = f"http://{self.host}:{self.port}"
        
        if self.open_browser:
            webbrowser.open(url)
        
        return url
    
    def stop(self):
        """Detiene el servidor."""
        if self.server:
            self.server.shutdown()
            self.server = None


class WebPreview:
    """
    High-level API para previsualización web.
    
    Usage:
        preview = WebPreview()
        preview.show(dag_graph)
        # Opens browser with interactive DAG
    """
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.server: Optional[CosmosPreviewServer] = None
    
    def show(self, html_content: str) -> str:
        """
        Muestra contenido HTML en el navegador.
        
        Returns:
            URL del preview
        """
        if self.server:
            self.server.stop()
        
        self.server = CosmosPreviewServer(port=self.port)
        return self.server.serve(html_content)
    
    def show_dag(self, dag_graph) -> str:
        """
        Muestra DAG en el navegador.
        
        Args:
            dag_graph: DAGGraph instance
        
        Returns:
            URL del preview
        """
        from .dag_renderer import DAGRenderer
        
        renderer = DAGRenderer()
        html = renderer.render_html(dag_graph)
        
        return self.show(html)
    
    def stop(self):
        """Detiene el preview."""
        if self.server:
            self.server.stop()
            self.server = None


# ============================================================
# CLI Integration
# ============================================================

def preview_command(file_path: str, port: int = 8765):
    """
    CLI command para previsualizar archivos Cosmos.
    
    Usage:
        python -m solvens.cosmos.visualizer.web_preview preview <file.cosmos>
    """
    from pathlib import Path
    from ..parser import CosmosParser
    from ..dag import CosmosDAG
    from .dag_renderer import DAGRenderer
    
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Parsear archivo Cosmos
    parser = CosmosParser()
    with open(path) as f:
        content = f.read()
    
    try:
        ast = parser.parse(content)
    except Exception as e:
        print(f"Parse error: {e}")
        return
    
    # Construir DAG
    dag = CosmosDAG.from_ast(ast)
    
    # Renderizar
    renderer = DAGRenderer()
    
    # Crear nodos del visualizador
    from .dag_renderer import DAGGraph, DAGNode, DAGEdge, NodeType
    
    viz_nodes = []
    viz_edges = []
    
    for node in dag.nodes:
        node_type = _infer_node_type(node)
        viz_nodes.append(DAGNode(
            id=node.get("id", node.get("name", "unknown")),
            label=node.get("name", "Node"),
            node_type=node_type,
            properties=node
        ))
    
    for edge in dag.edges:
        viz_edges.append(DAGEdge(
            source=edge.get("from", ""),
            target=edge.get("to", ""),
            label=edge.get("type", "flow")
        ))
    
    viz_dag = DAGGraph(
        nodes=viz_nodes,
        edges=viz_edges,
        metadata={"name": path.stem}
    )
    
    html = renderer.render_html(viz_dag)
    
    # Mostrar
    preview = WebPreview(port=port)
    url = preview.show(html)
    
    print(f"Opening preview at: {url}")
    return url


def _infer_node_type(node: dict) -> NodeType:
    """Infiere el tipo de nodo basado en el contenido."""
    name = node.get("name", "").lower()
    node_type = node.get("type", "")
    
    if node_type == "universe":
        return NodeType.UNIVERSE
    elif node_type == "light":
        return NodeType.LIGHT
    elif node_type == "celestial_body":
        return NodeType.CELESTIAL_BODY
    elif "event" in name or "trigger" in name:
        return NodeType.EVENT
    elif "constraint" in name or "restringido" in name:
        return NodeType.CONSTRAINT
    elif "task" in name or "agent" in name:
        return NodeType.TASK
    elif "provider" in name or "model" in name:
        return NodeType.PROVIDER
    elif "input" in name or "query" in name:
        return NodeType.INPUT
    elif "output" in name or "result" in name:
        return NodeType.OUTPUT
    else:
        return NodeType.TASK


# ============================================================
# Demo
# ============================================================

def demo():
    """Demo del web preview."""
    print("=" * 60)
    print("COSMOS WEB PREVIEW DEMO")
    print("=" * 60)
    
    from .dag_renderer import DAGRenderer, DAGGraph, DAGNode, DAGEdge, NodeType
    
    # Crear grafo de ejemplo
    graph = DAGGraph(
        metadata={"name": "Agent Orchestration Demo"},
        nodes=[
            DAGNode("1", "User Input", NodeType.INPUT),
            DAGNode("2", "Router", NodeType.TASK),
            DAGNode("3", "Claude", NodeType.PROVIDER),
            DAGNode("4", "GPT-4", NodeType.PROVIDER),
            DAGNode("5", "Aggregator", NodeType.TASK),
            DAGNode("6", "Output", NodeType.OUTPUT),
        ],
        edges=[
            DAGEdge("1", "2", "route", "flow"),
            DAGEdge("2", "3", "research", "flow"),
            DAGEdge("2", "4", "code", "flow"),
            DAGEdge("3", "5", "results", "flow"),
            DAGEdge("4", "5", "results", "flow"),
            DAGEdge("5", "6", "final", "flow"),
        ]
    )
    
    renderer = DAGRenderer()
    html = renderer.render_html(graph)
    
    preview = WebPreview(port=8765)
    url = preview.show(html)
    
    print(f"\nPreview server running at: {url}")
    print("Browser should open automatically.")
    print("\nPress Ctrl+C to stop.")
    
    # Mantener vivo
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        preview.stop()
        print("\nServer stopped.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
