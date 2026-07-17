# strassen_recursion_tree.py
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # Sin pantalla
import matplotlib.pyplot as plt
from dataclasses import dataclass


@dataclass
class RecursionNode:
    level: int
    label: str


class StrassenVisualizer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_count = 0

    def strassen_with_tree(self, n: int, parent=None):
        """Strassen recursivo que construye el árbol."""
        current_id = self.node_count
        self.node_count += 1
        label = f"Strassen(n={n})"
        
        self.graph.add_node(current_id, label=label, level=n)
        if parent is not None:
            self.graph.add_edge(parent, current_id)
        
        if n <= 64:
            return current_id  # Hoja
        
        mid = n // 2
        child_ids = []
        for i in range(7):  # 7 multiplicaciones Strassen
            child_id = self.strassen_with_tree(mid, current_id)
            child_ids.append(child_id)
        
        return current_id

    def visualize(self, max_size=256, output_path="strassen_tree.png"):
        self.graph.clear()
        self.node_count = 0
        root = self.strassen_with_tree(max_size)
        
        print(f"Árbol generado: {self.graph.number_of_nodes()} nodos, {self.graph.number_of_edges()} aristas")
        
        # Usar layout jerárquico para mejor visualización
        pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        plt.figure(figsize=(16, 10))
        nx.draw(
            self.graph, pos, 
            node_size=100, 
            node_color="lightblue", 
            font_size=4, 
            arrows=True,
            arrowsize=5,
            edge_color="gray",
            alpha=0.8
        )
        plt.title(f"Árbol de Recursión Strassen Topológico (n={max_size})", fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Visualización guardada en: {output_path}")
        plt.close()


# Ejecución
if __name__ == "__main__":
    viz = StrassenVisualizer()
    viz.visualize(128)  # Tamaño pequeño para demo
    print("\n✓ Visualización completada")
