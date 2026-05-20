from __future__ import annotations
import hashlib
import json
import math
import random
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class ConsistentHashEngine:
    def __init__(self, vnodes: int = 150):
        self._vnodes = vnodes
        self._lock = threading.RLock()
        self._ring: List[Tuple[int, str]] = []

    def add_scheduler(self, scheduler_id: str):
        with self._lock:
            for i in range(self._vnodes):
                key = f"{scheduler_id}{i}".encode()
                h = struct.unpack(">Q", hashlib.sha256(key).digest()[:8])[0]
                self._ring.append((h, scheduler_id))
            self._ring.sort(key=lambda x: x[0])

    def assign(self, content_id: str) -> Optional[str]:
        with self._lock:
            if not self._ring:
                return None
            h = struct.unpack(">Q", hashlib.sha256(content_id.encode()).digest()[:8])[0]
            for ring_hash, scheduler_id in self._ring:
                if ring_hash >= h:
                    return scheduler_id
            return self._ring[0][1]


@dataclass
class HealthStatus:
    scheduler_id: str
    alive: bool
    rtt: float
    checked_at: float = field(default_factory=time.time)


class SchedulerHealthMonitor:
    def __init__(self, interval: float = 10.0):
        self._lock = threading.RLock()
        self._statuses: Dict[str, HealthStatus] = {}
        self._probers = []
        self._interval = interval

    def add_prober(self, prober):
        self._probers.append(prober)

    def run(self):
        while True:
            time.sleep(self._interval)
            for prober in self._probers:
                start = time.time()
                try:
                    prober.probe()
                    rtt = time.time() - start
                    alive = True
                except Exception:
                    rtt = 0.0
                    alive = False
                status = HealthStatus(scheduler_id=prober.id(), alive=alive, rtt=rtt)
                with self._lock:
                    self._statuses[prober.id()] = status

    def is_alive(self, scheduler_id: str) -> bool:
        with self._lock:
            s = self._statuses.get(scheduler_id)
            return s.alive if s else False


class DecisionCache:
    def __init__(self, ttl: float = 300.0):
        self._lock = threading.RLock()
        self._store: Dict[str, Tuple[str, float]] = {}
        self._ttl = ttl

    def set(self, content_id: str, scheduler_id: str):
        with self._lock:
            self._store[content_id] = (scheduler_id, time.time() + self._ttl)

    def get(self, content_id: str) -> Optional[str]:
        with self._lock:
            entry = self._store.get(content_id)
            if entry is None:
                return None
            scheduler_id, expires_at = entry
            if time.time() > expires_at:
                del self._store[content_id]
                return None
            return scheduler_id


