from __future__ import annotations
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol


@dataclass
class Event:
    id: str = ""
    pubkey: str = ""
    created_at: int = 0
    kind: int = 0
    content: str = ""
    sig: str = ""


@dataclass
class AssetRecord:
    id: str
    author_key: str
    manifest: str
    version: int
    tags: List[str] = field(default_factory=list)
    deleted: bool = False
    deleted_at: Optional[float] = None
    updated_at: float = field(default_factory=time.time)


class SignatureValidator:
    def validate(self, event: Event) -> bool:
        if not event.id or not event.pubkey or not event.sig:
            return False
        payload = json.dumps([0, event.pubkey, event.created_at, event.kind, [], event.content])
        expected = hashlib.sha256(payload.encode()).hexdigest()
        return expected == event.id

    def reject_malformed(self, event: Event) -> Optional[str]:
        if not event.id:
            return "missing id"
        if not event.pubkey:
            return "missing pubkey"
        if not event.sig:
            return "missing signature"
        return None


class WriteAheadLog:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._file = open(path, "a+", encoding="utf-8")
        self._seq = 0

    def log(self, event: Event):
        with self._lock:
            self._seq += 1
            entry = {"seq": self._seq, "event": event.__dict__}
            self._file.write(json.dumps(entry) + "\n")
            self._file.flush()

    def replay(self) -> List[dict]:
        with self._lock:
            self._file.seek(0)
            entries = []
            for line in self._file:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return entries

    def close(self):
        self._file.close()


class StateBuilder:
    def __init__(self, wal: WriteAheadLog):
        self._lock = threading.RLock()
        self._assets: Dict[str, AssetRecord] = {}
        self.wal = wal

    def apply(self, event: Event):
        self.wal.log(event)
        with self._lock:
            if event.kind == 30000:
                self._apply_asset(event)
            elif event.kind == 5:
                self._apply_deletion(event)

    def _apply_asset(self, event: Event):
        existing = self._assets.get(event.id)
        if existing and existing.version >= event.created_at:
            return
        self._assets[event.id] = AssetRecord(
            id=event.id,
            author_key=event.pubkey,
            manifest=event.content,
            version=event.created_at,
        )

    def _apply_deletion(self, event: Event):
        for record in self._assets.values():
            if record.author_key == event.pubkey:
                record.deleted = True
                record.deleted_at = time.time()

    def get_asset(self, asset_id: str) -> Optional[AssetRecord]:
        with self._lock:
            return self._assets.get(asset_id)

    def list_assets(self) -> List[AssetRecord]:
        with self._lock:
            return [r for r in self._assets.values() if not r.deleted]


class AggregatorDatabase:
    def __init__(self):
        self._lock = threading.RLock()
        self._assets: Dict[str, AssetRecord] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._schedulers: Dict[str, dict] = {}

    def persist_asset(self, record: AssetRecord):
        with self._lock:
            self._assets[record.id] = record
            for tag in record.tags:
                self._tag_index.setdefault(tag, []).append(record.id)

    def get_asset(self, asset_id: str) -> Optional[AssetRecord]:
        with self._lock:
            return self._assets.get(asset_id)

    def query_by_tag(self, tag: str) -> List[AssetRecord]:
        with self._lock:
            ids = self._tag_index.get(tag, [])
            return [self._assets[i] for i in ids if i in self._assets]

    def persist_scheduler(self, scheduler_id: str, info: dict):
        with self._lock:
            self._schedulers[scheduler_id] = info

    def list_schedulers(self) -> List[dict]:
        with self._lock:
            return list(self._schedulers.values())


