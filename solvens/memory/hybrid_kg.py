"""
solvens/memory/hybrid_kg.py
===========================

HYBRID KNOWLEDGE GRAPH v0.2
===========================

Fusiona Graph + Vector retrieval para agents con memoria real.

Features:
- ChromaDB para vector storage
- NetworkX para knowledge graph
- Sentence transformers para embeddings
- Hybrid retrieval (vector + graph traversal)
- Cosmos DAG enrichment

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("solvens.memory.hybrid")


# ============================================================
# TRIPLE EXTRACTOR (Simple rule-based)
# ============================================================

class TripleExtractor:
    """
    Extrae triples (subject, predicate, object) de texto.
    
    Usa patrones simples para MVP.
    LLM-based extraction disponible via router.
    """
    
    # Patterns for relation extraction
    PATTERNS = [
        # "X is Y" / "X are Y"
        (r"(\w+)\s+is\s+(\w+)", "{0} is {1}"),
        (r"(\w+)\s+are\s+(\w+)", "{0} is {1}"),
        
        # "X works at Y" / "X is part of Y"
        (r"(\w+)\s+works?\s+(?:at|in|for)\s+(\w+)", "works_for"),
        (r"(\w+)\s+is\s+part\s+of\s+(\w+)", "part_of"),
        
        # "X owns Y" / "X has Y"
        (r"(\w+)\s+owns?\s+(\w+)", "owns"),
        (r"(\w+)\s+has\s+(\w+)", "has"),
        
        # "X is based in Y"
        (r"(\w+)\s+is\s+based\s+(?:in|at)\s+(\w+)", "located_in"),
        
        # "X competes with Y" / "X vs Y"
        (r"(\w+)\s+competes\s+with\s+(\w+)", "competes_with"),
        
        # "X acquired Y"
        (r"(\w+)\s+acquired\s+(\w+)", "acquired"),
    ]
    
    RELATION_MAP = {
        "is": "same_as",
        "works_for": "employed_by",
        "part_of": "member_of",
        "owns": "owner_of",
        "has": "possesses",
        "located_in": "based_in",
        "competes_with": "rival_of",
        "acquired": "acquired_by",
    }
    
    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        """Extrae triples del texto."""
        triples = []
        import re
        
        for pattern, relation in self.PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    subj = match.group(1).lower()
                    obj = match.group(2).lower()
                    rel = self.RELATION_MAP.get(relation, relation)
                    triples.append((subj, rel, obj))
        
        return triples
    
    async def extract_with_llm(self, text: str, router) -> List[Tuple[str, str, str]]:
        """
        Extrae triples usando LLM para mejor calidad.
        
        Args:
            text: Texto a procesar
            router: SmartRouter instance
            
        Returns:
            Lista de triples (subject, predicate, object)
        """
        prompt = f"""Extract knowledge triples from this text.
Return as JSON list of [subject, predicate, object].

Text: {text[:500]}

Examples:
- "Apple is a tech company" → ["apple", "is_a", "tech_company"]
- "Microsoft acquired GitHub" → ["microsoft", "acquired", "github"]
- "Google is based in Mountain View" → ["google", "located_in", "mountain_view"]
"""
        
        result = await router.execute(prompt)
        content = result.get("content", "[]")
        
        # Parse JSON response
        import json
        try:
            triples = json.loads(content)
            return [(t[0].lower(), t[1].lower().replace(" ", "_"), t[2].lower()) for t in triples]
        except:
            logger.warning("Failed to parse LLM triples, falling back to rule-based")
            return self.extract(text)


# ============================================================
# ENTITY EXTRACTOR
# ============================================================

class EntityExtractor:
    """Extrae entidades nombradas de texto."""
    
    COMMON_TYPES = {
        "ORG": ["company", "organization", "corp", "inc", "llc", "gmbh"],
        "PRODUCT": ["product", "service", "platform", "tool"],
        "PERSON": ["ceo", "founder", "cto", "president", "director"],
        "LOCATION": ["city", "country", "region", "headquarters"],
        "TECH": ["ai", "ml", "llm", "api", "sdk", "framework"],
    }
    
    def extract(self, text: str) -> List[Dict[str, str]]:
        """Extrae entidades con tipos."""
        import re
        
        entities = []
        text_lower = text.lower()
        
        # Named patterns
        patterns = {
            "COMPANY": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|LLC|GmbH|Ltd)\b",
            "PRODUCT": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Platform|Tool|Service|API)\b",
            "PRODUCT_SIMPLE": r"(?:uses?|built with|powered by)\s+([A-Z][a-z]+)",
        }
        
        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entities.append({
                    "text": match.group(1),
                    "type": entity_type,
                    "start": match.start(),
                    "end": match.end()
                })
        
        return entities


# ============================================================
# HYBRID KNOWLEDGE GRAPH
# ============================================================

@dataclass
class KnowledgeTriple:
    """Triple de conocimiento."""
    subject: str
    predicate: str
    object: str
    source: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Resultado de retrieval."""
    content: str
    score: float
    source: str
    entities: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)


