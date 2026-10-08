"""
aesthetic_tension.py - 인간 감성 및 미학적 텐션(Neuro-Aesthetic Tension) 온톨로지 엔진
- 러셀의 감정 원환 모형(Russell's Circumplex Model: Valence-Arousal)과 미학 텐션 시계열 모델링
- 타임라인 기반 시청각 텐션 곡선(Audiovisual Tension Curve) 계산 및 카타르시스(Climax) 정량 분석
"""

import math
from typing import Dict, List, Any, Optional, Tuple


class AestheticTensionEngine:
    """영상-음원 간의 감성 전이와 극적 긴장도를 수학적으로 시뮬레이션하는 엔진"""

    def __init__(self):
        # 감정 좌표계 (Valence: 쾌/불쾌 [-1, 1], Arousal: 각성도 [0, 1])
        self.emotion_presets = {
            "NeonMoodyDark": {"valence": -0.2, "arousal": 0.45, "label": "신비롭고 몽환적인 야경"},
            "TealAndOrangeLUT": {"valence": 0.5, "arousal": 0.70, "label": "세련되고 강렬한 시네마틱"},
            "CyberpunkHighContrast": {"valence": 0.3, "arousal": 0.95, "label": "폭발적 아드레날린"},
            "MonochromeLUT": {"valence": -0.6, "arousal": 0.30, "label": "고독하고 냉소적인 무드"},
        }

    def compute_tension_curve(
        self,
        duration_sec: float = 20.0,
        bpm: float = 128.0,
        drop_timestamp: float = 8.0,
        shot_cuts: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """0초부터 duration_sec까지의 실시간 시청각 텐션 곡선 T(t) 계산"""
        if shot_cuts is None:
            shot_cuts = [0.0, 4.0, 8.0, 11.0, 13.5, 15.0, 16.5, 18.0]

        step = 0.5
        time_points = []
        t = 0.0

        while t <= duration_sec:
            # 1. 음악 템포 및 드롭 비트 기여분 (BPM & Drop Beat Proximity)
            tempo_factor = min(1.0, bpm / 160.0)
            if t < drop_timestamp:
                # 빌드업 구간: 지수 함수형 긴장감 고조
                dist_to_drop = max(0.0, drop_timestamp - t)
                audio_tension = 0.3 + 0.5 * math.exp(-dist_to_drop / 3.0)
            else:
                # 드롭 폭발 후 점진적 안정화
                elapsed_after_drop = t - drop_timestamp
                audio_tension = 0.95 * math.exp(-elapsed_after_drop / 6.0)

            # 2. 샷 컷 빈도 기여분 (Cut Frequency Factor)
            # 최근 2초 이내의 컷 수 계산
            cuts_near = sum(1 for c in shot_cuts if max(0.0, t - 2.0) <= c <= t)
            cut_tension = min(1.0, cuts_near * 0.35)

            # 3. 종합 미학 텐션 점수 합성 (0.0 ~ 1.0)
            composite_tension = max(0.0, min(1.0, (0.55 * audio_tension) + (0.45 * cut_tension)))

            # 감정 상태 매핑
            if composite_tension >= 0.8:
                mood = "HIGH_VOLTAGE_CLIMAX"
            elif composite_tension >= 0.5:
                mood = "DYNAMIC_ENGAGEMENT"
            else:
                mood = "CONTEMPLATIVE_BUILDUP"

            time_points.append({
                "time": round(t, 2),
                "tension": round(composite_tension, 3),
                "audio_component": round(audio_tension, 3),
                "cut_component": round(cut_tension, 3),
                "mood_state": mood
            })
            t += step

        # 클라이맥스 피크 및 카타르시스 지표 검출
        peak_point = max(time_points, key=lambda x: x["tension"])
        catharsis_score = round(peak_point["tension"] * (bpm / 120.0), 3)

        # AI 연출 디렉팅 제언 도출
        recommendations = []
        if peak_point["time"] != drop_timestamp:
            diff = abs(peak_point["time"] - drop_timestamp)
            if diff > 1.0:
                recommendations.append(
                    f"긴장감 최고조 시점({peak_point['time']}s)과 음악 드롭 비트({drop_timestamp}s) 간에 {diff:.1f}초 편차가 존재합니다. "
                    "컷 전환 타이밍을 전진 배치하여 싱크를 일치시키십시오."
                )
        if catharsis_score >= 1.0:
            recommendations.append("클라이맥스 카타르시스 지수가 극대화되어 시청자 도파민 분비 조건에 최적화되었습니다.")
        else:
            recommendations.append("드롭 구간의 카메라 무브먼트 가속을 15% 추가하여 긴장감 증폭을 권장합니다.")

        return {
            "duration_sec": duration_sec,
            "bpm": bpm,
            "drop_beat_sec": drop_timestamp,
            "peak_tension_timestamp": peak_point["time"],
            "max_tension_score": peak_point["tension"],
            "catharsis_index": catharsis_score,
            "time_series": time_points,
            "director_recommendations": recommendations
        }
