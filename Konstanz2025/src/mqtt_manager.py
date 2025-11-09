
"""
mqtt_manager.py — Simple, robust MQTT manager for Raspberry Pi 'pillar' installations.

Requires: paho-mqtt >= 2.0
  pip install paho-mqtt

Quick start:
    from mqtt_manager import MqttPillarClient
    pillar = MqttPillarClient(
        broker_host="192.168.1.10",
        base_topic="pillars",
        pillar_id="pillar-01",
        username=None, password=None,
    )
    pillar.connect_and_loop()  # starts background network loop

    # Subscribe to shared triggers
    pillar.subscribe(f"{pillar.base_topic}/broadcast/#", qos=1)

    # Register a handler for incoming triggers
    def on_trigger(topic, payload, props):
        # do something with payload e.g. {'from': 'pillar-02', 'button': 1}
        print("TRIGGER:", topic, payload)
    pillar.on(f"{pillar.base_topic}/broadcast/trigger", on_trigger)

    # When a local button is pressed:
    pillar.send_trigger(button_id=1)

    # Publish state that late joiners should pick up immediately
    pillar.publish_retained(f"{pillar.base_topic}/mode", {"mode": "attract"}, qos=1)

    # On clean shutdown (e.g., SIGINT):
    pillar.close()
"""
from __future__ import annotations

import json
import socket
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, List

import paho.mqtt.client as mqtt
from paho.mqtt.matcher import MQTTMatcher

JSONDict = Dict[str, Any]
Handler = Callable[[str, Any, Optional[mqtt.Properties]], None]

class MqttPillarClientMock:
    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls: bool = False,
        keepalive: int = 30,
        base_topic: str = "pillars",
        pillar_id: Optional[str] = None,
        clean_session: bool = True,
        default_qos: int = 1,
        retain_presence: bool = True,
        reconnect_delay: Tuple[int, int] = (1, 30),
    ) -> None:
        pass

    def on(self, topic_filter: str, handler: Handler) -> None:
        pass

    def publish(self, topic: str, payload: Any, qos: Optional[int] = None, retain: bool = False) -> mqtt.MQTTMessageInfo:
        pass

    def announce_online(self) -> None:
        pass


