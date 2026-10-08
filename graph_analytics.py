"""
Knowledge Graph Analytics, Centrality & Bottleneck Diagnosis Engine
Calculates In/Out-degree centrality, iterative PageRank, and Single Point of Failure (SPOF)
bottlenecks across multi-agent workflow ontology graphs.
Pure Python implementation with zero heavy external dependencies.
"""

from collections import defaultdict
import rdflib
from rdflib import URIRef, RDF, RDFS


def build_network_adjacency(graph):
    """
    Extracts node set and adjacency lists from an rdflib.Graph.
    Ignores purely literal leaf objects for topological graph centrality.
    """
    nodes = set()
    out_edges = defaultdict(set)
    in_edges = defaultdict(set)

    for s, p, o in graph:
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            s_str = str(s)
            o_str = str(o)
            nodes.add(s_str)
            nodes.add(o_str)
            out_edges[s_str].add(o_str)
            in_edges[o_str].add(s_str)
        elif isinstance(s, URIRef):
            nodes.add(str(s))

    return list(nodes), out_edges, in_edges


def compute_pagerank(nodes, out_edges, in_edges, damping=0.85, max_iter=35, tol=1e-5):
    """
    Computes PageRank using iterative power method.
    """
    n = len(nodes)
    if n == 0:
        return {}

    initial_val = 1.0 / n
    ranks = {node: initial_val for node in nodes}

    for _ in range(max_iter):
        new_ranks = {}
        dangling_sum = sum(ranks[node] for node in nodes if len(out_edges[node]) == 0)
        dangling_contrib = damping * (dangling_sum / n)

        diff = 0.0
        for node in nodes:
            rank_sum = 0.0
            for neighbor in in_edges[node]:
                num_out = len(out_edges[neighbor])
                if num_out > 0:
                    rank_sum += ranks[neighbor] / num_out

            new_rank = (1.0 - damping) / n + damping * rank_sum + dangling_contrib
            diff += abs(new_rank - ranks[node])
            new_ranks[node] = new_rank

        ranks = new_ranks
        if diff < tol:
            break

    total = sum(ranks.values()) or 1.0
    return {k: round(v / total, 5) for k, v in ranks.items()}


def analyze_graph_topology(graph, top_k=5):
    """
    Conducts comprehensive topological centrality and bottleneck diagnosis.
    Returns hub rankings, bottleneck scores, health score, and risk warnings.
    """
    nodes, out_edges, in_edges = build_network_adjacency(graph)
    total_nodes = len(nodes)
    total_edges = sum(len(targets) for targets in out_edges.values())

    if total_nodes == 0:
        return {
            "total_nodes": 0,
            "total_edges": 0,
            "density": 0.0,
            "health_score": 100,
            "top_hubs": [],
            "top_bottlenecks": [],
            "warnings": []
        }

    pagerank_scores = compute_pagerank(nodes, out_edges, in_edges)

    node_stats = []
    isolated_nodes = []

    for node in nodes:
        in_deg = len(in_edges[node])
        out_deg = len(out_edges[node])
        total_deg = in_deg + out_deg
        pr = pagerank_scores.get(node, 0.0)

        # Bottleneck index: high transit hub with many incoming & outgoing paths
        bottleneck_index = round((in_deg * 1.5 + out_deg) * (1.0 + pr * 10.0), 3)

        node_ref = URIRef(node)
        lbl = graph.value(node_ref, RDFS.label)
        node_label = str(lbl) if lbl else node.split("#")[-1].split("/")[-1]

        types = [str(t).split("#")[-1] for _, _, t in graph.triples((node_ref, RDF.type, None))]
        type_str = types[0] if types else "Entity"

        if total_deg == 0:
            isolated_nodes.append(node_label)

        node_stats.append({
            "uri": node,
            "label": node_label,
            "type": type_str,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "total_degree": total_deg,
            "pagerank": pr,
            "bottleneck_score": bottleneck_index
        })

    sorted_by_pagerank = sorted(node_stats, key=lambda x: x["pagerank"], reverse=True)[:top_k]
    sorted_by_bottleneck = sorted(node_stats, key=lambda x: x["bottleneck_score"], reverse=True)[:top_k]

    max_possible_edges = total_nodes * (total_nodes - 1)
    density = round(total_edges / max_possible_edges, 4) if max_possible_edges > 0 else 0.0

    warnings = []
    deductions = 0

    if sorted_by_bottleneck and sorted_by_bottleneck[0]["bottleneck_score"] > 25.0:
        top_spof = sorted_by_bottleneck[0]
        warnings.append(f"단일 장애점(SPOF) 위험 노드 감지: '{top_spof['label']}' (의존성 집중도 {top_spof['bottleneck_score']})")
        deductions += 10

    if len(isolated_nodes) > 0:
        warnings.append(f"고립 노드 {len(isolated_nodes)}개 감지: 온톨로지 워크플로우에 연결되지 않은 개체 확인 필요")
        deductions += min(15, len(isolated_nodes) * 5)

    if density < 0.01 and total_nodes > 10:
        warnings.append("그래프 밀도 극저(Density < 0.01): 에이전트 간 협업 관계 연결 확충 권장")
        deductions += 5

    health_score = max(50, 100 - deductions)

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "density": density,
        "health_score": health_score,
        "isolated_nodes_count": len(isolated_nodes),
        "top_hubs": sorted_by_pagerank,
        "top_bottlenecks": sorted_by_bottleneck,
        "warnings": warnings,
        "recommendations": [
            "주요 병목(SPOF) 에이전트에 대체 에이전트 핸드오프 규칙 설정",
            "PageRank 상위 핵심 태스크에 대해 W3C PROV-O 품질 검증 우선 적용",
            "도메인 간 크로스 연계 브릿지를 활용하여 워크플로우 분산 처리"
        ]
    }
