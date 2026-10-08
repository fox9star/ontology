"""
tests/test_cognitive_breakthroughs.py - 5대 묘수 인지 엔진 종합 단위 테스트
1. Causal Knowledge Graph & What-If Simulator (causal_engine.py)
2. Self-Evolving Neuro-Symbolic Loop (ontology_evolver.py)
3. Ontology-Guided Geometric KGE (geometric_kge.py)
4. Multi-Agent Semantic Court (semantic_arbiter.py)
5. 4D Fluents & Time-Travel Graph Engine (temporal_graph.py)
"""

import unittest
import rdflib

from causal_engine import CausalKnowledgeGraph
from ontology_evolver import OntologyEvolver
from geometric_kge import GeometricKGEmbedding, HyperBox
from semantic_arbiter import SemanticArbiter
from temporal_graph import TemporalKnowledgeGraph


class TestCognitiveBreakthroughs(unittest.TestCase):

    # -------------------------------------------------------------
    # 1. Causal Knowledge Graph Tests
    # -------------------------------------------------------------
    def test_causal_what_if_simulation(self):
        ckg = CausalKnowledgeGraph()
        # What-if: BPM을 128에서 175로 대폭 가속했을 때의 인과 전파 시뮬레이션
        result = ckg.simulate_what_if(interventions={"BGM_Tempo_BPM": 175.0})

        self.assertEqual(result["status"], "success")
        self.assertIn("BGM_Tempo_BPM", result["applied_interventions"])
        self.assertGreater(result["counterfactual_state"]["Audio_Energy_Level"], result["baseline_state"]["Audio_Energy_Level"])
        self.assertGreater(len(result["causal_propagation_paths"]), 0)
        self.assertIsInstance(result["diagnostics"], list)

    # -------------------------------------------------------------
    # 2. Self-Evolving Neuro-Symbolic Loop Tests
    # -------------------------------------------------------------
    def test_ontology_evolver_mining_and_sandbox(self):
        evolver = OntologyEvolver()
        sample_log = "새로운 씬에서는 DroneHyperlapse 촬영 기법과 SpatialAudioReverb 음향 효과가 결합되어야 합니다."
        candidates = evolver.mine_candidate_concepts(sample_log, domain="mv")
        self.assertGreaterEqual(len(candidates), 2)

        ttl_patch = evolver.generate_candidate_ttl(candidates, domain="mv")
        self.assertIn("DroneHyperlapse", ttl_patch)
        self.assertIn("SpatialAudioReverb", ttl_patch)

        # Base in-memory RDF 그래프 생성
        base_g = rdflib.Graph()
        base_g.parse(data="""
            @prefix : <http://example.org/ontology/mv#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            :CameraMovement a owl:Class .
            :AudioEffect a owl:Class .
        """, format="turtle")

        verdict = evolver.sandbox_verify_evolution(base_g, ttl_patch, domain="mv")
        self.assertTrue(verdict["approved"])
        self.assertLess(verdict["risk_score"], 0.2)

    # -------------------------------------------------------------
    # 3. Geometric KGE Tests
    # -------------------------------------------------------------
    def test_geometric_kge_subclass_and_disjoint(self):
        kge = GeometricKGEmbedding(dim=8)

        # Shot is subClass of MediaAsset -> Box containment must hold
        ok, msg = kge.verify_subclass_axiom("Shot", "MediaAsset")
        self.assertTrue(ok)
        self.assertIn("GEOMETRIC PROOF", msg)

        # Shot and AudioTrack are Disjoint -> Box intersection must be empty
        ok_disjoint, d_msg = kge.verify_disjointness_axiom("Shot", "AudioTrack")
        self.assertTrue(ok_disjoint)
        self.assertIn("GEOMETRIC PROOF", d_msg)

        # Zero hallucination check
        self.assertTrue(kge.zero_hallucination_check("Shot", "MediaAsset"))

    # -------------------------------------------------------------
    # 4. Multi-Agent Semantic Court Tests
    # -------------------------------------------------------------
    def test_semantic_arbiter_court_ruling(self):
        arbiter = SemanticArbiter()
        dispute_proposals = [
            {
                "agent": "DirectorAgent",
                "action": "extend_shot",
                "params": {"shot_id": "Shot1", "duration": 12.0}
            },
            {
                "agent": "AudioEngineerAgent",
                "action": "enforce_beat_sync",
                "params": {"drop_beat_timestamp": 8.0, "require_cut_at_drop": True}
            }
        ]

        verdict = arbiter.arbitrate_dispute("Dispute-Session-2026-MV-01", dispute_proposals)
        self.assertEqual(verdict["status"], "ARBITRATED_SUCCESSFULLY")
        self.assertEqual(verdict["hard_conflicts_count"], 1)
        self.assertIn("스피드 램프", verdict["court_ruling"]["ruling_name"])
        self.assertIn("Axiom-MV-01", verdict["findings_of_conflict"][0]["violated_statute"]["id"])

    # -------------------------------------------------------------
    # 5. Temporal 4D Fluents Graph Tests
    # -------------------------------------------------------------
    def test_temporal_graph_point_in_time_and_lineage(self):
        tkg = TemporalKnowledgeGraph()

        # t = 4.0초 (Shot1 활성 구간) 스냅샷 조회
        snap_4s = tkg.query_point_in_time(4.0)
        self.assertGreater(snap_4s["active_facts_count"], 0)
        self.assertIn("http://example.org/ontology/mv#Shot1", snap_4s["active_entities"])
        self.assertNotIn("http://example.org/ontology/mv#Shot2", snap_4s["active_entities"])

        # t = 10.0초 (Shot2 활성 구간) 스냅샷 조회
        snap_10s = tkg.query_point_in_time(10.0)
        self.assertIn("http://example.org/ontology/mv#Shot2", snap_10s["active_entities"])
        self.assertNotIn("http://example.org/ontology/mv#Shot1", snap_10s["active_entities"])

        # Shot1의 타임라인 라이니지 추적
        lineage = tkg.trace_entity_lineage("http://example.org/ontology/mv#Shot1")
        self.assertEqual(len(lineage), 3)

        # 7.0초 ~ 9.0초 사이의 상태 전환 이벤트 감지
        transitions = tkg.detect_state_transitions(7.0, 9.0)
        self.assertGreater(len(transitions), 0)


if __name__ == "__main__":
    unittest.main()
