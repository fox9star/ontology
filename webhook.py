"""
Real-time Notification Webhook Module for Slack Block Kit, Discord, and Generic JSON Webhooks.
"""

import json
import logging
from typing import Dict, Any, Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def send_slack_notification(self, title: str, status: str, details: Dict[str, Any]) -> bool:
        """Send formatted Slack Block Kit message."""
        color = "#36a64f" if status == "SUCCESS" else "#ff0000"
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🤖 {title}", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:* `{status}`"},
                    {"type": "mrkdwn", "text": f"*Domain:* `{details.get('domain', 'N/A')}`"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```\n{json.dumps(details, indent=2, ensure_ascii=False)}\n```"}
            }
        ]
        payload = {"attachments": [{"color": color, "blocks": blocks}]}
        return self._dispatch(payload)

    def send_generic_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send raw JSON payload to target webhook URL."""
        payload = {"event": event_type, "timestamp": data.get("timestamp"), "data": data}
        return self._dispatch(payload)

    def _dispatch(self, payload: Dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.info(f"[SIMULATED WEBHOOK NOTIFICATION] Payload: {json.dumps(payload, ensure_ascii=False)}")
            return True
        try:
            res = requests.post(self.webhook_url, json=payload, timeout=5)
            if res.status_code in (200, 201, 202, 204):
                logger.info(f"Webhook delivered successfully to {self.webhook_url}")
                return True
            else:
                logger.error(f"Webhook HTTP error {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to dispatch webhook: {e}")
            return False

if __name__ == "__main__":
    notifier = WebhookNotifier()
    notifier.send_slack_notification(
        title="PySHACL Validation Passed",
        status="SUCCESS",
        details={"domain": "mv", "conforms": True, "triples": 142}
    )
