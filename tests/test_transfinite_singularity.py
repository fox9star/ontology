"""
Comprehensive Unit Test Suite for Tier 8: Non-Euclidean & Metacognitive Transfinite Singularity.
Tests:
1. Poincaré Ball Hyperbolic Embedding & Horosphere Decomposition
2. Spectral Graph Wavelet Transform (SGWT) & Multiresolution Analysis
3. Category-Theoretic Free Monad Engine & Monad Laws
4. Transfinite Ordinal Metacognition & Paradox Dissolver
5. Tier 8 REST API Endpoints (/api/v8/*)
"""

import json
import unittest

from poincare_hyperbolic import PoincareBall
from spectral_graph_wavelet import SpectralGraphWavelet
from free_monad_engine import FreeMonad, FreeMonadInterpreter
from transfinite_metacognition import TransfiniteOrdinal, TransfiniteMetacognition
import app


class TestTransfiniteSingularity(unittest.TestCase):

    def setUp(self):
        self.app = app.app
        self.app.testing = True
        self.client = self.app.test_client()

    # 1. Poincaré Ball Hyperbolic Geometry Tests
    def test_poincare_geodesic_distance_and_mobius_addition(self):
        pb = PoincareBall(dim=3)
        u = [0.2, 0.0, 0.0]
        v = [-0.2, 0.0, 0.0]
        dist = pb.geodesic_distance(u, v)
        self.assertGreater(dist, 0.4)
        # Identity addition with origin
        zero = [0.0, 0.0, 0.0]
        added = pb.mobius_addition(u, zero)
        self.assertAlmostEqual(added[0], u[0], places=4)

    def test_poincare_horosphere_hierarchy_depth(self):
        pb = PoincareBall(dim=3)
        pairs = [
            ("CreativeWork", "MusicVideo"),
            ("MusicVideo", "IndieMV")
        ]
        res = pb.embed_tree_hierarchy(pairs, root="CreativeWork")
        self.assertEqual(res["status"], "poincare_embedding_computed")
        self.assertEqual(res["root_concept"], "CreativeWork")
        # Horosphere depth increases monotonically down the tree
        nodes = res["horosphere_nodes"]
        self.assertEqual(nodes["CreativeWork"]["hyperbolic_depth"], 0.0)
        self.assertGreater(nodes["MusicVideo"]["hyperbolic_depth"], 0.0)
        self.assertGreater(nodes["IndieMV"]["hyperbolic_depth"], nodes["MusicVideo"]["hyperbolic_depth"])

    # 2. Spectral Graph Wavelet (SGWT) Tests
    def test_spectral_graph_wavelet_laplacian_and_chebyshev(self):
        sgwt = SpectralGraphWavelet()
        edges = [("A", "B", 1.0), ("B", "C", 1.0), ("C", "A", 1.0)]
        sgwt.build_graph(edges)
        lap, lam_max = sgwt.get_normalized_laplacian()
        self.assertEqual(len(lap), 3)
        self.assertLessEqual(lam_max, 2.0)

    def test_spectral_graph_wavelet_multiresolution_energy(self):
        sgwt = SpectralGraphWavelet()
        edges = [
            ("CI", "Build", 1.0),
            ("Build", "Test", 1.0),
            ("Test", "Deploy", 1.0),
            ("OutlierNode", "Test", 0.2)
        ]
        res = sgwt.compute_multiresolution_spectrum(edges, scales=[0.5, 2.0])
        self.assertEqual(res["status"], "sgwt_transform_completed")
        self.assertIn("scale_0.5", res["multiresolution_scales"])
        self.assertIn("scale_2.0", res["multiresolution_scales"])
        self.assertGreater(len(res["top_wavelet_anomalies"]), 0)

    # 3. Category-Theoretic Free Monad Tests
    def test_free_monad_laws_formal_verification(self):
        monad = FreeMonad.pure(100)
        laws = monad.verify_monad_laws(test_val=100)
        self.assertTrue(laws["left_identity_law"])
        self.assertTrue(laws["right_identity_law"])
        self.assertTrue(laws["associativity_law"])
        self.assertTrue(laws["all_monad_laws_satisfied"])

    def test_free_monad_transactional_interpretation(self):
        # Monadic program: Checkpoint -> Assert -> Assert -> Pure
        prog = FreeMonad.suspend("CREATE_CHECKPOINT", {"checkpoint_id": "cp1"}, lambda r1:
            FreeMonad.suspend("ASSERT_TRIPLE", {"s": "MV_01", "p": "hasDirector", "o": "Alice"}, lambda r2:
                FreeMonad.suspend("ASSERT_TRIPLE", {"s": "MV_01", "p": "hasBPM", "o": "128"}, lambda r3:
                    FreeMonad.pure("TransactionCommitted")
                )
            )
        )
        interpreter = FreeMonadInterpreter()
        res = interpreter.interpret(prog)
        self.assertEqual(res["status"], "monadic_execution_completed")
        self.assertEqual(res["return_value"], "TransactionCommitted")
        self.assertEqual(res["final_active_triples_count"], 2)

    # 4. Transfinite Ordinal Metacognition Tests
    def test_transfinite_ordinal_ordering(self):
        zero = TransfiniteOrdinal(0, 0)
        one = TransfiniteOrdinal(0, 1)
        omega = TransfiniteOrdinal.omega(1)
        omega_plus_one = omega.successor()

        self.assertTrue(zero < one)
        self.assertTrue(one < omega)
        self.assertTrue(omega < omega_plus_one)
        self.assertEqual(str(omega_plus_one), "omega + 1")

    def test_transfinite_paradox_dissolution_ascension(self):
        meta = TransfiniteMetacognition()
        statements = [
            {"id": "LiarStmt", "text": "Statement LiarStmt is invalid", "negates": []},
            {"id": "RuleA", "text": "RuleA", "negates": ["RuleB"]},
            {"id": "RuleB", "text": "RuleB", "negates": ["RuleA"]}
        ]
        paradoxes = meta.detect_self_referential_paradox(statements)
        self.assertEqual(len(paradoxes), 2)

        # Dissolve via transfinite ascension
        dissolved = meta.dissolve_paradox_via_transfinite_ascension(paradoxes[0])
        self.assertEqual(dissolved["status"], "paradox_dissolved")
        self.assertEqual(dissolved["transfinite_ascended_ordinal"], "omega + 1")
        self.assertTrue(dissolved["godelian_consistency_confirmed"])

    # 5. Tier 8 REST API Tests
    def test_api_v8_poincare_embed(self):
        payload = {
            "pairs": [["CreativeWork", "MusicVideo"], ["MusicVideo", "IndieMV"]],
            "root": "CreativeWork"
        }
        res = self.client.post('/api/v8/poincare/embed-and-distance', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "poincare_embedding_computed")
        self.assertIn("horosphere_nodes", data)

    def test_api_v8_sgwt_wavelet(self):
        payload = {
            "edges": [["DevOps_A", "DevOps_B", 1.0], ["DevOps_B", "DevOps_C", 1.0]],
            "scales": [0.5, 2.0]
        }
        res = self.client.post('/api/v8/sgwt/wavelet-transform', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "sgwt_transform_completed")

    def test_api_v8_free_monad(self):
        payload = {
            "operations": [
                {"op": "ASSERT_TRIPLE", "s": "MV_02", "p": "hasGenre", "o": "Synthwave"}
            ]
        }
        res = self.client.post('/api/v8/free-monad/compose-and-execute', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "monadic_execution_completed")
        self.assertTrue(data["monad_laws"]["all_monad_laws_satisfied"])

    def test_api_v8_transfinite_paradox(self):
        payload = {
            "statements": [
                {"id": "Paradox1", "text": "Statement Paradox1 is invalid", "negates": []}
            ]
        }
        res = self.client.post('/api/v8/transfinite/dissolve-paradox', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "paradox_resolution_completed")
        self.assertEqual(data["resolved_paradoxes_count"], 1)


if __name__ == "__main__":
    unittest.main()
