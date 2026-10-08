"""
tests/test_cognitive_api.py - v2 인지 엔진 REST API 엔드포인트 종합 테스트
"""

import json
import unittest
import app


class TestCognitiveAPI(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()

    def test_api_v2_causal_what_if(self):
        payload = {"interventions": {"BGM_Tempo_BPM": 150.0}}
        res = self.app.post(
            '/api/v2/causal/what-if',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("Audience_Engagement_Score", data["counterfactual_state"])

    def test_api_v2_evolver_mine_and_verify(self):
        payload = {
            "text": "이번 씬은 DroneHyperlapse 촬영과 TealOrangeLUT 색보정이 필수적입니다.",
            "ont": "mv"
        }
        res = self.app.post(
            '/api/v2/evolver/mine-and-verify',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(len(data["candidates"]), 1)
        self.assertTrue(data["verdict"]["approved"])

    def test_api_v2_kge_verify_axiom(self):
        # Subclass verification
        payload = {"axiom": "subclass", "class_a": "Shot", "class_b": "MediaAsset"}
        res = self.app.post(
            '/api/v2/kge/verify-axiom',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["verified"])

        # Disjoint verification
        payload_disjoint = {"axiom": "disjoint", "class_a": "Shot", "class_b": "AudioTrack"}
        res_d = self.app.post(
            '/api/v2/kge/verify-axiom',
            data=json.dumps(payload_disjoint),
            content_type='application/json'
        )
        self.assertEqual(res_d.status_code, 200)
        self.assertTrue(res_d.get_json()["verified"])

    def test_api_v2_arbiter_arbitrate(self):
        payload = {
            "title": "Scene 1 Drop Beat Conflict",
            "proposals": [
                {
                    "agent": "DirectorAgent",
                    "action": "extend_shot",
                    "params": {"duration": 14.0}
                },
                {
                    "agent": "AudioEngineerAgent",
                    "action": "enforce_beat_sync",
                    "params": {"drop_beat_timestamp": 8.0, "require_cut_at_drop": True}
                }
            ]
        }
        res = self.app.post(
            '/api/v2/arbiter/arbitrate',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ARBITRATED_SUCCESSFULLY")
        self.assertIn("court_ruling", data)

    def test_api_v2_temporal_snapshot(self):
        res = self.app.get('/api/v2/temporal/snapshot?timestamp=5.0')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["query_timestamp_sec"], 5.0)
        self.assertGreater(data["active_facts_count"], 0)


if __name__ == "__main__":
    unittest.main()
