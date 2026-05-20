from __future__ import annotations
import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class ProbeResult:
    indexer_id: str
    query: str
    response: Any
    latency: float
    issued_at: float
    consistent: bool


class EvidenceStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._transcripts: List[ProbeResult] = []

    def record_transcript(self, result: ProbeResult):
        with self._lock:
            self._transcripts.append(result)

    def get_transcripts(self, indexer_id: str) -> List[ProbeResult]:
        with self._lock:
            return [t for t in self._transcripts if t.indexer_id == indexer_id]


class L2IndexerProtocol(Protocol):
    def query(self, req: Any) -> Any: ...
    def id(self) -> str: ...


class L2ProbeEngine:
    def __init__(self, indexers: List[L2IndexerProtocol], evidence_store: EvidenceStore, interval: float = 60.0):
        self._indexers = indexers
        self._evidence_store = evidence_store
        self._interval = interval

    def run(self):
        while True:
            time.sleep(self._interval)
            self._probe()

    def _probe(self):
        if not self._indexers:
            return
        selected = random.choice(self._indexers)
        query = self._random_query()
        start = time.time()
        try:
            resp = selected.query(query)
            consistent = True
        except Exception:
            resp = None
            consistent = False
        latency = time.time() - start
        result = ProbeResult(
            indexer_id=selected.id(),
            query=query,
            response=resp,
            latency=latency,
            issued_at=start,
            consistent=consistent,
        )
        self._evidence_store.record_transcript(result)

    def _random_query(self) -> str:
        return random.choice(["list_assets", "get_manifest", "query_by_tag"])


@dataclass
class L1Event:
    id: str
    kind: int
    pubkey: str
    created_at: int
    content: str


class GroundTruthDatabase:
    def __init__(self):
        self._lock = threading.RLock()
        self._events: List[L1Event] = []
        self._by_author: Dict[str, List[L1Event]] = {}
        self._by_asset: Dict[str, List[L1Event]] = {}

    def ingest(self, event: L1Event):
        with self._lock:
            self._events.append(event)
            self._by_author.setdefault(event.pubkey, []).append(event)
            self._by_asset.setdefault(event.id, []).append(event)

    def get_author_timeline(self, pubkey: str) -> List[L1Event]:
        with self._lock:
            return list(self._by_author.get(pubkey, []))

    def get_asset_history(self, asset_id: str) -> List[L1Event]:
        with self._lock:
            return list(self._by_asset.get(asset_id, []))


class L1RelaySourceProtocol(Protocol):
    def fetch_events(self, since: int) -> List[L1Event]: ...


class L1Scanner:
    def __init__(self, relays: List[L1RelaySourceProtocol], ground_truth: GroundTruthDatabase, interval: float = 30.0):
        self._relays = relays
        self._ground_truth = ground_truth
        self._interval = interval

    def run(self):
        last_scan = int(time.time())
        while True:
            time.sleep(self._interval)
            for relay in self._relays:
                try:
                    events = relay.fetch_events(last_scan)
                    for e in events:
                        self._ground_truth.ingest(e)
                except Exception:
                    pass
            last_scan = int(time.time())


@dataclass
class Verdict:
    indexer_id: str
    omissions: List[str] = field(default_factory=list)
    censored: List[str] = field(default_factory=list)
    equivocal: List[str] = field(default_factory=list)
    issued_at: float = field(default_factory=time.time)


class Comparator:
    def __init__(self, ground_truth: GroundTruthDatabase, evidence_store: EvidenceStore):
        self._ground_truth = ground_truth
        self._evidence_store = evidence_store

    def analyze(self, indexer_id: str) -> Verdict:
        transcripts = self._evidence_store.get_transcripts(indexer_id)
        verdict = Verdict(indexer_id=indexer_id)
        for t in transcripts:
            if not t.consistent:
                verdict.omissions.append(t.query)
        return verdict


@dataclass
class AuditReport:
    watchdog_key: str
    verdicts: List[Verdict]
    merkle_root: str
    sig: str
    issued_at: float = field(default_factory=time.time)


class ReportSigner:
    def __init__(self, identity_key: bytes):
        self._identity_key = identity_key

    def sign(self, verdicts: List[Verdict]) -> AuditReport:
        data = json.dumps([v.__dict__ for v in verdicts], default=str).encode()
        sig = hashlib.sha256(data + self._identity_key).hexdigest()
        return AuditReport(
            watchdog_key=hashlib.sha256(self._identity_key).hexdigest(),
            verdicts=verdicts,
            merkle_root=hashlib.sha256(data).hexdigest(),
            sig=sig,
        )


@dataclass
class ReputationScore:
    indexer_id: str
    score: float
    evidence: List[str]
    timestamps: List[float]
    published_at: float = field(default_factory=time.time)


class ReputationEventPublisher:
    def __init__(self, nostr_publisher):
        self._publisher = nostr_publisher

    def publish(self, score: ReputationScore):
        self._publisher.publish_all([score.__dict__])
