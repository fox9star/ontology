"""
Comprehensive Unit Test Suite for Tier 6: Transcendent Cognitive Frontiers.
Tests:
1. Hyperdimensional Vector Symbolic Architecture (HDC / VSA)
2. Active Inference & Variational Free Energy Minimization (FEP)
3. Autopoietic Self-Compiling Quine Ontology
4. Decentralized Byzantine Semantic CRDT Swarm Consensus
5. Tier 6 REST API Endpoints (/api/v6/*)
"""

import json
import unittest

from hyperdimensional_vsa import HyperdimensionalVSA, HDVector
from active_inference_fep import ActiveInferenceEngine
from autopoietic_quine import AutopoieticQuine
from semantic_crdt_swarm import SemanticCRDTNode, SemanticSwarmOrchestrator
import app


class TestTranscendentFrontier(unittest.TestCase):

    def setUp(self):
        self.app = app.app
        self.app.testing = True
        self.client = self.app.test_client()

    # 1. Hyperdimensional Computing (HDC / VSA) Tests
    def test_hyperdimensional_binding_and_unbinding(self):
        dim = 1024
        u = HDVector.random_deterministic("ConceptA", dim)
        v = HDVector.random_deterministic("ConceptB", dim)
        bound = u.bind(v)
        # Self-inverse unbinding: u * (u * v) == v
        unbound_v = u.bind(bound)
        self.assertEqual(unbound_v.values, v.values)
        self.assertAlmostEqual(unbound_v.cosine_similarity(v), 1.0, places=4)

    def test_hyperdimensional_graph_encoding_and_query(self):
        hdc = HyperdimensionalVSA(dim=2048)
        triples = [
            ("MV_Cyberpunk", "hasDirector", "Alice"),
            ("MV_Cyberpunk", "hasBPM", "140"),
            ("MV_Acoustic", "hasDirector", "Bob")
        ]
        graph_vec = hdc.encode_graph(triples)
        results = hdc.query_object(graph_vec, "MV_Cyberpunk", "hasDirector", candidates=["Alice", "Bob", "Charlie"])
        self.assertEqual(results[0][0], "Alice")
        self.assertGreater(results[0][1], 0.3)

    def test_hyperdimensional_noise_resilience(self):
        hdc = HyperdimensionalVSA(dim=2048)
        report = hdc.benchmark_noise_resilience("MV_Rock", "hasDirector", "Dave", noise_levels=[0.1, 0.25, 0.4])
        # Up to 40% noise should remain correctly identifiable
        self.assertTrue(report["resilience_curve"]["noise_10pct"]["identified_correctly"])
        self.assertTrue(report["resilience_curve"]["noise_25pct"]["identified_correctly"])
        self.assertTrue(report["resilience_curve"]["noise_40pct"]["identified_correctly"])

    # 2. Active Inference & Free Energy Minimization (FEP) Tests
    def test_active_inference_variational_free_energy(self):
        engine = ActiveInferenceEngine()
        obs = {
            "mv": {"sample_count": 10, "verified_triples_ratio": 0.95, "unresolved_anomalies_count": 0},
            "devops": {"sample_count": 2, "verified_triples_ratio": 0.50, "unresolved_anomalies_count": 3}
        }
        res = engine.evaluate_free_energy(obs)
        self.assertEqual(res["status"], "active_inference_converged")
        self.assertIn("global_variational_free_energy", res)
        # devops domain has anomalies, so it should trigger an epistemic curiosity probe
        self.assertTrue(any(p["target_domain"] == "devops" for p in res["epistemic_curiosity_probes"]))

    def test_active_inference_epistemic_foraging(self):
        engine = ActiveInferenceEngine()
        foraging_res = engine.execute_epistemic_foraging("healthcare", 6)
        self.assertEqual(foraging_res["status"], "epistemic_foraging_successful")
        self.assertTrue(foraging_res["free_energy_reduction_achieved"])

    # 3. Autopoietic Quine Ontology Tests
    def test_autopoietic_quine_lesion_detection(self):
        quine = AutopoieticQuine()
        # Missing "MusicVideo" and mandatory properties
        active_classes = ["Pipeline", "PatientRecord"]
        active_props = ["hasPipelineId", "hasPatientId"]
        integrity = quine.inspect_graph_integrity(active_classes, active_props)
        self.assertFalse(integrity["intact"])
        self.assertGreater(integrity["lesion_count"], 0)
        self.assertTrue(any(l["target_entity"] == "MusicVideo" for l in integrity["lesions"]))

    def test_autopoietic_quine_self_repair(self):
        quine = AutopoieticQuine()
        active_classes = ["PatientRecord"]
        active_props = ["hasPatientId"]
        integrity = quine.inspect_graph_integrity(active_classes, active_props)
        repair = quine.synthesize_self_repair(integrity["lesions"])
        self.assertEqual(repair["status"], "autopoietic_regeneration_completed")
        self.assertTrue(repair["quine_integrity_confirmed"])
        self.assertGreater(len(repair["generated_rdf_triples"]), 0)
        # Quine source generation
        source = quine.generate_quine_source()
        self.assertIn("Autopoietic Quine Ontology", source)

    # 4. Decentralized Semantic CRDT Swarm Tests
    def test_semantic_crdt_semilattice_monotonicity(self):
        node_a = SemanticCRDTNode("node-a")
        node_b = SemanticCRDTNode("node-b")

        rec1 = node_a.add_triple("Scene_01", "hasLighting", "NeonDark")
        time_old = rec1.timestamp
        # Merge into node_b
        res = node_b.merge_semilattice([rec1])
        self.assertEqual(res["accepted_triples"], 1)
        self.assertEqual(node_b.get_active_triples(), [("Scene_01", "hasLighting", "NeonDark")])

    def test_semantic_crdt_byzantine_quarantine(self):
        honest_node = SemanticCRDTNode("honest-01")
        byzantine_node = SemanticCRDTNode("byzantine-66", is_byzantine=True)

        bad_rec1 = byzantine_node.add_triple("ExploitPayload", "rdf:type", "Attack")
        bad_rec2 = byzantine_node.add_triple("PatientRecord_01", "rdf:type", "MusicVideo")  # Disjointness violation

        merge_res = honest_node.merge_semilattice([bad_rec1, bad_rec2])
        self.assertEqual(merge_res["accepted_triples"], 0)
        self.assertEqual(merge_res["rejected_byzantine_triples"], 2)
        self.assertEqual(len(honest_node.quarantine_store), 2)

    def test_semantic_crdt_swarm_consensus(self):
        swarm = SemanticSwarmOrchestrator(node_count=4)
        swarm.nodes["agent-node-01"].add_triple("Song_01", "hasTempo", "120")
        swarm.nodes["agent-node-02"].add_triple("Scene_02", "hasActor", "Eve")

        # 3 rounds of gossip
        for _ in range(3):
            r = swarm.execute_epidemic_gossip_round()

        self.assertTrue(r["consensus_achieved"])
        self.assertEqual(r["shared_triples_count"], 2)

    # 5. Tier 6 REST API Tests
    def test_api_v6_hdc_query(self):
        payload = {
            "triples": [["MV_Cyberpunk", "hasDirector", "Alice"], ["MV_Cyberpunk", "hasBPM", "140"]],
            "query_subject": "MV_Cyberpunk",
            "query_predicate": "hasDirector",
            "candidates": ["Alice", "Bob"]
        }
        res = self.client.post('/api/v6/hdc/query', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["top_match"], "Alice")

    def test_api_v6_active_inference(self):
        payload = {
            "observations": {
                "mv": {"sample_count": 8, "verified_triples_ratio": 0.9, "unresolved_anomalies_count": 0}
            }
        }
        res = self.client.post('/api/v6/active-inference/evaluate', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("global_variational_free_energy", data)

    def test_api_v6_autopoiesis(self):
        payload = {
            "active_classes": ["PatientRecord"],
            "active_properties": ["hasPatientId"]
        }
        res = self.client.post('/api/v6/autopoiesis/repair', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "autopoietic_regeneration_completed")

    def test_api_v6_crdt_swarm(self):
        payload = {"node_count": 3, "simulate_byzantine": True}
        res = self.client.post('/api/v6/crdt-swarm/sync', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["gossip_round_status"], "completed")
        self.assertTrue(data["consensus_achieved"])


if __name__ == "__main__":
    unittest.main()
