"""
quantum_cognitive.py - 양자 인지 중첩 그래프 (Quantum-Cognitive Superposition Graph)
- 힐베르트 공간(Hilbert Space)의 복소수 케트 벡터 |ψ⟩를 통한 다의적 지식 중첩(Superposition) 모델링
- 질문 맥락(Observer Context)에 의한 파동함수 붕괴(State Collapse) 및 양자 간섭(Interference) 효과 추론
"""

import math
import cmath
from typing import Dict, List, Any, Tuple, Optional


class QuantumBasisState:
    def __init__(self, label: str, amplitude: complex):
        self.label = label
        self.amplitude = amplitude

    @property
    def probability(self) -> float:
        return abs(self.amplitude) ** 2


class QuantumSemanticNode:
    """복수의 상반된 의미론적 해석이 중첩되어 공존하는 양자 개념 노드"""

    def __init__(self, name: str, states: Dict[str, complex]):
        self.name = name
        self.basis_states: List[QuantumBasisState] = []
        self._normalize_and_set(states)

    def _normalize_and_set(self, states: Dict[str, complex]):
        total_sq = sum(abs(amp) ** 2 for amp in states.values())
        norm_factor = math.sqrt(total_sq) if total_sq > 0 else 1.0
        self.basis_states = [
            QuantumBasisState(label, amp / norm_factor)
            for label, amp in states.items()
        ]

    def get_superposition_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "state": s.label,
                "amplitude_real": round(s.amplitude.real, 4),
                "amplitude_imag": round(s.amplitude.imag, 4),
                "probability_percent": round(s.probability * 100, 2)
            }
            for s in self.basis_states
        ]

    def measure_collapse(self, observer_context: str) -> Dict[str, Any]:
        """관측자 맥락(Observer Context)과의 내적(Inner Product) 연산을 통해 단일 고유 상태로 붕괴"""
        # 한-영 감성 키워드 사전 매핑
        semantic_lexicon = {
            "MelancholicSadness": ["슬픔", "슬픈", "이별", "비극", "sad", "sadness", "melancholy", "grief"],
            "CyberpunkMystery": ["사이버펑크", "추격", "화려한", "네온", "cyberpunk", "mystery", "neon", "action"],
            "AdrenalineAction": ["액션", "아드레날린", "폭발", "action", "adrenaline", "speed"],
            "ChaosAndPanic": ["혼돈", "패닉", "공포", "chaos", "panic", "fear"]
        }

        weights = {}
        ctx_lower = observer_context.lower()
        for s in self.basis_states:
            w = 1.0
            # 라벨 텍스트 매칭
            for term in s.label.lower().split():
                if term in ctx_lower:
                    w += 2.0
            # 동의어 사전 매칭
            for keyword in semantic_lexicon.get(s.label, []):
                if keyword in ctx_lower:
                    w += 3.0
            weights[s.label] = w

        # 가중 투영된 양자 확률 재계산
        weighted_probs = {
            s.label: s.probability * weights[s.label]
            for s in self.basis_states
        }
        total_w = sum(weighted_probs.values())
        collapsed_label = max(weighted_probs, key=weighted_probs.get)
        collapsed_prob = weighted_probs[collapsed_label] / total_w if total_w > 0 else 1.0

        # 양자 위상 간섭(Quantum Interference) 지표 산출
        interference_term = round(math.sin(sum(cmath.phase(s.amplitude) for s in self.basis_states)), 4)

        return {
            "collapsed_eigenstate": collapsed_label,
            "collapse_probability": round(collapsed_prob, 4),
            "quantum_phase_interference": interference_term,
            "interpretation": (
                f"관측 맥락('{observer_context}')과의 상호작용으로 파동함수가 붕괴하여, "
                f"{collapsed_prob*100:.1f}%의 확률 밀도로 '{collapsed_label}' 고유 상태가 확정되었습니다."
            )
        }


class QuantumCognitiveEngine:
    """양자 인지 중첩 노드들을 관리하고 문맥별 붕괴를 실행하는 엔진"""

    def __init__(self):
        self.nodes: Dict[str, QuantumSemanticNode] = {}
        self._initialize_default_quantum_nodes()

    def _initialize_default_quantum_nodes(self):
        """다의성을 가진 온톨로지 개념의 중첩 상태 초기화"""
        # 1. NeonMoodyDark: 고독한 슬픔 (0.6) + 사이버펑크 신비 (0.8)
        self.nodes["NeonMoodyDark"] = QuantumSemanticNode("NeonMoodyDark", {
            "MelancholicSadness": complex(0.6, 0.0),
            "CyberpunkMystery": complex(0.8, 0.0)
        })

        # 2. FastCutMontage: 아드레날린 액션 (0.707) + 혼돈과 패닉 (0.707)
        self.nodes["FastCutMontage"] = QuantumSemanticNode("FastCutMontage", {
            "AdrenalineAction": complex(0.707, 0.1),
            "ChaosAndPanic": complex(0.707, -0.1)
        })

    def get_node_superposition(self, node_name: str) -> Optional[List[Dict[str, Any]]]:
        node = self.nodes.get(node_name)
        return node.get_superposition_summary() if node else None

    def observe_and_collapse(self, node_name: str, context: str) -> Dict[str, Any]:
        node = self.nodes.get(node_name)
        if not node:
            return {"error": f"존재하지 않는 양자 개념 노드: {node_name}"}

        pre_state = node.get_superposition_summary()
        collapse_res = node.measure_collapse(context)

        return {
            "node_name": node_name,
            "pre_measurement_superposition": pre_state,
            "post_measurement_collapse": collapse_res
        }
