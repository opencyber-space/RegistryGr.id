from __future__ import annotations
import hashlib
import json
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable


@dataclass
class NostrEvent:
    id: str = ""
    pubkey: str = ""
    created_at: int = 0
    kind: int = 0
    content: str = ""
    sig: str = ""
    tags: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "content": self.content,
            "sig": self.sig,
            "tags": self.tags,
        }


@dataclass
class Filter:
    kinds: List[int] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    since: Optional[int] = None
    until: Optional[int] = None


@dataclass
class Subscription:
    id: str
    filters: List[Filter]
    callback: Callable[[NostrEvent], None]


KIND_ASSET_EVENT = 30000
KIND_AUTHOR_MANIFEST = 30001
KIND_PROPAGATION_INTENT = 30002
KIND_REVOCATION = 5
KIND_L2_CHECKPOINT = 30003
KIND_WATCHDOG_AUDIT_REPORT = 30004


class EventSpace:
    def is_asset_event(self, kind: int) -> bool:
        return kind == KIND_ASSET_EVENT

    def is_revocation(self, kind: int) -> bool:
        return kind == KIND_REVOCATION

    def is_checkpoint(self, kind: int) -> bool:
        return kind == KIND_L2_CHECKPOINT

    def is_watchdog_report(self, kind: int) -> bool:
        return kind == KIND_WATCHDOG_AUDIT_REPORT


class NostrRelay:
    def __init__(self, role: str = "primary"):
        self._lock = threading.Lock()
        self._events: List[NostrEvent] = []
        self._subscriptions: Dict[str, Subscription] = {}
        self.role = role

    def persist_event(self, event: NostrEvent):
        with self._lock:
            self._events.append(event)
            self._notify(event)

    def _notify(self, event: NostrEvent):
        for sub in self._subscriptions.values():
            if self._matches(event, sub.filters):
                try:
                    sub.callback(event)
                except Exception:
                    pass

    def _matches(self, event: NostrEvent, filters: List[Filter]) -> bool:
        if not filters:
            return True
        for f in filters:
            if event.kind in f.kinds:
                return True
        return False

    def subscribe(self, sub_id: str, filters: List[Filter], callback: Callable[[NostrEvent], None]) -> Subscription:
        sub = Subscription(id=sub_id, filters=filters, callback=callback)
        with self._lock:
            self._subscriptions[sub_id] = sub
        return sub

    def unsubscribe(self, sub_id: str):
        with self._lock:
            self._subscriptions.pop(sub_id, None)

    def list_events(self) -> List[NostrEvent]:
        with self._lock:
            return list(self._events)

    def replicate_from(self, source: "NostrRelay"):
        def _worker():
            while True:
                time.sleep(5)
                source_events = source.list_events()
                with self._lock:
                    existing_ids = {e.id for e in self._events}
                for e in source_events:
                    if e.id not in existing_ids:
                        self.persist_event(e)
        t = threading.Thread(target=_worker, daemon=True)
        t.start()


class RelayA(NostrRelay):
    def __init__(self):
        super().__init__(role="primary")


class RelayB(NostrRelay):
    def __init__(self, relay_a: RelayA):
        super().__init__(role="replica")
        self.replicate_from(relay_a)


class RelayC(NostrRelay):
    def __init__(self, relay_b: RelayB):
        super().__init__(role="redundant")
        self.replicate_from(relay_b)


class NostrPublisher:
    def __init__(self, relay_urls: List[str], min_acceptance: int = 1):
        self.relay_urls = relay_urls
        self.min_acceptance = min_acceptance
        self.max_retries = 3

    def publish_all(self, events) -> None:
        for event in events:
            self._publish_one(event)

    def _publish_one(self, event) -> None:
        accepted = 0
        payload = json.dumps(["EVENT", event if isinstance(event, dict) else event.__dict__]).encode()
        for url in self.relay_urls:
            try:
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=10):
                    accepted += 1
            except Exception:
                pass
        if accepted < self.min_acceptance:
            raise RuntimeError(f"only {accepted} relays accepted, need {self.min_acceptance}")

    def publish_revocation(self, event_id: str) -> None:
        revocation = NostrEvent(kind=KIND_REVOCATION, tags=[["e", event_id]], content="revoked", created_at=int(time.time()))
        self._publish_one(revocation)