class HybridKnowledgeGraph:
    """
    Hybrid Knowledge Graph que fusiona:
    - Vector embeddings (ChromaDB)
    - Knowledge Graph (NetworkX)
    
    Uso:
        kg = HybridKnowledgeGraph()
        await kg.ingest(["Document about Apple..."], [{"source": "legal"}])
        
        results = kg.hybrid_retrieve("Apple legal risks")
        
        # Enrich Cosmos DAG
        executor.enrich_with_knowledge(dag, query)
    """
    
    def __init__(
        self,
        collection_name: str = "solvens_knowledge",
        persist_path: str = "./.solvens/vector_db",
        embedder_name: str = "all-MiniLM-L6-v2",
        enable_llm_extraction: bool = False
    ):
        self.collection_name = collection_name
        self.persist_path = persist_path
        self.enable_llm_extraction = enable_llm_extraction
        
        # Try imports
        self._chroma = None
        self._nx = None
        self._embedder = None
        
        # Node embeddings
        self.node_embeddings: Dict[str, List[float]] = {}  # node_id -> embedding
        self._node_collection = None
        
        self._init_components()
        
        # Triple extractor
        self.triple_extractor = TripleExtractor()
        self.entity_extractor = EntityExtractor()
        
        logger.info(f"HybridKnowledgeGraph initialized (chroma={self._chroma is not None}, nx={self._nx is not None})")
    
    def _init_components(self):
        """Inicializa componentes opcionales."""
        # ChromaDB
        try:
            import chromadb
            os.makedirs(self.persist_path, exist_ok=True)
            self._chroma = chromadb.PersistentClient(path=self.persist_path)
            self._collection = self._chroma.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Solvens Hybrid Knowledge Base"}
            )
            # Node collection
            self._node_collection = self._chroma.get_or_create_collection(
                name=f"{self.collection_name}_nodes",
                metadata={"hnsw:space": "cosine", "description": "Node embeddings"}
            )
            logger.info("ChromaDB initialized with node collection")
        except ImportError:
            logger.warning("ChromaDB not installed. Run: pip install chromadb")
            self._collection = None
            self._node_collection = None
        
        # NetworkX
        try:
            import networkx as nx
            self._nx = nx
            self._graph = nx.MultiDiGraph()
            logger.info("NetworkX initialized")
        except ImportError:
            logger.warning("NetworkX not installed. Run: pip install networkx")
            self._graph = None
        
        # Sentence Transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(embedder_name)
            logger.info(f"Embedder loaded: {embedder_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Run: pip install sentence-transformers")
            self._embedder = None
    
    def ingest(
        self,
        texts: List[str],
        metadata: List[Dict[str, Any]] = None,
        extract_triples: bool = True
    ) -> int:
        """
        Ingesta documentos al knowledge graph.
        
        Args:
            texts: Lista de documentos
            metadata: Metadata por documento
            extract_triples: Si extraer triples de conocimiento
            
        Returns:
            Número de documentos ingeridos
        """
        if metadata is None:
            metadata = [{} for _ in texts]
        
        ingested = 0
        
        for idx, (text, meta) in enumerate(zip(texts, metadata)):
            doc_id = meta.get("id", f"doc_{uuid.uuid4().hex[:8]}")
            
            # 1. Vector embedding
            if self._collection and self._embedder:
                try:
                    embedding = self._embedder.encode([text])[0].tolist()
                    self._collection.add(
                        documents=[text],
                        embeddings=[embedding],
                        ids=[doc_id],
                        metadatas=[{**meta, "text_hash": hashlib.md5(text.encode()).hexdigest()}]
                    )
                    ingested += 1
                except Exception as e:
                    logger.error(f"Vector ingestion failed for {doc_id}: {e}")
            
            # 2. Graph triples
            if extract_triples and self._graph:
                triples = self.triple_extractor.extract(text)
                
                for subj, pred, obj in triples:
                    self._graph.add_edge(
                        subj, obj,
                        relation=pred,
                        source=doc_id,
                        **meta
                    )
            
            # 3. Entities
            if self._graph:
                entities = self.entity_extractor.extract(text)
                for ent in entities:
                    if ent["text"] not in self._graph:
                        self._graph.add_node(
                            ent["text"],
                            type=ent["type"],
                            **meta
                        )
        
        logger.info(f"Ingested {ingested} documents, {len(self._graph.nodes) if self._graph else 0} nodes")
        
        return ingested
    
    async def ingest_with_llm(
        self,
        texts: List[str],
        metadata: List[Dict[str, Any]] = None,
        router = None
    ) -> int:
        """Ingesta usando LLM para mejor extracción."""
        if not self.enable_llm_extraction or not router:
            return self.ingest(texts, metadata, extract_triples=True)
        
        ingested = 0
        
        for idx, (text, meta) in enumerate(zip(texts, metadata)):
            doc_id = meta.get("id", f"doc_{uuid.uuid4().hex[:8]}")
            
            # Vector
            if self._collection and self._embedder:
                embedding = self._embedder.encode([text])[0].tolist()
                self._collection.add(
                    documents=[text],
                    embeddings=[embedding],
                    ids=[doc_id],
                    metadatas=[meta]
                )
                ingested += 1
            
            # LLM triples
            triples = await self.triple_extractor.extract_with_llm(text, router)
            
            for subj, pred, obj in triples:
                self._graph.add_edge(
                    subj, obj,
                    relation=pred,
                    source=doc_id,
                    extracted_by="llm"
                )
        
        return ingested
    
    def hybrid_retrieve(
        self,
        query: str,
        k: int = 5,
        graph_depth: int = 2,
        alpha: float = 0.5
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval: vector similarity + graph traversal.
        
        Args:
            query: Query string
            k: Número de resultados
            graph_depth: Profundidad de traversal en graph
            alpha: Balance entre vector (1) y graph (0)
            
        Returns:
            Lista de RetrievalResult ordenados por score
        """
        results = []
        
        # 1. Vector retrieval
        if self._collection and self._embedder:
            query_emb = self._embedder.encode([query])[0].tolist()
            vector_results = self._collection.query(
                query_embeddings=[query_emb],
                n_results=k
            )
            
            for i, (doc, dist) in enumerate(zip(
                vector_results.get("documents", [[]])[0],
                vector_results.get("distances", [[]])[0]
            )):
                score = 1 - min(dist, 1)  # Convert distance to similarity
                meta = vector_results.get("metadatas", [[{}]])[0][i]
                
                results.append(RetrievalResult(
                    content=doc,
                    score=score * alpha,  # Weight by alpha
                    source=meta.get("source", "vector"),
                    entities=[],
                    relations=[]
                ))
        
        # 2. Graph expansion
        if self._graph:
            entities = self.entity_extractor.extract(query)
            graph_results = []
            
            for ent in entities:
                ent_text = ent["text"]
                
                if ent_text in self._graph:
                    # Get neighbors
                    try:
                        neighbors = list(self._graph.neighbors(ent_text))
                        
                        for neighbor in neighbors[:graph_depth]:
                            edge_data = self._graph.get_edge_data(ent_text, neighbor)
                            
                            if edge_data:
                                for data in edge_data.values():
                                    relation = data.get("relation", "related_to")
                                    graph_results.append({
                                        "entity": ent_text,
                                        "neighbor": neighbor,
                                        "relation": relation,
                                        "score": 0.8 * (1 - alpha)  # Weight by alpha
                                    })
                    except Exception as e:
                        logger.debug(f"Graph traversal error: {e}")
            
            # Add graph results
            for gr in graph_results:
                results.append(RetrievalResult(
                    content=f"{gr['entity']} {gr['relation']} {gr['neighbor']}",
                    score=gr["score"],
                    source="graph",
                    entities=[gr["entity"], gr["neighbor"]],
                    relations=[gr["relation"]]
                ))
        
        # 3. Merge and rank
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:k]
    
    def get_subgraph(self, entity: str, depth: int = 2) -> Dict:
        """Obtiene subgraph centrado en una entidad."""
        if not self._graph or entity not in self._graph:
            return {"nodes": [], "edges": []}
        
        nodes = {entity}
        edges = []
        
        def expand(node, current_depth):
            if current_depth >= depth:
                return
            for neighbor in self._graph.neighbors(node):
                nodes.add(neighbor)
                edge_data = self._graph.get_edge_data(node, neighbor)
                for data in edge_data.values() if edge_data else [{}]:
                    edges.append({
                        "from": node,
                        "to": neighbor,
                        "relation": data.get("relation", "related_to")
                    })
                expand(neighbor, current_depth + 1)
        
        expand(entity, 0)
        
        return {
            "nodes": list(nodes),
            "edges": edges
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del knowledge graph."""
        return {
            "documents": self._collection.count() if self._collection else 0,
            "graph_nodes": len(self._graph.nodes) if self._graph else 0,
            "graph_edges": len(self._graph.edges) if self._graph else 0,
            "components": {
                "chroma": self._chroma is not None,
                "networkx": self._nx is not None,
                "embedder": self._embedder is not None
            }
        }
    
    def clear(self):
        """Limpia el knowledge graph."""
        if self._collection:
            try:
                self._chroma.delete_collection(self.collection_name)
                self._collection = self._chroma.get_or_create_collection(self.collection_name)
            except:
                pass
        
        if self._node_collection:
            try:
                self._chroma.delete_collection(f"{self.collection_name}_nodes")
                self._node_collection = self._chroma.get_or_create_collection(
                    f"{self.collection_name}_nodes"
                )
            except:
                pass
        
        self.node_embeddings.clear()
        
        if self._graph:
            self._graph.clear()
    
    # ============================================================
    # NODE EMBEDDINGS
    # ============================================================
    
    def _normalize_node_id(self, name: str) -> str:
        """Normaliza ID de nodo."""
        return name.lower().replace(" ", "_").replace(".", "").replace(",", "")
    
    def embed_node(
        self, 
        node_id: str, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> Optional[List[float]]:
        """
        Genera y guarda embedding para un nodo.
        
        Args:
            node_id: Identificador unico del nodo
            content: Contenido para generar embedding
            metadata: Metadata opcional
            
        Returns:
            Embedding vector o None si falla
        """
        if metadata is None:
            metadata = {}
        
        if not self._embedder or not self._node_collection:
            return None
        
        try:
            emb = self._embedder.encode([content], normalize_embeddings=True)[0].tolist()
            
            self.node_embeddings[node_id] = emb
            self._node_collection.add(
                documents=[content],
                embeddings=[emb],
                ids=[node_id],
                metadatas=[metadata]
            )
            
            logger.debug(f"Embedded node: {node_id}")
            return emb
            
        except Exception as e:
            logger.error(f"Failed to embed node {node_id}: {e}")
            return None
    
    def ingest_with_node_embeddings(
        self, 
        texts: List[str], 
        metadatas: List[Dict[str, Any]] = None,
        extract_triples: bool = True
    ) -> List[str]:
        """
        Ingesta completa: text -> triples -> nodes con embeddings.
        
        Args:
            texts: Lista de documentos
            metadatas: Metadata por documento
            extract_triples: Si extraer triples
            
        Returns:
            Lista de IDs de documentos ingeridos
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Base ingestion (vector + graph)
        ids = self.ingest(texts, metadatas, extract_triples=extract_triples)
        
        # Crear nodos con embeddings
        for text, meta in zip(texts, metadatas):
            # Extraer entidades/nodos principales
            entities = self._extract_entities_from_text(text)
            
            for ent in entities:
                node_id = self._normalize_node_id(ent)
                content = ent + ": " + text[:500]
                
                self.embed_node(
                    node_id=node_id,
                    content=content,
                    metadata=meta
                )
                
                # Link al graph si existe
                if self._graph and ent in self._graph:
                    # Anadir embedding al nodo del graph
                    if 'embedding' not in self._graph.nodes[ent]:
                        self._graph.nodes[ent]['embedding'] = self.node_embeddings.get(node_id)
        
        logger.info(f"Ingested {len(ids)} docs with node embeddings")
        return ids
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """
        Extrae entidades de un texto para crear nodos.
        
        Usa el entity extractor o LLM si esta disponible.
        """
        entities = []
        
        # Usar entity extractor
        extracted = self.entity_extractor.extract(text)
        for ent in extracted:
            entities.append(ent["text"])
        
        # Fallback: palabras clave importantes
        if not entities:
            import re
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            entities = list(set(words[:10]))  # Max 10
        
        return entities
    
    def node_similarity_search(
        self, 
        query: str, 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busqueda semantica pura en nodos del grafo.
        
        Args:
            query: Query string
            top_k: Numero de resultados
            
        Returns:
            Lista de nodos similares con scores
        """
        if not self._embedder or not self._node_collection:
            return []
        
        try:
            query_emb = self._embedder.encode([query], normalize_embeddings=True)[0].tolist()
            results = self._node_collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            similar = []
            for i, res_id in enumerate(results.get('ids', [[]])[0] or []):
                doc = results['documents'][0][i] if results.get('documents') else ""
                dist = results['distances'][0][i] if results.get('distances') else 1.0
                meta = results['metadatas'][0][i] if results.get('metadatas') else {}
                
                similar.append({
                    "node": res_id,
                    "content": doc,
                    "score": 1 - min(dist, 1),  # Convert distance to similarity
                    "metadata": meta
                })
            
            return similar
            
        except Exception as e:
            logger.error(f"Node similarity search failed: {e}")
            return []
    
    def enrich_dag_with_node_vectors(
        self, 
        dag: Any, 
        query: str,
        threshold_low: float = 0.65,
        threshold_high: float = 0.75
    ) -> Dict[str, Any]:
        """
        Enrich Cosmos DAG nodes con nearest nodes vectoriales.
        
        Args:
            dag: CosmosDAG a enriquecer
            query: Query para busqueda de nodos similares
            threshold_low: Umbral minimo para agregar contexto
            threshold_high: Umbral para agregar edges semanticos
            
        Returns:
            Dict con informacion del enrichment
        """
        similar_nodes = self.node_similarity_search(query, top_k=8)
        
        if not similar_nodes:
            return {"enriched_nodes": 0, "added_edges": 0}
        
        enriched_count = 0
        added_edges = 0
        
        # Enriquecer nodos del DAG
        if hasattr(dag, 'nodes'):
            for node_id, node in dag.nodes.items():
                # Agregar vector context
                node_context = [
                    n for n in similar_nodes 
                    if n['score'] > threshold_low
                ][:4]
                
                if node_context:
                    if not hasattr(node, 'properties'):
                        node.properties = {}
                    node.properties['vector_context'] = node_context
                    enriched_count += 1
                
                # Agregar edges a nodos similares (alta similitud)
                for sim in similar_nodes:
                    if sim['score'] > threshold_high:
                        if hasattr(dag, 'nodes') and hasattr(dag, 'edges'):
                            edge_exists = any(
                                e.source == node_id and e.target == sim['node']
                                for e in dag.edges
                            )
                            if not edge_exists:
                                from solvens.cosmos.moat_parser import CosmosEdge
                                dag.edges.append(CosmosEdge(
                                    source=node_id,
                                    target=sim['node'],
                                    edge_type="semantic_similarity",
                                    label=f"similar_{sim['score']:.2f}",
                                    properties={"score": sim['score']}
                                ))
                                added_edges += 1
        
        logger.info(f"DAG enriched: {enriched_count} nodes, {added_edges} edges")
        
        return {
            "enriched_nodes": enriched_count,
            "added_edges": added_edges,
            "similar_nodes": len(similar_nodes)
        }
    
    def get_node_clusters(self, min_similarity: float = 0.7) -> List[List[str]]:
        """
        Obtiene clusters de nodos similares.
        
        Usa similarity search para agrupar nodos relacionados.
        
        Args:
            min_similarity: Score minimo para considerar similar
            
        Returns:
            Lista de clusters (listas de node_ids)
        """
        if not self.node_embeddings:
            return []
        
        clusters = []
        processed = set()
        
        for node_id in self.node_embeddings:
            if node_id in processed:
                continue
            
            # Buscar similares
            similar = self.node_similarity_search(node_id, top_k=10)
            
            cluster = [node_id]
            for sim in similar:
                if sim['score'] > min_similarity and sim['node'] not in processed:
                    cluster.append(sim['node'])
                    processed.add(sim['node'])
            
            if len(cluster) > 1:
                clusters.append(cluster)
            
            processed.add(node_id)
        
        return clusters
    
    # ============================================================
    # LOUVAIN CLUSTERING - Community Detection
    # ============================================================
    
    def run_louvain_clustering(
        self, 
        resolution: float = 1.0,
        weight_attr: str = 'weight'
    ) -> Dict[int, List[str]]:
        """
        Aplica Louvain community detection sobre el grafo.
        
        Args:
            resolution: Resolution parameter (higher = more smaller clusters)
            weight_attr: Edge attribute to use as weight
            
        Returns:
            Dict {community_id: [nodes]}
        """
        if not self._graph or len(self._graph.nodes) < 3:
            return {0: list(self._graph.nodes) if self._graph else []}
        
        try:
            import community as community_louvain
            
            # Louvain optimizado para weighted graphs
            partition = community_louvain.best_partition(
                self._graph.to_undirected(), 
                resolution=resolution,
                weight=weight_attr
            )
            
            # Agrupar por comunidad
            from collections import defaultdict
            communities = defaultdict(list)
            for node, comm_id in partition.items():
                communities[comm_id].append(node)
            
            # Agrega metadata al grafo
            for node, comm_id in partition.items():
                if node in self._graph:
                    self._graph.nodes[node]['community'] = comm_id
            
            self.communities = dict(communities)
            logger.info(f"Louvain clustering: {len(self.communities)} communities detected")
            
            return self.communities
            
        except ImportError:
            logger.warning("python-louvain not installed. Run: pip install python-louvain")
            return self._basic_clustering()
        except Exception as e:
            logger.error(f"Louvain clustering failed: {e}")
            return {0: list(self._graph.nodes)}
    
    def _basic_clustering(self) -> Dict[int, List[str]]:
        """
        Clustering basico cuando Louvain no esta disponible.
        
        Usa simple connected components.
        """
        if not self._graph:
            return {}
        
        try:
            import networkx as nx
            components = list(nx.connected_components(self._graph.to_undirected()))
            return {i: list(comp) for i, comp in enumerate(components)}
        except:
            return {0: list(self._graph.nodes)}
    
    def get_community_summary(self) -> List[Dict[str, Any]]:
        """
        Resumen de clusters para decision-making.
        
        Returns:
            Lista de summaries con metadata de cada comunidad
        """
        if not hasattr(self, 'communities') or not self.communities:
            self.run_louvain_clustering()
        
        summaries = []
        
        for cid, nodes in self.communities.items():
            if not nodes:
                continue
                
            summary = {
                "community_id": cid,
                "size": len(nodes),
                "nodes": nodes[:10],  # Top 10
                "density": 0,
                "central_nodes": [],
                "sample_relations": [],
                "keywords": self._extract_cluster_keywords(nodes)
            }
            
            # Subgraph para metricas
            if self._graph and len(nodes) > 1:
                try:
                    subgraph = self._graph.subgraph(nodes)
                    summary["density"] = self._nx.density(subgraph) if self._nx else 0
                    summary["central_nodes"] = self._get_central_nodes(subgraph, 3)
                    summary["sample_relations"] = list(subgraph.edges(data=True))[:5]
                except:
                    pass
            
            summaries.append(summary)
        
        # Ordenar por size
        summaries.sort(key=lambda x: x["size"], reverse=True)
        
        return summaries
    
    def _get_central_nodes(self, subgraph, top_k: int = 3) -> List[Tuple[str, int]]:
        """
        Nodos mas centrales (degree centrality).
        
        Args:
            subgraph: Subgraph a analizar
            top_k: Numero de nodos a retornar
            
        Returns:
            Lista de (node_id, degree) tuples
        """
        try:
            degrees = dict(subgraph.degree())
            return sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:top_k]
        except:
            return []
    
    def _extract_cluster_keywords(self, nodes: List[str]) -> List[str]:
        """
        Extrae keywords de un cluster basandose en los nodos.
        
        Args:
            nodes: Lista de node_ids en el cluster
            
        Returns:
            Lista de keywords
        """
        keywords = []
        
        # Common patterns
        tech_keywords = ['ai', 'ml', 'llm', 'api', 'cloud', 'data', 'tech']
        legal_keywords = ['law', 'court', 'legal', 'act', 'regulation', 'boe']
        market_keywords = ['market', 'sales', 'revenue', 'cost', 'profit', 'growth']
        
        nodes_str = ' '.join(nodes).lower()
        
        for kw in tech_keywords:
            if kw in nodes_str:
                keywords.append(kw)
        
        for kw in legal_keywords:
            if kw in nodes_str:
                keywords.append(kw)
        
        for kw in market_keywords:
            if kw in nodes_str:
                keywords.append(kw)
        
        return list(set(keywords))[:5]
    
    def visualize_communities(
        self, 
        output_path: str = "communities.png",
        figsize: tuple = (12, 8)
    ) -> Optional[str]:
        """
        Visualizacion de comunidades para debug/dashboard.
        
        Args:
            output_path: Path para guardar la imagen
            figsize: Tamano de la figura
            
        Returns:
            Path de la imagen o None si falla
        """
        if not self._graph or len(self._graph.nodes) < 2:
            logger.warning("Not enough nodes to visualize")
            return None
        
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
            
            plt.figure(figsize=figsize)
            
            # Layout
            pos = nx.spring_layout(self._graph, k=2, iterations=50)
            
            # Communities
            partition = nx.get_node_attributes(self._graph, 'community')
            if not partition:
                self.run_louvain_clustering()
                partition = nx.get_node_attributes(self._graph, 'community')
            
            colors = [partition.get(n, 0) for n in self._graph.nodes()]
            
            # Draw
            nx.draw_networkx_nodes(
                self._graph, pos, 
                node_color=colors, 
                cmap=plt.cm.rainbow, 
                node_size=500,
                alpha=0.8
            )
            nx.draw_networkx_edges(
                self._graph, pos, 
                alpha=0.3,
                edge_color='gray'
            )
            nx.draw_networkx_labels(
                self._graph, pos, 
                font_size=6,
                font_weight='bold'
            )
            
            plt.title(f"Solvens Knowledge Graph - {len(self.communities) if hasattr(self, 'communities') else 0} Communities")
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Communities visualized: {output_path}")
            return output_path
            
        except ImportError:
            logger.warning("matplotlib not installed. Run: pip install matplotlib")
            return None
        except Exception as e:
            logger.error(f"Visualization failed: {e}")
            return None
    
    def enrich_dag_with_communities(self, dag: Any) -> Dict[str, Any]:
        """
        Enriquece Cosmos DAG con informacion de comunidades.
        
        Cada nodo del DAG obtiene metadata de su cluster.
        
        Args:
            dag: CosmosDAG a enriquecer
            
        Returns:
            Dict con informacion del enrichment
        """
        if not hasattr(self, 'communities') or not self.communities:
            self.run_louvain_clustering()
        
        enriched = 0
        
        if hasattr(dag, 'nodes'):
            for node_id, node in dag.nodes.items():
                # Encontrar comunidad
                community_id = None
                for cid, nodes in self.communities.items():
                    if node_id in nodes:
                        community_id = cid
                        break
                
                if community_id is not None:
                    if not hasattr(node, 'properties'):
                        node.properties = {}
                    
                    node.properties['community_id'] = community_id
                    node.properties['community_size'] = len(self.communities[community_id])
                    node.properties['cluster_keywords'] = self._extract_cluster_keywords(
                        self.communities[community_id]
                    )
                    enriched += 1
        
        logger.info(f"DAG enriched with {enriched} community assignments")
        
        return {
            "enriched_nodes": enriched,
            "total_communities": len(self.communities) if hasattr(self, 'communities') else 0
        }
    
    def suggest_sub_agents(self) -> List[Dict[str, Any]]:
        """
        Sugiere sub-agents basados en clusters.
        
        Returns:
            Lista de sub-agent suggestions con config
        """
        summaries = self.get_community_summary()
        
        suggestions = []
        
        for summary in summaries:
            # Solo clusters significativos
            if summary['size'] < 3:
                continue
            
            suggestion = {
                "name": f"{summary['keywords'][0] if summary['keywords'] else 'Agent'}_Cluster_{summary['community_id']}",
                "community_id": summary['community_id'],
                "size": summary['size'],
                "keywords": summary['keywords'],
                "nodes": summary['nodes'],
                "specialization": self._infer_specialization(summary),
                "estimated_tasks_per_week": summary['size'] * 10
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _infer_specialization(self, summary: Dict) -> str:
        """
        Infiere especializacion del cluster.
        
        Args:
            summary: Community summary
            
        Returns:
            String de especializacion
        """
        keywords = summary.get('keywords', [])
        
        if 'legal' in keywords or 'court' in keywords or 'boe' in keywords:
            return "Legal Analysis"
        elif 'market' in keywords or 'sales' in keywords:
            return "Market Intelligence"
        elif 'ai' in keywords or 'tech' in keywords:
            return "Technical Research"
        elif 'financial' in keywords or 'revenue' in keywords:
            return "Financial Analysis"
        else:
            return "General Purpose"
    
    # ============================================================
    # LLM-POWERED METHODS (via router)
    # ============================================================
    
    def set_router(self, router):
        """Inyecta router para LLM calls."""
        self.router = router
    
    def _extract_triples_llm(
        self, 
        text: str, 
        max_triples: int = 12
    ) -> List[Tuple[str, str, str]]:
        """
        LLM triple extraction optimizada: few-shot, structured output, fallback.
        
        Features:
        - Few-shot fuerte con ejemplos en espanol
        - Routing inteligente (Grok/Claude primero)
        - Temperature bajo para precision
        - Post-procesamiento robusto
        - Fallback nunca falla
        """
        if not self.router:
            return self._fallback_triples(text)
        
        few_shot = """
Ejemplos:
Texto: "Apple lanzo el iPhone 16 en California."
Triples:
Apple|lanzo|iPhone 16
iPhone 16|lanzado_en|California

Texto: "Solvens Amoris desarrolla Cosmos para agents que facturan."
Triples:
Solvens_Amoris|desarrolla|Cosmos
Cosmos|usado_por|agents
agents|generan|ingresos

Texto: "Microsoft adquirio GitHub en 2018."
Triples:
Microsoft|adquirio|GitHub
GitHub|adquirido_en|2018

Texto: "Google desarrolla productos de IA."
Triples:
Google|desarrolla|productos_ia
IA|es_un|tecnologia
"""
        
        prompt = f"""
{few_shot}

Ahora extrae triples estrictos (subject, predicate, object) del texto siguiente.
Reglas:
- Subject y Object: entidades concretas (personas, empresas, conceptos clave).
- Predicate: verbo o relacion clara y concisa.
- Maximo {max_triples} triples relevantes.
- Ignora ruido, filler y opiniones debiles.
- Responde UNICAMENTE con lineas "subject|predicate|object". Nada mas.

Texto: {text[:6000]}
Triples:
"""
        
        try:
            response = self.router.execute(prompt)
            content = response.get("content", "")
            
            triples = []
            for line in content.strip().split('\n'):
                line = line.strip()
                if '|' in line and not line.startswith('#'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        subj, pred, obj = parts[0], parts[1], ' '.join(parts[2:])
                        if subj and pred and obj:
                            subj = subj.lower().replace(" ", "_")
                            pred = pred.lower().replace(" ", "_")
                            obj = obj.lower().replace(" ", "_")
                            triples.append((subj, pred, obj))
            
            # Dedup
            seen = set()
            unique = []
            for t in triples[:max_triples]:
                if t not in seen:
                    seen.add(t)
                    unique.append(t)
            
            return unique
            
        except Exception as e:
            logger.warning(f"LLM triple extraction failed: {e}")
            return self._fallback_triples(text)
    
    def _fallback_triples(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Simple heuristic fallback para cuando LLM no esta disponible.
        
        Usa patrones simples para extraer relaciones basicas.
        """
        import re
        
        triples = []
        text_lower = text.lower()
        
        # Patterns
        patterns = [
            (r'(\w+)\s+(?:lanzo|lanz\ufffdo|desarrolla|desarroll\ufffd|adquirio|adquir\ufffd|cre\ufffd|creo|compr\ufffd|compro|trabaja)\s+(\w+)', 'relacionado_con'),
            (r'(\w+)\s+(?:es|son|era|eran)\s+(\w+)', 'es_un'),
            (r'(\w+)\s+(?:en|con|para|sobre)\s+(\w+)', 'relacionado_con'),
        ]
        
        for pattern, default_rel in patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    subj, obj = groups[0], groups[1]
                    if len(subj) > 2 and len(obj) > 2:
                        triples.append((subj, default_rel, obj))
        
        # Simple: first and last significant words per sentence
        sentences = text.split('.')
        for sent in sentences[:5]:
            words = re.findall(r'\b\w{4,}\b', sent.lower())
            if len(words) >= 3:
                triples.append((words[0], 'asociado_con', words[-1]))
        
        # Limit
        seen = set()
        unique = []
        for t in triples[:8]:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        
        return unique
    
    def ingest_with_llm(
        self,
        texts: List[str],
        metadatas: List[Dict] = None,
        extract_triples: bool = True
    ) -> int:
        """
        Ingest con LLM-powered triple extraction.
        
        Args:
            texts: Documentos a ingestar
            metadatas: Metadata por documento
            extract_triples: Si usar LLM para triples
            
        Returns:
            Número de documentos ingeridos
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        ingested = 0
        
        for text, meta in zip(texts, metadatas):
            doc_id = meta.get("id", f"doc_{uuid.uuid4().hex[:8]}")
            
            # Vector embedding
            if self._collection and self._embedder:
                try:
                    embedding = self._embedder.encode([text])[0].tolist()
                    self._collection.add(
                        documents=[text],
                        embeddings=[embedding],
                        ids=[doc_id],
                        metadatas=[{**meta, "text_hash": hashlib.md5(text.encode()).hexdigest()}]
                    )
                    ingested += 1
                except Exception as e:
                    logger.error(f"Vector ingestion failed: {e}")
            
            # LLM triples
            if extract_triples and self.router and self._graph:
                triples = self._extract_triples_llm(text)
                for subj, pred, obj in triples:
                    self._graph.add_edge(
                        subj, obj,
                        relation=pred,
                        source=doc_id,
                        extracted_by="llm"
                    )
        
        logger.info(f"LLM ingest complete: {ingested} docs, {len(self._graph.edges) if self._graph else 0} triples")
        return ingested
    
    def enrich_dag_context(self, dag: Any, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Enrich Cosmos DAG con contexto del knowledge graph.
        
        Args:
            dag: CosmosDAG a enriquecer
            query: Query para retrieval
            
        Returns:
            Contexto enriquecido para injection
        """
        results = self.hybrid_retrieve(query, k=k)
        
        context = {
            "retrieved_docs": results,
            "top_entities": [],
            "graph_paths": []
        }
        
        # Extract top entities
        for result in results[:3]:
            if result.entities:
                context["top_entities"].extend(result.entities)
        
        # Get graph paths
        for entity in context["top_entities"][:3]:
            subgraph = self.get_subgraph(entity, depth=1)
            if subgraph["nodes"]:
                context["graph_paths"].append(subgraph)
        
        return context
    
    def self_improve(self, query: str, response: str) -> int:
        """
        Self-improvement: ingesta resultado para futuras queries.
        
        Args:
            query: Query original
            response: Respuesta generada
            
        Returns:
            Número de items ingeridos
        """
        combined = f"Query: {query}\nResponse: {response}"
        
        return self.ingest(
            [combined],
            [{"type": "agent_output", "query_hash": hashlib.md5(query.encode()).hexdigest()}],
            extract_triples=True
        )


# ============================================================
# DEMO
# ============================================================

async def demo():
    """Demo del Hybrid Knowledge Graph."""
    print("=" * 60)
    print("HYBRID KNOWLEDGE GRAPH v0.2 - REFINED")
    print("=" * 60)
    
    kg = HybridKnowledgeGraph()
    
    # Check components
    stats = kg.get_stats()
    print("\n[Components]")
    print(f"  ChromaDB: {'✓' if stats['components']['chroma'] else '✗'}")
    print(f"  NetworkX: {'✓' if stats['components']['networkx'] else '✗'}")
    print(f"  Embedder: {'✓' if stats['components']['embedder'] else '✗'}")
    
    # Ingest sample data
    print("\n[Ingesting documents...]")
    
    docs = [
        {
            "text": "Apple is a technology company based in Cupertino. Apple competes with Microsoft and Google.",
            "meta": {"source": "company_db", "type": "company"}
        },
        {
            "text": "Microsoft acquired GitHub in 2018. Microsoft is based in Redmond.",
            "meta": {"source": "company_db", "type": "company"}
        },
        {
            "text": "Google develops AI products. Google acquired DeepMind. Google is based in Mountain View.",
            "meta": {"source": "company_db", "type": "company"}
        },
    ]
    
    texts = [d["text"] for d in docs]
    metas = [d["meta"] for d in docs]
    
    ingested = kg.ingest(texts, metas)
    print(f"  Ingested: {ingested} documents")
    
    # Stats
    stats = kg.get_stats()
    print(f"  Graph nodes: {stats['graph_nodes']}")
    print(f"  Graph edges: {stats['graph_edges']}")
    
    # Retrieve
    print("\n[Hybrid Retrieval: 'Apple']")
    results = kg.hybrid_retrieve("Apple legal risks", k=5)
    
    for i, result in enumerate(results):
        print(f"\n  Result {i + 1}:")
        print(f"    Content: {result.content[:60]}...")
        print(f"    Score: {result.score:.2f}")
        print(f"    Source: {result.source}")
        if result.entities:
            print(f"    Entities: {result.entities}")
    
    # Subgraph
    print("\n[Subgraph: apple]")
    subgraph = kg.get_subgraph("apple", depth=1)
    print(f"  Nodes: {subgraph['nodes']}")
    print(f"  Edges: {subgraph['edges']}")
    
    print("\n" + "=" * 60)
    print("HYBRID KG READY")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
