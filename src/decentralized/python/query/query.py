from __future__ import annotations
import hashlib
import json
import math
import random
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol


@dataclass
class QueryRequest:
    asset_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    author_id: Optional[str] = None
    limit: int = 50


@dataclass
class AssetResult:
    id: str
    manifest: str
    version: int


@dataclass
class QueryResponse:
    assets: List[AssetResult] = field(default_factory=list)
    merkle_proof: List[str] = field(default_factory=list)
    signature: str = ""
    transcript: str = ""


class AssetStoreProtocol(Protocol):
    def get_asset(self, asset_id: str) -> Optional[Any]: ...
    def query_by_tag(self, tag: str) -> List[Any]: ...
    def list_assets(self) -> List[Any]: ...


class CacheProtocol(Protocol):
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any): ...


class QueryAPI:
    def __init__(self, store: AssetStoreProtocol, cache: CacheProtocol, signing_key: bytes):
        self.store = store
        self.cache = cache
        self.signing_key = signing_key

    def handle(self, raw: bytes) -> bytes:
        req = QueryRequest(**json.loads(raw))
        resp = self._execute(req)
        resp.signature = self._sign(resp)
        return json.dumps(resp.__dict__, default=list).encode()

    def _execute(self, req: QueryRequest) -> QueryResponse:
        cache_key = self._cache_key(req)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        results = []
        if req.asset_id:
            asset = self.store.get_asset(req.asset_id)
            if asset:
                results.append(AssetResult(id=asset.id, manifest=asset.manifest, version=asset.version))
        for tag in req.tags:
            for asset in self.store.query_by_tag(tag):
                results.append(AssetResult(id=asset.id, manifest=asset.manifest, version=asset.version))
        resp = QueryResponse(
            assets=results,
            transcript=json.dumps({"request": req.__dict__, "count": len(results), "ts": int(time.time())}),
        )
        self.cache.set(cache_key, resp)
        return resp

    def _sign(self, resp: QueryResponse) -> str:
        data = json.dumps([a.__dict__ for a in resp.assets], sort_keys=True).encode()
        return hashlib.sha256(data + self.signing_key).hexdigest()

    def _cache_key(self, req: QueryRequest) -> str:
        data = json.dumps(req.__dict__, sort_keys=True).encode()
        return hashlib.sha256(data).hexdigest()


class Resolver:
    def __init__(self, indexers: list):
        self._lock = threading.RLock()
        self._indexers = list(indexers)

    def select_quorum(self, req: QueryRequest):
        with self._lock:
            pool = list(self._indexers)
        random.shuffle(pool)
        quorum_size = (len(pool) // 2) + 1
        return pool[:quorum_size], quorum_size

    def add_indexer(self, indexer):
        with self._lock:
            self._indexers.append(indexer)

    def remove_indexer(self, indexer_id: str):
        with self._lock:
            self._indexers = [ix for ix in self._indexers if ix.id() != indexer_id]


class Verifier:
    def verify_author_signature(self, resp: QueryResponse, pub_key: str) -> bool:
        return bool(resp.signature)

    def verify_merkle_proof(self, asset_id: str, proof: List[str], root: str) -> bool:
        if not proof:
            return False
        current = asset_id
        for sibling in proof:
            combined = current + sibling
            current = hashlib.sha256(combined.encode()).hexdigest()
        return current == root

    def verify_l2_signature(self, resp: QueryResponse, checkpoint_root: str) -> bool:
        return bool(resp.signature)

    def verify_all(self, resp: QueryResponse, pub_key: str, checkpoint_root: str = "") -> bool:
        if not self.verify_author_signature(resp, pub_key):
            return False
        if checkpoint_root and resp.merkle_proof:
            for asset in resp.assets:
                if not self.verify_merkle_proof(asset.id, resp.merkle_proof, checkpoint_root):
                    return False
        return self.verify_l2_signature(resp, checkpoint_root)


class ResultUnion:
    def merge(self, responses: List[QueryResponse]) -> QueryResponse:
        seen: Dict[str, AssetResult] = {}
        for resp in responses:
            for asset in resp.assets:
                existing = seen.get(asset.id)
                if not existing or asset.version > existing.version:
                    seen[asset.id] = asset
        merged = sorted(seen.values(), key=lambda a: a.version, reverse=True)
        return QueryResponse(assets=merged)


@dataclass
class WatchdogReport:
    indexer_id: str
    score: float
    issued_at: float = field(default_factory=time.time)


class ReputationFilter:
    def __init__(self, decay_rate: float = 0.01):
        self.decay_rate = decay_rate
        self._lock = threading.Lock()
        self._reports: Dict[str, List[WatchdogReport]] = {}

    def add_report(self, report: WatchdogReport):
        with self._lock:
            self._reports.setdefault(report.indexer_id, []).append(report)

    def score(self, indexer_id: str) -> float:
        with self._lock:
            reports = self._reports.get(indexer_id, [])
        if not reports:
            return 1.0
        now = time.time()
        weighted_sum = 0.0
        total_weight = 0.0
        for r in reports:
            age_hours = (now - r.issued_at) / 3600.0
            weight = math.exp(-self.decay_rate * age_hours)
            weighted_sum += r.score * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 1.0

    def filter(self, assets: List[AssetResult], min_score: float = 0.5) -> List[AssetResult]:
        return assets


class FallbackReader:
    def __init__(self, l1_relays: list):
        self._relays = l1_relays

    def read(self, req: QueryRequest) -> QueryResponse:
        last_err = None
        for relay in self._relays:
            try:
                return relay.query(req)
            except Exception as e:
                last_err = e
        raise RuntimeError(f"no l1 relay available: {last_err}")
