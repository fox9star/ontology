"""
Apache Jena Fuseki Live Sync & SPARQL 1.1 Update Connector
Provides automated synchronization between local RDF graphs and remote Fuseki triplestores.
Handles offline status gracefully without crashing.
"""

import os
import urllib.request
import urllib.error
import urllib.parse
from app import ONTOLOGIES, load_graph
from rdflib import Namespace
from rdflib.namespace import RDF

DEFAULT_FUSEKI_URL = os.environ.get("FUSEKI_ENDPOINT", "http://127.0.0.1:3030/ds")
HEALTH = Namespace("http://example.org/ontology/healthcare#")


def _has_protected_healthcare_data(graph):
    """Recognize patient-linked or clinical text before any remote transfer."""
    if any(graph.triples((None, HEALTH.patientId, None))):
        return True
    if any(graph.triples((None, HEALTH.findingText, None))):
        return True
    for patient in graph.subjects(RDF.type, HEALTH.PatientRecord):
        classifications = set(graph.objects(patient, HEALTH.dataClassification))
        if classifications != {HEALTH.Synthetic}:
            return True
    return False


def get_endpoint_url(endpoint=None):
    return (endpoint or DEFAULT_FUSEKI_URL).rstrip("/")


def check_fuseki_connection(endpoint=None):
    """
    Checks if the Apache Jena Fuseki server is running and reachable.
    Returns (is_connected, message, ping_ms).
    """
    url = f"{get_endpoint_url(endpoint)}/sparql?query=ASK%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D"
    import time
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            return True, f"Fuseki 연결 정상 (응답코드: {resp.status})", round(elapsed, 1)
    except Exception as e:
        return False, f"Fuseki 서버 미가동 또는 연결 불가 ({str(e)})", 0.0


def sync_graph_to_fuseki(graph, graph_name=None, endpoint=None, allow_sensitive_healthcare=False):
    """
    Syncs an rdflib.Graph to Fuseki using the Graph Store HTTP Protocol (GSP).
    PUT /data?graph=<graph_name> replaces the named graph.
    """
    if _has_protected_healthcare_data(graph) and not allow_sensitive_healthcare:
        return {
            "success": False,
            "status_code": 403,
            "triples_synced": 0,
            "graph_name": graph_name or "default",
            "code": "SENSITIVE_HEALTHCARE_TRANSFER_BLOCKED",
            "message": "민감 의료 데이터의 Fuseki 전송은 명시적으로 허용되지 않았습니다.",
        }
    base = get_endpoint_url(endpoint)
    serialized = graph.serialize(format="nt")
    if isinstance(serialized, str):
        data_bytes = serialized.encode("utf-8")
    else:
        data_bytes = serialized

    if graph_name:
        encoded_name = urllib.parse.quote(graph_name, safe="")
        gsp_url = f"{base}/data?graph={encoded_name}"
    else:
        gsp_url = f"{base}/data?default"

    req = urllib.request.Request(
        gsp_url,
        data=data_bytes,
        method="PUT",
        headers={"Content-Type": "application/n-triples"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return {
                "success": True,
                "status_code": resp.status,
                "triples_synced": len(graph),
                "graph_name": graph_name or "default",
                "message": f"성공적으로 {len(graph)}개 트리플이 Fuseki에 동기화되었습니다."
            }
    except Exception as e:
        return {
            "success": False,
            "status_code": getattr(e, "code", 0),
            "triples_synced": 0,
            "graph_name": graph_name or "default",
            "message": f"Fuseki 동기화 실패: {str(e)}"
        }


def sync_domain(domain_key, project_id=None, endpoint=None, allow_sensitive_healthcare=False):
    """
    Loads and synchronizes a specific domain's graph to Fuseki.
    """
    if domain_key not in ONTOLOGIES:
        raise ValueError(f"알 수 없는 도메인: {domain_key}")

    cfg = ONTOLOGIES[domain_key]
    g = load_graph(domain_key, project_id)
    graph_uri = f"{cfg['prefix']}graph"
    return sync_graph_to_fuseki(
        g, graph_name=graph_uri, endpoint=endpoint,
        allow_sensitive_healthcare=allow_sensitive_healthcare,
    )


def sync_all_domains(endpoint=None, allow_sensitive_healthcare=False):
    """
    Synchronizes all 7 domains to Fuseki triplestore.
    """
    results = []
    connected, msg, _ = check_fuseki_connection(endpoint)
    if not connected:
        return {
            "connected": False,
            "message": msg,
            "domains": []
        }

    for dom in ONTOLOGIES:
        res = sync_domain(dom, endpoint=endpoint, allow_sensitive_healthcare=allow_sensitive_healthcare)
        results.append({"domain": dom, **res})

    total_synced = sum(r.get("triples_synced", 0) for r in results if r.get("success"))
    return {
        "connected": True,
        "total_domains": len(results),
        "total_triples_synced": total_synced,
        "domains": results
    }