class MqttPillarClient:
    """Manage MQTT connection, presence, pub/sub, and trigger helpers.

    Design goals:
    - Minimal dependencies (paho-mqtt only)
    - Robust reconnect with backoff
    - Retained presence + Last Will
    - Topic handler registry supporting wildcards
    - JSON payload convenience (auto encode/decode)
    - Background network loop for easy integration in main loops
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls: bool = False,
        keepalive: int = 30,
        base_topic: str = "pillars",
        pillar_id: Optional[str] = None,
        clean_session: bool = True,
        default_qos: int = 1,
        retain_presence: bool = True,
        reconnect_delay: Tuple[int, int] = (1, 30),
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.base_topic = base_topic.rstrip("/")
        self.pillar_id = pillar_id or socket.gethostname()
        self.keepalive = keepalive
        self.default_qos = default_qos
        self.retain_presence = retain_presence

        # Internal state
        self._connected_evt = threading.Event()
        self._stop_evt = threading.Event()
        self._handlers = MQTTMatcher()  # supports wildcard topics
        self._lock = threading.RLock()

        # paho-mqtt client (v2 callback API)
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=(client_id or self.pillar_id),
            clean_session=clean_session,
        )

        if username:
            self.client.username_pw_set(username=username, password=password)
        if tls:
            self.client.tls_set()  # use system CA; customize if needed

        # Last Will & Testament (announce offline if we drop unexpectedly)
        will_topic = f"{self.base_topic}/{self.pillar_id}/status"
        self.client.will_set(will_topic, payload="offline", qos=1, retain=True)

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        # self.client.on_publish = self._on_publish

        # Reconnect backoff
        self.client.reconnect_delay_set(min_delay=reconnect_delay[0], max_delay=reconnect_delay[1])

    # ---------- Public API ----------

    def connect_and_loop(self, start_network_thread: bool = True) -> None:
        """Connect to broker and start the network loop.

        If start_network_thread is True (default), starts a background network loop.
        Otherwise, call self.client.loop_start/loop or integrate with your own poller.
        """
        print("-- broker_host is   ", self.broker_host)
        print("-- broker_port is   ", self.broker_port)
        self.client.connect(self.broker_host, self.broker_port, self.keepalive)
        # <MQTTErrorCode.MQTT_ERR_SUCCESS: 0> -> means no error
        if start_network_thread:
            self.client.loop_start()
        # Wait briefly for connection (non-fatal if it takes longer)
        self._connected_evt.wait(timeout=5.0)

    def on(self, topic_filter: str, handler: Handler) -> None:
        """Register a handler for an MQTT topic filter (wildcards supported).
        Handler signature: handler(topic: str, payload: Any, props: mqtt.Properties|None).
        """
        with self._lock:
            self._handlers[topic_filter] = handler

    def subscribe(self, topic: str, qos: Optional[int] = None) -> None:
        self.client.subscribe(topic, qos if qos is not None else self.default_qos)

    def publish(self, topic: str, payload: Any, qos: Optional[int] = None, retain: bool = False) -> mqtt.MQTTMessageInfo:
        data = self._encode(payload)
        return self.client.publish(topic, data, qos if qos is not None else self.default_qos, retain)

    def publish_retained(self, topic: str, payload: Any, qos: Optional[int] = None) -> mqtt.MQTTMessageInfo:
        return self.publish(topic, payload, qos=qos, retain=True)

    def announce_online(self) -> None:
        if self.retain_presence:
            self.publish_retained(f"{self.base_topic}/{self.pillar_id}/status", "online", qos=1)

    def send_trigger(self, button_id: int, extra: Optional[JSONDict] = None, qos: Optional[int] = None) -> None:
        """Broadcast a simple trigger to all subscribers on the LAN."""
        topic = f"{self.base_topic}/broadcast/trigger"
        payload = {"from": self.pillar_id, "button": int(button_id)}
        if extra:
            payload.update(extra)
        self.publish(topic, payload, qos=qos if qos is not None else self.default_qos)

    def publish_state(self, key: str, value: Any, qos: Optional[int] = None, retain: bool = True) -> None:
        topic = f"{self.base_topic}/{self.pillar_id}/state/{key}"
        self.publish(topic, {"value": value, "ts": time.time()}, qos=qos, retain=retain)

    def close(self, publish_offline: bool = True) -> None:
        """Gracefully stop the loop and disconnect."""
        if publish_offline and self.retain_presence:
            try:
                self.publish_retained(f"{self.base_topic}/{self.pillar_id}/status", "offline", qos=1)
                # give it a moment to flush
                self.client.loop(timeout=0.1)
            except Exception:
                pass
        try:
            self.client.loop_stop()
        except Exception:
            pass
        try:
            self.client.disconnect()
        except Exception:
            pass

    # ---------- Internal callbacks ----------

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int, properties: Optional[mqtt.Properties] = None) -> None:
        if rc == 0:
            self._connected_evt.set()
            self.announce_online()
        else:
            # connection failed; will keep retrying due to reconnect_delay_set
            self._connected_evt.clear()

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int, properties: Optional[mqtt.Properties] = None) -> None:
        self._connected_evt.clear()
        # paho will auto-reconnect if loop is running; presence LWT will fire if ungraceful

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        payload = self._decode(msg.payload)
        # dispatch to exact and wildcard handlers
        # MQTTMatcher returns the most specific match first if multiple are registered
        for handler in self._iter_matching_handlers(msg.topic):
            try:
                handler(msg.topic, payload, getattr(msg, 'properties', None))
            except Exception as e:
                # don't crash the network thread
                print(f"Handler error for {msg.topic}: {e}")

    def _on_subscribe(self, client: mqtt.Client, userdata: Any, mid: int, granted_qos: List[int], properties: Optional[mqtt.Properties] = None) -> None:
        pass  # hook for logging if needed

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int) -> None:
        pass  # hook for logging if needed

    # ---------- Helpers ----------

    def _iter_matching_handlers(self, topic: str):
        # MQTTMatcher iterfind yields (filter, handler)
        for handler in self._handlers.iter_match(topic):
            yield handler

    @staticmethod
    def _encode(payload: Any) -> bytes:
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
        if isinstance(payload, str):
            return payload.encode("utf-8")
        # default to JSON
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")

    @staticmethod
    def _decode(data: bytes) -> Any:
        # try JSON first, fall back to utf-8 string
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            try:
                return data.decode("utf-8")
            except Exception:
                return data  # raw bytes as last resort
