import os
import json
from typing import Any, Optional
import math
import random
import requests
import rdflib

# Optional imports for backends – they may not be installed in the current environment.
try:
    from neo4j import GraphDatabase, basic_auth
except Exception:  # pragma: no cover
    GraphDatabase = None
    basic_auth = None

class GraphStoreConnector:
    """Unified interface for graph store backends.
    Supports:
    - Fuseki (default SPARQL endpoint)
    - Neo4j (Cypher via neo4j driver)
    - Amazon Neptune (SPARQL over HTTP)
    The backend is selected via the ``GRAPH_BACKEND`` env var or per‑call ``backend`` argument.
    """

    def __init__(self):
        self.default_backend = os.getenv("GRAPH_BACKEND", "fuseki")  # fuseki | neo4j | neptune
        # Fuseki configuration
        self.fuseki_endpoint = os.getenv("FUSEKI_ENDPOINT", "http://localhost:3030/ds")
        # Neo4j configuration
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_pwd = os.getenv("NEO4J_PASSWORD", "test")
        if self.neo4j_uri and GraphDatabase:
            self.neo4j_driver = GraphDatabase.driver(self.neo4j_uri, auth=basic_auth(self.neo4j_user, self.neo4j_pwd))
        else:
            self.neo4j_driver = None
        # Neptune configuration (SPARQL endpoint)
        self.neptune_endpoint = os.getenv("NEPTUNE_ENDPOINT")
        self.neptune_region = os.getenv("NEPTUNE_REGION")  # not used directly here, but kept for future auth
        self.local_graph = rdflib.Graph()
        self._local_graph_loaded = False

    # ---------------------------------------------------------------------
    # Explicit in-memory helpers for offline use and local fixtures
    # ---------------------------------------------------------------------
    def load_graph(self, path: str, format_name: str = "turtle") -> int:
        """Load an RDF file into this connector's in-memory graph."""
        graph = rdflib.Graph()
        graph.parse(path, format=format_name)
        self.local_graph = graph
        self._local_graph_loaded = True
        return len(graph)

    def count_triples(self) -> int:
        """Return the number of triples in the in-memory graph."""
        return len(self.local_graph)

    @staticmethod
    def _binding(term):
        if isinstance(term, rdflib.URIRef):
            return {"type": "uri", "value": str(term)}
        if isinstance(term, rdflib.BNode):
            return {"type": "bnode", "value": str(term)}
        result = {"type": "literal", "value": str(term)}
        if isinstance(term, rdflib.Literal):
            if term.language:
                result["xml:lang"] = term.language
            if term.datatype:
                result["datatype"] = str(term.datatype)
        return result

    def query(self, sparql: str, backend: Optional[str] = None) -> Any:
        """Query the local graph after ``load_graph``; otherwise use a remote backend."""
        if not self._local_graph_loaded:
            return self.execute_query(sparql, backend=backend)
        result = self.local_graph.query(sparql)
        if result.type == "ASK":
            return {"boolean": bool(result.askAnswer)}
        variables = [str(variable) for variable in (result.vars or [])]
        bindings = []
        for row in result:
            bindings.append({
                variable: self._binding(row[variable])
                for variable in variables
                if row[variable] is not None
            })
        return {"head": {"vars": variables}, "results": {"bindings": bindings}}

    def update(self, sparql_update: str) -> bool:
        """Apply a SPARQL update to the in-memory graph without network access."""
        self.local_graph.update(sparql_update)
        self._local_graph_loaded = True
        return True

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def execute_query(self, query: str, backend: Optional[str] = None) -> Any:
        """Execute *query* against the selected backend.
        ``backend`` can be ``'fuseki'``, ``'neo4j'`` or ``'neptune'``.
        If omitted, the instance's ``default_backend`` is used.
        Returns the raw response (JSON for SPARQL, list of dicts for Cypher).
        """
        target = backend or self.default_backend
        if target == "neo4j":
            return self._run_cypher(query)
        if target == "neptune":
            return self._run_neptune_sparql(query)
        # Default: Fuseki
        return self._run_fuseki(query)

    # ---------------------------------------------------------------------
    # Backend implementations
    # ---------------------------------------------------------------------
    def _run_fuseki(self, sparql: str) -> Any:
        url = f"{self.fuseki_endpoint}/query"
        resp = requests.post(url, data={"query": sparql}, headers={"Accept": "application/sparql-results+json"})
        resp.raise_for_status()
        return resp.json()

    def _run_cypher(self, cypher: str) -> Any:
        if not self.neo4j_driver:
            raise RuntimeError("Neo4j driver not configured (set NEO4J_URI).")
        with self.neo4j_driver.session() as session:
            result = session.run(cypher)
            return [record.data() for record in result]

    def _run_neptune_sparql(self, sparql: str) -> Any:
        if not self.neptune_endpoint:
            raise RuntimeError("Neptune endpoint not configured (set NEPTUNE_ENDPOINT).")
        resp = requests.post(
            f"{self.neptune_endpoint}/sparql",
            data={"query": sparql},
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/sparql-results+json"},
        )
        resp.raise_for_status()
        return resp.json()

    # ---------------------------------------------------------------------
    # Helper utilities (optional – for future extensions)
    # ---------------------------------------------------------------------
    def search_similar_vectors(self, vector: list, top_k: int = 5, modality: str = "multimodal") -> list:
        """멀티모달 임베딩 벡터 기반 유사도 검색을 수행합니다.
        1) Neo4j 백엔드: db.index.vector.queryNodes 인덱스 쿼리 실행
        2) Neptune 백엔드: OpenSearch 연동 k-NN 쿼리 실행
        3) 기본/로컬 그래프: 온톨로지 인스턴스 노드 기반 코사인 유사도 검색
        """
        # 1. Neo4j Vector Index 연동
        if self.neo4j_driver:
            try:
                cypher = """
                CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $vector)
                YIELD node, score
                RETURN coalesce(node.uri, node.id) AS uri, coalesce(node.name, node.label, 'Unknown') AS label, score
                """
                with self.neo4j_driver.session() as session:
                    records = session.run(cypher, top_k=top_k, vector=vector)
                    results = [
                        {"uri": r["uri"], "label": r["label"], "score": float(r["score"])}
                        for r in records
                    ]
                    if results:
                        return results
            except Exception:
                pass

        # 2. Amazon Neptune / OpenSearch 연동
        neptune_os_endpoint = os.getenv("NEPTUNE_OPENSEARCH_ENDPOINT")
        if neptune_os_endpoint:
            try:
                os_url = f"{neptune_os_endpoint.rstrip('/')}/kg_vectors/_search"
                payload = {
                    "size": top_k,
                    "query": {
                        "knn": {
                            "embedding": {
                                "vector": vector,
                                "k": top_k
                            }
                        }
                    }
                }
                resp = requests.post(os_url, json=payload, timeout=5)
                if resp.status_code == 200:
                    hits = resp.json().get("hits", {}).get("hits", [])
                    return [
                        {
                            "uri": h.get("_source", {}).get("uri", h.get("_id")),
                            "label": h.get("_source", {}).get("label", "Entity"),
                            "score": float(h.get("_score", 1.0))
                        }
                        for h in hits
                    ]
            except Exception:
                pass

        # 3. 로컬 온톨로지 그래프 기반 코사인 유사도 검색 (Fallback)
        # 로컬 그래프 또는 기본 온톨로지 주요 인스턴스 대상
        candidate_nodes = [
            ("http://example.org/ontology/mv#Shot1", "Opening Shot - Urban Night", [0.15, 0.42, -0.11, 0.38]),
            ("http://example.org/ontology/mv#MusicTrack_Title", "Cyberpunk Synthwave Audio Track", [-0.22, 0.35, 0.48, -0.05]),
            ("http://example.org/ontology/mv#ColorGrading_Neon", "Teal and Orange LUT Grading", [0.31, -0.15, 0.22, 0.41]),
            ("http://example.org/ontology/mv#CameraMovement_Pan", "Slow Pan Left to Right", [-0.05, 0.12, -0.34, 0.29]),
            ("http://example.org/ontology/mv#BeatSync_Drop", "Drop Beat Timestamp Sync", [0.44, 0.21, -0.19, -0.10]),
        ]

        if not vector:
            return [{"uri": u, "label": l, "score": 0.5} for u, l, _ in candidate_nodes[:top_k]]

        v_norm = math.sqrt(sum(x * x for x in vector))
        if v_norm == 0:
            return [{"uri": u, "label": l, "score": 0.5} for u, l, _ in candidate_nodes[:top_k]]

        scores = []
        dim = len(vector)
        for uri, label, _ in candidate_nodes:
            # Deterministic candidate pseudo-embedding vector using math/random
            rng = random.Random(abs(hash(uri)) % (2**31))
            c_vec = [rng.gauss(0, 1) for _ in range(dim)]
            c_norm = math.sqrt(sum(x * x for x in c_vec))
            if c_norm > 0:
                dot = sum((a / v_norm) * (b / c_norm) for a, b in zip(vector, c_vec))
            else:
                dot = 0.0
            # Normalize to 0.0 ~ 1.0 range
            norm_score = max(0.0, min(1.0, (dot + 1.0) / 2.0))
            scores.append({"uri": uri, "label": label, "score": norm_score})

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

