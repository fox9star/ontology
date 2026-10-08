"""
causal_engine.py - 인과 추론 그래프(Causal Knowledge Graph) 및 반사실(What-If) 시뮬레이션 엔진
- Pearl의 인과 모델(Structural Causal Model, SCM)을 온톨로지 지식 그래프와 결합
- 개입(Intervention, Do-Calculus) 기반 연쇄 효과 및 반사실(Counterfactual) 결과 예측
"""

import math
from typing import Dict, List, Any, Optional, Tuple
import rdflib
from rdflib import Namespace, RDF, RDFS, Literal, URIRef

CAUSAL = Namespace("http://example.org/ontology/causal#")
MV = Namespace("http://example.org/ontology/mv#")


class CausalNode:
    def __init__(self, name: str, node_type: str = "variable", default_val: float = 0.5):
        self.name = name
        self.node_type = node_type
        self.default_val = default_val
        self.parents: List[Tuple['CausalNode', float, str]] = []  # (parent_node, weight, relation_type)
        self.children: List[Tuple['CausalNode', float, str]] = []

    def add_child(self, child: 'CausalNode', weight: float = 1.0, relation: str = "causes"):
        self.children.append((child, weight, relation))
        child.parents.append((self, weight, relation))


class CausalKnowledgeGraph:
    """온톨로지 그래프로부터 인과 DAG(Directed Acyclic Graph)를 구축하고 개입 효과를 계산합니다."""

    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self._build_default_causal_network()

    def _build_default_causal_network(self):
        """음악-영상 및 일반 AI 시스템의 인과 관계 네트워크 기본 토폴로지 구축"""
        # MV 도메인 인과 노드 생성
        bpm = self.get_or_create_node("BGM_Tempo_BPM", default_val=128.0)
        energy = self.get_or_create_node("Audio_Energy_Level", default_val=0.85)
        cut_freq = self.get_or_create_node("Shot_Cut_Frequency", default_val=1.2)  # 초당 컷 수
        color_sat = self.get_or_create_node("Color_Saturation", default_val=0.7)
        retention = self.get_or_create_node("Audience_Engagement_Score", default_val=0.82)
        cognitive_load = self.get_or_create_node("Viewer_Visual_Fatigue", default_val=0.25)
        motion_intensity = self.get_or_create_node("Camera_Motion_Speed", default_val=0.6)

        # 인과 엣지 연결 (원인 -> 결과, 가중치, 관계 유형)
        bpm.add_child(energy, weight=0.85, relation="causes")
        energy.add_child(cut_freq, weight=0.75, relation="drives")
        cut_freq.add_child(retention, weight=0.65, relation="enhances")
        cut_freq.add_child(cognitive_load, weight=0.55, relation="increases")
        motion_intensity.add_child(cognitive_load, weight=0.45, relation="amplifies")
        color_sat.add_child(retention, weight=0.35, relation="mediates")
        cognitive_load.add_child(retention, weight=-0.60, relation="degrades")

    def get_or_create_node(self, name: str, default_val: float = 0.5) -> CausalNode:
        if name not in self.nodes:
            self.nodes[name] = CausalNode(name, default_val=default_val)
        return self.nodes[name]

    def load_from_rdf(self, g: rdflib.Graph):
        """RDF 온톨로지에서 causal:causes, causal:effectSize 트리플을 파싱하여 인과 그래프 확장"""
        query = """
        PREFIX causal: <http://example.org/ontology/causal#>
        SELECT ?cause ?effect ?weight ?rel WHERE {
            ?cause ?rel ?effect .
            OPTIONAL { ?rel causal:effectSize ?weight }
            FILTER(?rel IN (causal:causes, causal:prevents, causal:amplifies, causal:mediates))
        }
        """
        try:
            for row in g.query(query):
                c_name = str(row["cause"]).split("#")[-1]
                e_name = str(row["effect"]).split("#")[-1]
                w = float(row["weight"]) if row.get("weight") else 0.7
                rel = str(row["rel"]).split("#")[-1]
                c_node = self.get_or_create_node(c_name)
                e_node = self.get_or_create_node(e_name)
                c_node.add_child(e_node, weight=w, relation=rel)
        except Exception:
            pass

    def simulate_what_if(self, interventions: Dict[str, float]) -> Dict[str, Any]:
        """Pearl의 Do-Calculus (do(X = x)) 시뮬레이션:
        특정 원인 변수를 강제 변경했을 때, 다운스트림 인과 네트워크 전체에 전파되는 반사실적 변화 계산
        """
        # 현재 상태 복제
        current_state = {name: node.default_val for name, node in self.nodes.items()}
        counterfactual_state = dict(current_state)

        # 개입(Intervention) 적용 (부모와의 인과 연결 절단 후 고정값 주입)
        applied_interventions = {}
        for target, val in interventions.items():
            if target in counterfactual_state:
                counterfactual_state[target] = float(val)
                applied_interventions[target] = {
                    "original": current_state[target],
                    "intervened": float(val),
                    "delta": float(val) - current_state[target]
                }

        # 전방향 인과 전파 (Forward Causal Propagation)
        propagation_paths = []
        for target, change_info in applied_interventions.items():
            delta = change_info["delta"]
            target_node = self.nodes[target]

            # BFS 전파
            queue = [(target_node, delta, 1.0, [target])]
            visited = set()
            while queue:
                curr_node, incoming_delta, damping, path = queue.pop(0)
                for child, weight, rel in curr_node.children:
                    if child.name in interventions:
                        continue  # 개입된 변수는 고정됨 (Do-operator)

                    impact = incoming_delta * weight * damping
                    counterfactual_state[child.name] += impact
                    # 값 범위 클리핑
                    if "BPM" not in child.name and "Frequency" not in child.name:
                        counterfactual_state[child.name] = max(0.0, min(1.0, counterfactual_state[child.name]))

                    new_path = path + [f"--({rel}: {weight})--> {child.name}"]
                    propagation_paths.append({
                        "source": target,
                        "target": child.name,
                        "causal_chain": " -> ".join(new_path),
                        "effect_size": round(impact, 4)
                    })

                    if child.name not in visited:
                        visited.add(child.name)
                        queue.append((child, impact, damping * 0.8, path + [child.name]))

        # 리스크 및 이상 징후 자동 진단
        diagnostics = []
        fatigue = counterfactual_state.get("Viewer_Visual_Fatigue", 0.0)
        engagement = counterfactual_state.get("Audience_Engagement_Score", 0.0)

        if fatigue > 0.7:
            diagnostics.append("[CRITICAL RISK] 과도한 컷 전환/카메라 모션으로 시각 피로도가 임계치(0.70)를 초과했습니다.")
        if engagement < 0.5:
            diagnostics.append("[PERFORMANCE WARNING] 변경된 연출 조합으로 인해 예상 몰입도가 저하(0.50 미만)됩니다.")
        if engagement >= 0.85 and fatigue <= 0.4:
            diagnostics.append("[OPTIMAL SYNERGY] 높은 관객 몰입도와 쾌적한 피로도 수준이 성공적으로 양립되었습니다.")

        return {
            "status": "success",
            "applied_interventions": applied_interventions,
            "baseline_state": current_state,
            "counterfactual_state": counterfactual_state,
            "causal_propagation_paths": propagation_paths,
            "diagnostics": diagnostics
        }
