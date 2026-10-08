import unittest
import os
import sys
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webhook import WebhookNotifier

class TestWebhookNotifier(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.remote = patch("webhook.requests.post", side_effect=AssertionError("Unexpected network request"))
        self.post = self.remote.start()
        self.addCleanup(self.remote.stop)

    def test_simulated_dispatch(self):
        notifier = WebhookNotifier(webhook_url=None)
        res_slack = notifier.send_slack_notification(
            title="Unit Test Event",
            status="SUCCESS",
            details={"test": True}
        )
        self.assertTrue(res_slack)
        
        res_generic = notifier.send_generic_event("test_event", {"status": "ok"})
        self.assertTrue(res_generic)
        self.post.assert_not_called()

    def test_explicit_delivery_is_mocked(self):
        self.post.side_effect = None
        self.post.return_value = Mock(status_code=204)
        notifier = WebhookNotifier(webhook_url="https://example.invalid/webhook")
        self.assertTrue(notifier.send_generic_event("test_event", {"status": "ok"}))
        self.post.assert_called_once()

    def test_delivery_error_is_reported(self):
        self.post.side_effect = requests.ConnectionError("offline test")
        notifier = WebhookNotifier(webhook_url="https://example.invalid/webhook")
        self.assertFalse(notifier.send_generic_event("test_event", {}))

if __name__ == "__main__":
    unittest.main()
