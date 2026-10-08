"""
temporal_graph.py - 4차원 시공간 플루언트 (4D Fluents & Temporal KG) 타임머신 엔진
- OWL-Time 및 4D Fluents 패턴을 적용하여 시간 축을 따라 상태가 변화하는 지식 그래프 모델링
- 타임머신 포인트-인-타임(Point-in-Time) 스냅샷 재구성 및 개체 생애주기 궤적(Entity Lineage) 추적
"""

from typing import Dict, List, Any, Optional, Tuple
import rdflib
from rdflib import Namespace, RDF, RDFS, Literal, URIRef

TEMPORAL = Namespace("http://example.org/ontology/temporal#")
MV = Namespace("http://example.org/ontology/mv#")


class TemporalFluentTriple:
    """시간 구간 [valid_from, valid_to) 동안 유효한 4차원 시공간 삼원조"""

    def __init__(
        self,
        subject: str,
        predicate: str,
        obj: Any,
        valid_from: float,
        valid_to: float,
        fluent_id: Optional[str] = None
    ):
        self.subject = subject
        self.predicate = predicate
        self.obj = obj
        self.valid_from = float(valid_from)
        self.valid_to = float(valid_to)
        self.fluent_id = fluent_id or f"fluent_{abs(hash((subject, predicate, str(obj), valid_from)))}"

    def is_active_at(self, timestamp: float) -> bool:
        """특정 시점 t에 이 삼원조가 유효한지 판정"""
        return self.valid_from <= timestamp < self.valid_to


class TemporalKnowledgeGraph:
    """4D 플루언트 삼원조를 관리하고 임의 시점의 그래프 상태를 복원하는 타임머신 엔진"""

    def __init__(self):
        self.fluents: List[TemporalFluentTriple] = []
        self._seed_sample_temporal_data()

    def _seed_sample_temporal_data(self):
        """뮤직비디오 타임라인 4D 시공간 상태 데이터 시딩"""
        # Shot 1 (0.0초 ~ 8.0초): 오프닝 야경, Teal&Orange, 35mm 렌즈, 차분한 무드
        self.add_fluent("http://example.org/ontology/mv#Shot1", "http://example.org/ontology/mv#activeColorGrade", "TealAndOrangeLUT", 0.0, 8.0)
        self.add_fluent("http://example.org/ontology/mv#Shot1", "http://example.org/ontology/mv#cameraLens", "35mm_Anamorphic", 0.0, 8.0)
        self.add_fluent("http://example.org/ontology/mv#Shot1", "http://example.org/ontology/mv#lightingMood", "NeonMoodyDark", 0.0, 8.0)

        # Shot 2 (8.0초 ~ 16.5초): 드롭 비트 폭발, 붉은 스트로브 조명, 24mm 광각, 격렬한 무드
        self.add_fluent("http://example.org/ontology/mv#Shot2", "http://example.org/ontology/mv#activeColorGrade", "CyberpunkHighContrast", 8.0, 16.5)
        self.add_fluent("http://example.org/ontology/mv#Shot2", "http://example.org/ontology/mv#cameraLens", "24mm_UltraWide", 8.0, 16.5)
        self.add_fluent("http://example.org/ontology/mv#Shot2", "http://example.org/ontology/mv#lightingMood", "StrobePulsingRed", 8.0, 16.5)

        # 음악 트랙 상태 변화: 0.0~8.0 (빌드업 100 BPM), 8.0~16.5 (드롭 클라이맥스 140 BPM)
        self.add_fluent("http://example.org/ontology/mv#MainAudioTrack", "http://example.org/ontology/mv#currentSection", "IntroBuildUp", 0.0, 8.0)
        self.add_fluent("http://example.org/ontology/mv#MainAudioTrack", "http://example.org/ontology/mv#tempoBPM", 100, 0.0, 8.0)
        self.add_fluent("http://example.org/ontology/mv#MainAudioTrack", "http://example.org/ontology/mv#currentSection", "ClimaxDrop", 8.0, 16.5)
        self.add_fluent("http://example.org/ontology/mv#MainAudioTrack", "http://example.org/ontology/mv#tempoBPM", 140, 8.0, 16.5)

    def add_fluent(self, s: str, p: str, o: Any, valid_from: float, valid_to: float):
        fluent = TemporalFluentTriple(s, p, o, valid_from, valid_to)
        self.fluents.append(fluent)
        return fluent

    def query_point_in_time(self, timestamp: float) -> Dict[str, Any]:
        """특정 시점 t의 지식 그래프 상태를 100% 완전 복원 (Point-in-Time Snapshot)"""
        active_facts = []
        entities_present = set()

        for f in self.fluents:
            if f.is_active_at(timestamp):
                active_facts.append({
                    "subject": f.subject,
                    "predicate": f.predicate,
                    "object": f.obj,
                    "valid_range": f"{f.valid_from:.1f}s ~ {f.valid_to:.1f}s"
                })
                entities_present.add(f.subject)

        return {
            "query_timestamp_sec": float(timestamp),
            "active_facts_count": len(active_facts),
            "active_entities": sorted(list(entities_present)),
            "snapshot_graph": active_facts
        }

    def trace_entity_lineage(self, entity_uri: str) -> List[Dict[str, Any]]:
        """특정 엔티티가 시간에 따라 어떤 상태 전이를 겪었는지 궤적(Timeline Trace) 추출"""
        history = []
        for f in self.fluents:
            if f.subject == entity_uri:
                history.append({
                    "predicate": f.predicate.split("#")[-1] if "#" in f.predicate else f.predicate,
                    "value": f.obj,
                    "valid_from": f.valid_from,
                    "valid_to": f.valid_to,
                    "duration": round(f.valid_to - f.valid_from, 2)
                })

        history.sort(key=lambda x: x["valid_from"])
        return history

    def detect_state_transitions(self, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """지정된 시간 구간 [start_time, end_time] 내에 발생한 모든 상태 전환 이벤트 감지"""
        events = []
        for f in self.fluents:
            if start_time <= f.valid_from <= end_time:
                events.append({
                    "timestamp": f.valid_from,
                    "event_type": "STATE_ENTER",
                    "subject": f.subject.split("#")[-1],
                    "predicate": f.predicate.split("#")[-1],
                    "new_value": f.obj
                })
            if start_time <= f.valid_to <= end_time:
                events.append({
                    "timestamp": f.valid_to,
                    "event_type": "STATE_EXIT",
                    "subject": f.subject.split("#")[-1],
                    "predicate": f.predicate.split("#")[-1],
                    "old_value": f.obj
                })

        events.sort(key=lambda x: x["timestamp"])
        return events