class HotCache:
    def __init__(self, ttl: float = 60.0):
        self._lock = threading.RLock()
        self._store: Dict[str, tuple] = {}
        self.ttl = ttl
        t = threading.Thread(target=self._evict_loop, daemon=True)
        t.start()

    def set(self, key: str, value: Any):
        with self._lock:
            self._store[key] = (value, time.time() + self.ttl)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def _evict_loop(self):
        while True:
            time.sleep(self.ttl / 2)
            now = time.time()
            with self._lock:
                expired = [k for k, (_, exp) in self._store.items() if now > exp]
                for k in expired:
                    del self._store[k]


class RelayConsumer:
    def __init__(self, relays: list, replay_window: float = 300.0):
        self._relays = relays
        self._replay_window = replay_window
        self._seen: set = set()
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[Event], None]] = []

    def on_event(self, callback: Callable[[Event], None]):
        self._callbacks.append(callback)

    def start(self):
        since = time.time() - self._replay_window
        for relay in self._relays:
            t = threading.Thread(target=self._ingest, args=(relay, since), daemon=True)
            t.start()

    def _ingest(self, relay, since: float):
        try:
            for event in relay.stream_events(since):
                with self._lock:
                    if event.id in self._seen:
                        continue
                    self._seen.add(event.id)
                for cb in self._callbacks:
                    try:
                        cb(event)
                    except Exception:
                        pass
        except Exception:
            pass


@dataclass
class StateDelta:
    from_version: int
    to_version: int
    changes: List[AssetRecord]


class L2StateSynchronizer:
    def __init__(self, builder: StateBuilder, peers: list, interval: float = 30.0):
        self._builder = builder
        self._peers = peers
        self._interval = interval
        self._version = 0
        self._lock = threading.Lock()

    def run(self):
        while True:
            time.sleep(self._interval)
            self._sync()

    def _sync(self):
        with self._lock:
            current_version = self._version
        delta = StateDelta(
            from_version=current_version,
            to_version=current_version,
            changes=self._builder.list_assets(),
        )
        for peer in self._peers:
            try:
                remote_delta = peer.exchange_delta(delta)
                self._apply_delta(remote_delta)
            except Exception:
                pass

    def _apply_delta(self, delta: StateDelta):
        for record in delta.changes:
            self._builder.apply(Event(
                id=record.id,
                pubkey=record.author_key,
                created_at=record.version,
                kind=30000,
                content=record.manifest,
            ))
        with self._lock:
            if delta.to_version > self._version:
                self._version = delta.to_version


class CheckpointBuilder:
    def __init__(self, state_builder: StateBuilder):
        self._state_builder = state_builder

    def derive_root(self) -> str:
        assets = self._state_builder.list_assets()
        data = json.dumps([a.__dict__ for a in assets], sort_keys=True, default=str).encode()
        return hashlib.sha256(data).hexdigest()


@dataclass
class ThresholdSignature:
    indexer_id: str
    sig: str
    root: str
    signed_at: float = field(default_factory=time.time)


@dataclass
class CheckpointRecord:
    root: str
    epoch: int
    sigs: List[ThresholdSignature]
    created_at: float = field(default_factory=time.time)


class QuorumSigner:
    def __init__(self, threshold: int):
        self._threshold = threshold
        self._lock = threading.Lock()
        self._sigs: Dict[str, List[ThresholdSignature]] = {}

    def add_signature(self, root: str, sig: ThresholdSignature) -> bool:
        with self._lock:
            self._sigs.setdefault(root, []).append(sig)
            return len(self._sigs[root]) >= self._threshold

    def get_signatures(self, root: str) -> List[ThresholdSignature]:
        with self._lock:
            return list(self._sigs.get(root, []))


class CheckpointDatabase:
    def __init__(self):
        self._lock = threading.RLock()
        self._records: List[CheckpointRecord] = []

    def store(self, record: CheckpointRecord):
        with self._lock:
            self._records.append(record)

    def latest(self) -> Optional[CheckpointRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def get_by_epoch(self, epoch: int) -> Optional[CheckpointRecord]:
        with self._lock:
            for r in self._records:
                if r.epoch == epoch:
                    return r
            return None
