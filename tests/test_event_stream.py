"""
Unit tests for SSE Event Stream and Real-time Telemetry Bus.
"""

import unittest
from app import app
import event_stream


class TestEventStream(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_format_sse(self):
        msg = event_stream.format_sse({"key": "val"}, event="TEST_EV", event_id=42)
        self.assertIn("id: 42\n", msg)
        self.assertIn("event: TEST_EV\n", msg)
        self.assertIn('data: {"key": "val"}\n\n', msg)

    def test_publish_and_history(self):
        event = event_stream.publish_event("CUSTOM_TEST", {"agent": "TestAgent", "status": "active"})
        self.assertEqual(event["event"], "CUSTOM_TEST")
        self.assertEqual(event["payload"]["agent"], "TestAgent")

        history = event_stream.bus.get_history(limit=5)
        self.assertTrue(any(e["event"] == "CUSTOM_TEST" for e in history))

    def test_subscribe_and_unsubscribe(self):
        q = event_stream.bus.subscribe()
        self.assertIn(q, event_stream.bus._subscribers)
        event_stream.publish_event("SUB_TEST", {"ping": "pong"})
        item = q.get(timeout=1.0)
        self.assertEqual(item["event"], "SUB_TEST")
        event_stream.bus.unsubscribe(q)
        self.assertNotIn(q, event_stream.bus._subscribers)

    def test_api_stream_broadcast(self):
        res = self.client.post('/api/v1/stream/broadcast', json={
            "event": "API_BROADCAST_TEST",
            "payload": {"hello": "world"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["event"]["event"], "API_BROADCAST_TEST")

    def test_api_stream_history(self):
        res = self.client.get('/api/v1/stream/history?limit=10')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("history", data)
        self.assertIn("active_clients", data)


if __name__ == "__main__":
    unittest.main()
