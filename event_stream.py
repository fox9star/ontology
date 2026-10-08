"""
Real-time Server-Sent Events (SSE) & Telemetry Event Bus
Provides ultra-low-latency real-time broadcasting of agent handoffs, task state changes,
SHACL alerts, instance mutations, and pipeline telemetry to connected web clients.
Pure Python, thread-safe, zero external broker dependency.
"""

import time
import json
import queue
import threading
from datetime import datetime


class EventBus:
    """Thread-safe publish-subscribe event bus for Server-Sent Events."""
    def __init__(self, max_history=100):
        self._subscribers = set()
        self._lock = threading.Lock()
        self._history = []
        self._max_history = max_history
        self._event_counter = 0

    def subscribe(self):
        """Returns a queue.Queue for a new subscriber client."""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q):
        """Removes a subscriber queue."""
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, event_type, payload=None):
        """
        Publishes an event to all active subscriber queues.
        Also retains recent event history.
        """
        with self._lock:
            self._event_counter += 1
            event = {
                "id": self._event_counter,
                "event": event_type,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "payload": payload or {}
            }
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            # Broadcast to all connected queues
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead_queues.append(q)
            for dq in dead_queues:
                self._subscribers.discard(dq)

        return event

    def get_history(self, limit=20):
        """Returns recent event history."""
        with self._lock:
            return list(self._history[-limit:])

    def active_subscribers_count(self):
        with self._lock:
            return len(self._subscribers)


# Global singleton instance
bus = EventBus()


def publish_event(event_type, payload=None):
    """Global helper to publish an event."""
    return bus.publish(event_type, payload)


def format_sse(data, event=None, event_id=None):
    """Formats a message for Server-Sent Events stream."""
    msg = ""
    if event_id is not None:
        msg += f"id: {event_id}\n"
    if event:
        msg += f"event: {event}\n"
    msg += f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    return msg


def sse_event_stream(timeout=25.0):
    """
    Generator yielding Server-Sent Events for Flask Response streaming.
    Sends an initial connected ping and periodic keepalive heartbeats.
    """
    q = bus.subscribe()
    try:
        # Initial greeting event
        yield format_sse({
            "status": "connected",
            "message": "AI Agent Ontology SSE Telemetry Bus Connected",
            "active_clients": bus.active_subscribers_count()
        }, event="sys_init", event_id=0)

        while True:
            try:
                event = q.get(timeout=timeout)
                yield format_sse(event["payload"], event=event["event"], event_id=event["id"])
            except queue.Empty:
                # Keepalive heartbeat
                yield f": keepalive {int(time.time())}\n\n"
    finally:
        bus.unsubscribe(q)
