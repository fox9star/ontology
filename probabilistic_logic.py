"""
probabilistic_logic.py - 확률적 소프트 로직 (Probabilistic Soft Logic, PSL) 추론기
- 0과 1의 이분법을 극복하는 연속 진리값 [0.0, 1.0] 기반 루카시에비치(Lukasiewicz) t-norm 연산
- 노이즈와 불확실성이 존재하는 실세계 도메인 사실 관계에 대한 신뢰도 기반 확률적 추론
"""

from typing import Dict, List, Any, Tuple, Optional


class ProbabilisticRule:
    def __init__(self, antecedent_keys: List[str], consequent_key: str, weight: float = 1.0, name: str = ""):
        self.antecedent_keys = antecedent_keys
        self.consequent_key = consequent_key
        self.weight = weight
        self.name = name or f"Rule_{consequent_key}"

    def evaluate_satisfaction(self, facts: Dict[str, float]) -> Tuple[float, float]:
        """루카시에비치 t-norm을 적용하여 규칙 충족도 및 위반 거리(Distance to Satisfaction) 산출
        Lukasiewicz AND: max(0, sum(values) - (n - 1))
        Lukasiewicz Implication: min(1, 1 - Antecedent + Consequent)
        Distance: max(0, Antecedent - Consequent)
        """
        # 전제부(Antecedent) 진리값 계산 (Lukasiewicz AND)
        ant_vals = [facts.get(k, 0.5) for k in self.antecedent_keys]
        if not ant_vals:
            ant_val = 1.0
        elif len(ant_vals) == 1:
            ant_val = ant_vals[0]
        else:
            ant_val = max(0.0, sum(ant_vals) - (len(ant_vals) - 1.0))

        # 결론부(Consequent) 진리값
        cons_val = facts.get(self.consequent_key, 0.5)

        # 위반 거리 d = max(0, A - C)
        distance = max(0.0, ant_val - cons_val)
        satisfaction = 1.0 - distance
        return satisfaction, distance


class ProbabilisticLogicEngine:
    """불확실성이 포함된 온톨로지 사실들로부터 가장 신뢰도 높은 결론을 도출하는 소프트 로직 엔진"""

    def __init__(self):
        self.rules: List[ProbabilisticRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """도메인 지식 규칙 등록 (전제 조건들 -> 결과, 가중치)"""
        # 1. 고에너지 음원 + 빠른 컷 -> 시청자 몰입도 높음 (가중치 0.90)
        self.rules.append(ProbabilisticRule(["HighAudioEnergy", "FastCutCadence"], "HighEngagement", weight=0.90, name="R1_Engagement"))
        # 2. 어두운 야경 + 과도한 카메라 흔들림 -> 시각 피로도 높음 (가중치 0.85)
        self.rules.append(ProbabilisticRule(["DarkLighting", "ExcessiveCameraShake"], "HighVisualFatigue", weight=0.85, name="R2_VisualFatigue"))
        # 3. 비트싱크 일치 + 틸앤오렌지 LUT -> 프로페셔널 퀄리티 (가중치 0.95)
        self.rules.append(ProbabilisticRule(["AccurateBeatSync", "TealOrangeGrading"], "ProfessionalGrade", weight=0.95, name="R3_ProQuality"))
        # 4. 시각 피로도가 높으면 몰입도 저하 (가중치 0.80)
        self.rules.append(ProbabilisticRule(["HighVisualFatigue"], "LowRetentionRisk", weight=0.80, name="R4_FatigueRisk"))

    def infer(self, observed_facts: Dict[str, float], iterations: int = 10) -> Dict[str, Any]:
        """관측된 확률적 사실(0.0 ~ 1.0)로부터 완화 반복 최적화를 통해 목표 진리값 수렴 추론"""
        current_state = dict(observed_facts)

        # 미관측 목표 변수 초기화
        target_keys = {r.consequent_key for r in self.rules if r.consequent_key not in current_state}
        for k in target_keys:
            current_state[k] = 0.5  # 무정보 사전확률

        rule_evaluations = []

        # 고정점 반복 최적화 (Fixed-Point Relaxation)
        for _ in range(iterations):
            for rule in self.rules:
                if rule.consequent_key in observed_facts:
                    continue  # 고정된 관측값은 업데이트하지 않음

                # 전제부 진리값
                ant_vals = [current_state.get(k, 0.5) for k in rule.antecedent_keys]
                if not ant_vals:
                    ant_val = 1.0
                elif len(ant_vals) == 1:
                    ant_val = ant_vals[0]
                else:
                    ant_val = max(0.0, sum(ant_vals) - (len(ant_vals) - 1.0))

                # 소프트 로직 그래디언트 업데이트
                current_val = current_state[rule.consequent_key]
                target_val = ant_val
                # 가중치에 따른 점진적 수렴
                current_state[rule.consequent_key] = current_val + 0.3 * rule.weight * (target_val - current_val)
                current_state[rule.consequent_key] = max(0.0, min(1.0, current_state[rule.consequent_key]))

        # 최종 규칙 충족도 점검
        for rule in self.rules:
            sat, dist = rule.evaluate_satisfaction(current_state)
            rule_evaluations.append({
                "rule": rule.name,
                "antecedents": rule.antecedent_keys,
                "consequent": rule.consequent_key,
                "satisfaction_score": round(sat, 4),
                "weighted_confidence": round(sat * rule.weight, 4)
            })

        # 최종 신뢰도 요약
        inferred_targets = {k: round(current_state[k], 4) for k in target_keys}

        return {
            "status": "success",
            "observed_inputs": observed_facts,
            "inferred_truth_values": inferred_targets,
            "overall_state": {k: round(v, 4) for k, v in current_state.items()},
            "rule_satisfactions": rule_evaluations
        }
