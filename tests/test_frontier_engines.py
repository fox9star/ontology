"""
tests/test_frontier_engines.py - 프론티어 4대 묘수 엔진 및 v3 API 종합 단위 테스트
1. Axiom-to-LoRA Knowledge Distiller (knowledge_distiller.py)
2. Neuro-Aesthetic Tension Engine (aesthetic_tension.py)
3. Probabilistic Soft Logic Engine (probabilistic_logic.py)
4. Frontier REST APIs & Digital Twin UI (/digital-twin, /api/v3/...)
"""

import json
import unittest
import rdflib

from knowledge_distiller import KnowledgeDistiller
from aesthetic_tension import AestheticTensionEngine
from probabilistic_logic import ProbabilisticLogicEngine
import app


class TestFrontierEngines(unittest.TestCase):

    def setUp(self):
        self.client = app.app.test_client()

    # 1. Knowledge Distiller Unit Tests
    def test_knowledge_distiller_synthesis(self):
        g = rdflib.Graph()
        g.parse(data="""
            @prefix : <http://example.org/ontology/mv#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            :Shot a owl:Class ; rdfs:label "Shot"@en .
            :CloseUpShot a owl:Class ; rdfs:subClassOf :Shot ; rdfs:label "CloseUpShot"@en .
            :AudioTrack a owl:Class ; owl:disjointWith :Shot .
        """, format="turtle")

        distiller = KnowledgeDistiller(g)
        dataset = distiller.synthesize_lora_dataset(domain="mv", max_samples=10)
        self.assertGreater(len(dataset), 0)
        self.assertIn("instruction", dataset[0])
        self.assertIn("output", dataset[0])

        cfg = distiller.export_lora_config(len(dataset))
        self.assertEqual(cfg["lora_r"], 16)
        self.assertIn("Llama-3-8B", cfg["model_architecture"])

    # 2. Aesthetic Tension Unit Tests
    def test_aesthetic_tension_computation(self):
        engine = AestheticTensionEngine()
        res = engine.compute_tension_curve(duration_sec=16.0, bpm=140.0, drop_timestamp=8.0)
        self.assertGreater(len(res["time_series"]), 10)
        self.assertGreaterEqual(res["max_tension_score"], 0.0)
        self.assertLessEqual(res["max_tension_score"], 1.0)
        self.assertGreater(res["catharsis_index"], 0.0)
        self.assertGreater(len(res["director_recommendations"]), 0)

    # 3. Probabilistic Soft Logic Unit Tests
    def test_probabilistic_soft_logic_inference(self):
        engine = ProbabilisticLogicEngine()
        observed = {"HighAudioEnergy": 0.95, "FastCutCadence": 0.85, "DarkLighting": 0.1}
        result = engine.infer(observed, iterations=5)
        self.assertEqual(result["status"], "success")
        self.assertIn("HighEngagement", result["inferred_truth_values"])
        # High audio energy + fast cuts should yield high engagement probability
        self.assertGreater(result["inferred_truth_values"]["HighEngagement"], 0.7)

    # 4. Frontier REST APIs Tests
    def test_api_digital_twin_ui(self):
        res = self.client.get('/digital-twin')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ONTOLOGY DIGITAL TWIN", res.data)
        self.assertIn(b"graphCanvas", res.data)

    def test_api_v3_distill_dataset(self):
        res = self.client.get('/api/v3/distill/dataset?limit=5')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("training_dataset", data)
        self.assertIn("lora_hyperparameters", data)

    def test_api_v3_aesthetic_tension_curve(self):
        res = self.client.get('/api/v3/aesthetic/tension-curve?bpm=135&duration=12')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["bpm"], 135.0)
        self.assertIn("time_series", data)

    def test_api_v3_probabilistic_infer(self):
        payload = {"facts": {"HighAudioEnergy": 0.9, "FastCutCadence": 0.8}}
        res = self.client.post('/api/v3/probabilistic/infer', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("HighEngagement", data["inferred_truth_values"])


if __name__ == "__main__":
    unittest.main()
