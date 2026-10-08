"""
Cross-Domain Ontology Alignment & Reasoning Engine
Executes semantic bridging rules across heterogeneous industrial domains
(MV Video -> E-Commerce Products, DevOps Failures -> Agent Handoffs, Healthcare -> Expert Escalation).
"""

import rdflib
from rdflib import URIRef, Literal, RDF, RDFS
from app import load_graph

BRIDGE_NS = rdflib.Namespace("https://example.org/bridge#")
MV_NS = rdflib.Namespace("https://example.org/mv#")
ECOM_NS = rdflib.Namespace("http://example.org/ontology/ecommerce#")
DEVOPS_NS = rdflib.Namespace("https://example.org/devops#")
AG_NS = rdflib.Namespace("https://example.org/agent#")
HEALTH_NS = rdflib.Namespace("http://example.org/ontology/healthcare#")
PROV_NS = rdflib.Namespace("http://www.w3.org/ns/prov#")


def align_cross_domains():
    """
    Loads heterogeneous domains and executes cross-domain alignment reasoning rules.
    Returns the fused graph and alignment metadata.
    """
    mv_g = load_graph("mv")
    ecom_g = load_graph("ecommerce")
    devops_g = load_graph("devops")
    agent_g = load_graph("agent")
    health_g = load_graph("healthcare")

    fused = rdflib.Graph()
    for g in (mv_g, ecom_g, devops_g, agent_g, health_g):
        for triple in g:
            fused.add(triple)

    inferred_triples = []

    # Rule 1: MV MusicVideo / VideoAsset -> E-Commerce Product Promotion
    # Any VideoAsset in MV is aligned to promote an available E-Commerce Product
    products = list(fused.subjects(RDF.type, ECOM_NS.Product))
    videos = list(fused.subjects(RDF.type, MV_NS.MusicVideo)) + list(fused.subjects(RDF.type, MV_NS.VideoAsset))

    if videos and products:
        for idx, vid in enumerate(videos):
            target_prod = products[idx % len(products)]
            triple = (vid, BRIDGE_NS.promotesProduct, target_prod)
            fused.add(triple)
            inferred_triples.append({
                "rule": "MV_to_ECommerce_PromotionalVideo",
                "subject": str(vid).split("#")[-1],
                "predicate": "bridge:promotesProduct",
                "object": str(target_prod).split("#")[-1],
                "description": "뮤직비디오/영상 에셋을 전자상거래 상품의 프로모션 비디오로 연계"
            })

    # Rule 2: DevOps PipelineRun failure -> Autonomous Agent Remediation Handoff
    autonomous_agents = list(fused.subjects(RDF.type, AG_NS.AutonomousAgent)) or [URIRef("https://example.org/agent#DevOpsRemediationAgent")]
    for run in fused.subjects(RDF.type, DEVOPS_NS.PipelineRun):
        status = fused.value(run, DEVOPS_NS.runStatus)
        if status and str(status).lower() in ("failed", "failure", "error"):
            handoff_task = URIRef(f"{str(run)}_RemediationTask")
            remediation_agent = autonomous_agents[0]
            fused.add((handoff_task, RDF.type, AG_NS.Task))
            fused.add((handoff_task, RDFS.label, Literal("CI/CD 빌드 실패 자동 복구 태스크", lang="ko")))
            fused.add((handoff_task, AG_NS.assignedTo, remediation_agent))
            fused.add((run, BRIDGE_NS.triggersRemediation, handoff_task))

            inferred_triples.append({
                "rule": "DevOps_to_Agent_IncidentHandoff",
                "subject": str(run).split("#")[-1],
                "predicate": "bridge:triggersRemediation",
                "object": str(handoff_task).split("#")[-1],
                "description": "CI/CD 파이프라인 실패 감지 시 자율 에이전트 복구 태스크로 자동 핸드오프"
            })

    # Rule 3: Healthcare Low Confidence Diagnosis -> Expert Clinical Escalation
    for task in fused.subjects(RDF.type, HEALTH_NS.DiagnosticTask):
        report = fused.value(task, HEALTH_NS.generatesReport)
        if report:
            conf = fused.value(report, HEALTH_NS.confidenceScore)
            try:
                conf_val = float(str(conf))
            except (ValueError, TypeError):
                conf_val = 1.0

            if conf_val < 0.90:
                escalation = URIRef(f"{str(task)}_SeniorConsult")
                fused.add((task, BRIDGE_NS.requiresEscalation, escalation))
                inferred_triples.append({
                    "rule": "Healthcare_LowConfidence_Escalation",
                    "subject": str(task).split("#")[-1],
                    "predicate": "bridge:requiresEscalation",
                    "object": str(escalation).split("#")[-1],
                    "description": "진단 신뢰도 임계치 미달 시 전문의 2차 협진 태스크로 연계"
                })

    return {
        "total_fused_triples": len(fused),
        "inferred_count": len(inferred_triples),
        "aligned_domains": ["mv", "ecommerce", "devops", "agent", "healthcare"],
        "inferred_triples": inferred_triples
    }