class Bridge:
    def __init__(self):
        self._lock = threading.RLock()
        self._global_state: Dict[str, Any] = {}

    def update_global_state(self, key: str, value: Any):
        with self._lock:
            self._global_state[key] = value

    def get_state(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._global_state.get(key)

    def expose_control_api(self) -> dict:
        with self._lock:
            return dict(self._global_state)


class ManagerAPIFacade:
    def __init__(self, hash_engine: ConsistentHashEngine, decision_cache: DecisionCache,
                 health_monitor: SchedulerHealthMonitor, bridge: Bridge):
        self._hash_engine = hash_engine
        self._decision_cache = decision_cache
        self._health_monitor = health_monitor
        self._bridge = bridge

    def select_scheduler(self, content_id: str) -> Optional[str]:
        cached = self._decision_cache.get(content_id)
        if cached and self._health_monitor.is_alive(cached):
            return cached
        selected = self._hash_engine.assign(content_id)
        if selected:
            self._decision_cache.set(content_id, selected)
        return selected

    def preheat(self, content_id: str):
        pass

    def keepalive(self, scheduler_id: str):
        pass


@dataclass
class TaskSpec:
    content_id: str
    scheduler_id: str
    intent: str
    scope: str
    ttl: float


class PolicyEngine:
    def evaluate(self, spec: TaskSpec) -> bool:
        if spec.ttl <= 0:
            return False
        if not spec.intent:
            return False
        return True


@dataclass
class Task:
    id: str
    content_id: str
    scheduler_id: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0


class TaskOrchestrator:
    def __init__(self):
        self._lock = threading.RLock()
        self._tasks: Dict[str, Task] = {}
        self._preheat: set = set()

    def create_task(self, task: Task):
        with self._lock:
            self._tasks[task.id] = task

    def invalidate_task(self, task_id: str):
        with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.status = "invalidated"

    def reconcile_preheat(self, content_id: str):
        with self._lock:
            self._preheat.add(content_id)

    def reconcile_eviction(self, content_id: str):
        with self._lock:
            self._preheat.discard(content_id)


@dataclass
class PlacementRequest:
    content_id: str
    peer_id: str
    priority: int = 0


@dataclass
class PlacementResponse:
    scheduler_id: str
    peer_id: str


class SchedulerAPI:
    def __init__(self, facade: ManagerAPIFacade, task_manager: "TaskManager"):
        self._facade = facade
        self._task_manager = task_manager

    def handle_placement(self, req: PlacementRequest) -> PlacementResponse:
        scheduler_id = self._facade.select_scheduler(req.content_id) or ""
        return PlacementResponse(scheduler_id=scheduler_id, peer_id=req.peer_id)


@dataclass
class TaskState:
    id: str
    content_id: str
    status: str = "pending"
    ttl: float = 3600.0
    created_at: float = field(default_factory=time.time)


class TaskManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._tasks: Dict[str, TaskState] = {}

    def track(self, task: TaskState):
        with self._lock:
            self._tasks[task.id] = task

    def expire(self):
        now = time.time()
        with self._lock:
            expired = [tid for tid, t in self._tasks.items() if now > t.created_at + t.ttl]
            for tid in expired:
                self._tasks[tid].status = "expired"
                del self._tasks[tid]

    def get(self, task_id: str) -> Optional[TaskState]:
        with self._lock:
            return self._tasks.get(task_id)


@dataclass
class PeerEntry:
    id: str
    addr: str
    score: float = 1.0
    last_seen: float = field(default_factory=time.time)


class PeerManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._peers: Dict[str, PeerEntry] = {}

    def register(self, peer: PeerEntry):
        with self._lock:
            self._peers[peer.id] = peer

    def update_score(self, peer_id: str, score: float):
        with self._lock:
            p = self._peers.get(peer_id)
            if p:
                p.score = score

    def best_peers(self, n: int) -> List[PeerEntry]:
        with self._lock:
            peers = sorted(self._peers.values(), key=lambda p: p.score, reverse=True)
            return peers[:n]


@dataclass
class PieceEntry:
    content_id: str
    chunk_idx: int
    hash: str
    available: bool = True
    peer_ids: List[str] = field(default_factory=list)


class PieceManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._pieces: Dict[str, PieceEntry] = {}

    def register(self, piece: PieceEntry):
        key = f"{piece.content_id}:{piece.chunk_idx}"
        with self._lock:
            self._pieces[key] = piece

    def validate_checksum(self, content_id: str, idx: int, expected_hash: str) -> bool:
        key = f"{content_id}:{idx}"
        with self._lock:
            p = self._pieces.get(key)
            return p is not None and p.hash == expected_hash


class TopologyBuilder:
    def __init__(self, fan_out: int = 3):
        self._fan_out = fan_out

    def build(self, peer_ids: List[str]) -> Dict[str, List[str]]:
        tree: Dict[str, List[str]] = {pid: [] for pid in peer_ids}
        for i, pid in enumerate(peer_ids):
            start = i * self._fan_out + 1
            for j in range(start, min(start + self._fan_out, len(peer_ids))):
                tree[pid].append(peer_ids[j])
        return tree


class LoadController:
    def __init__(self):
        self._lock = threading.RLock()
        self._limits: Dict[str, int] = {}
        self._counters: Dict[str, int] = {}

    def set_limit(self, peer_id: str, limit: int):
        with self._lock:
            self._limits[peer_id] = limit
            self._counters[peer_id] = 0

    def allow(self, peer_id: str) -> bool:
        with self._lock:
            limit = self._limits.get(peer_id)
            if limit is None:
                return True
            current = self._counters.get(peer_id, 0)
            if current >= limit:
                return False
            self._counters[peer_id] = current + 1
            return True


class FailureHandler:
    def __init__(self, task_manager: TaskManager, peer_manager: PeerManager):
        self._task_manager = task_manager
        self._peer_manager = peer_manager

    def handle(self, task_id: str, error: Exception):
        task = self._task_manager.get(task_id)
        if task:
            task.status = "failed"
            self._task_manager.track(task)

    def repair_distribution(self, content_id: str):
        pass


@dataclass
class MetricsSnapshot:
    latency: float
    throughput: float
    cache_hits: int
    cache_misses: int
    timestamp: float = field(default_factory=time.time)


class MetricsExporter:
    def __init__(self):
        self._lock = threading.Lock()
        self._latency: float = 0.0
        self._hits: int = 0
        self._misses: int = 0
        self._bytes: int = 0
        self._snapshots: List[MetricsSnapshot] = []

    def record_latency(self, d: float):
        with self._lock:
            self._latency = d

    def record_cache_hit(self):
        with self._lock:
            self._hits += 1

    def record_cache_miss(self):
        with self._lock:
            self._misses += 1

    def record_bytes(self, n: int):
        with self._lock:
            self._bytes += n

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(
                latency=self._latency,
                throughput=float(self._bytes),
                cache_hits=self._hits,
                cache_misses=self._misses,
            )

    def publish(self):
        snap = self.snapshot()
        with self._lock:
            self._snapshots.append(snap)
