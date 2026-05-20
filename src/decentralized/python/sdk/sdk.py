from __future__ import annotations
import hashlib
import json
import time
import math
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Protocol, runtime_checkable


CHUNK_SIZE = 4 * 1024 * 1024


@dataclass
class Chunk:
    index: int
    offset: int
    length: int
    data: bytes


@dataclass
class AssetEntry:
    index: int
    offset: int
    length: int
    hash: str


@dataclass
class Manifest:
    asset_id: str
    version: int
    merkle_root: str
    assets: List[AssetEntry]
    created_at: float = field(default_factory=time.time)


@dataclass
class Policy:
    propagation_intent: str = "public"
    distribution_scope: str = "global"
    ttl_seconds: int = 86400
    deletion_semantics: str = "tombstone"


@dataclass
class EncodedManifest:
    manifest: Manifest
    policy: Policy


@dataclass
class SignedEvent:
    id: str
    pubkey: str
    created_at: int
    kind: int
    content: str
    sig: str
    tags: List[List[str]] = field(default_factory=list)


@dataclass
class UploadState:
    asset_id: str
    completed_steps: dict = field(default_factory=dict)
    failed_step: Optional[str] = None
    chunks: List[Chunk] = field(default_factory=list)
    merkle_root: Optional[bytes] = None
    manifest: Optional[Manifest] = None
    encoded_manifest: Optional[EncodedManifest] = None
    signed_events: List[SignedEvent] = field(default_factory=list)


class Chunker:
    def __init__(self, chunk_size: int = CHUNK_SIZE):
        self.chunk_size = chunk_size

    def split(self, data: bytes) -> List[Chunk]:
        chunks = []
        offset = 0
        index = 0
        while offset < len(data):
            end = min(offset + self.chunk_size, len(data))
            chunk_data = data[offset:end]
            chunks.append(Chunk(index=index, offset=offset, length=len(chunk_data), data=chunk_data))
            offset = end
            index += 1
        return chunks

    def aligned_ranges(self, chunks: List[Chunk]) -> List[tuple]:
        return [(c.offset, c.offset + c.length - 1) for c in chunks]


class Hasher:
    def hash_chunk(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def compute_merkle_root(self, chunks: List[Chunk]) -> bytes:
        if not chunks:
            raise ValueError("no chunks")
        hashes = [self.hash_chunk(c.data) for c in chunks]
        return self._build_root(hashes)

    def _build_root(self, hashes: List[bytes]) -> bytes:
        if len(hashes) == 1:
            return hashes[0]
        if len(hashes) % 2 != 0:
            hashes = hashes + [hashes[-1]]
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined).digest())
        return self._build_root(next_level)

    def merkle_root_hex(self, chunks: List[Chunk]) -> str:
        return self.compute_merkle_root(chunks).hex()

    def chunk_hash_hex(self, data: bytes) -> str:
        return self.hash_chunk(data).hex()


_version_counter = 0
_version_lock = threading.Lock()


def _next_version() -> int:
    global _version_counter
    with _version_lock:
        _version_counter += 1
        return _version_counter


class ManifestBuilder:
    def __init__(self):
        self.hasher = Hasher()

    def build(self, chunks: List[Chunk], merkle_root: bytes) -> Manifest:
        entries = [
            AssetEntry(
                index=c.index,
                offset=c.offset,
                length=c.length,
                hash=self.hasher.chunk_hash_hex(c.data),
            )
            for c in chunks
        ]
        return Manifest(
            asset_id="",
            version=_next_version(),
            merkle_root=merkle_root.hex(),
            assets=entries,
        )


class PolicyEncoder:
    def encode(self, manifest: Manifest, policy: Policy) -> EncodedManifest:
        return EncodedManifest(manifest=manifest, policy=policy)


class Signer:
    def sign(self, encoded: EncodedManifest, priv_key: bytes) -> List[SignedEvent]:
        pub_key = self._derive_pubkey(priv_key)
        content = json.dumps({
            "manifest": encoded.manifest.__dict__,
            "policy": encoded.policy.__dict__,
        }, default=str)
        now = int(time.time())
        event_id = self._derive_id(pub_key, now, 30000, content)
        sig = self._sign_payload(event_id, priv_key)
        return [SignedEvent(
            id=event_id,
            pubkey=pub_key,
            created_at=now,
            kind=30000,
            content=content,
            sig=sig,
        )]

    def _derive_pubkey(self, priv_key: bytes) -> str:
        return hashlib.sha256(priv_key).hexdigest()

    def _derive_id(self, pub_key: str, created_at: int, kind: int, content: str) -> str:
        payload = json.dumps([0, pub_key, created_at, kind, [], content])
        return hashlib.sha256(payload.encode()).hexdigest()

    def _sign_payload(self, event_id: str, priv_key: bytes) -> str:
        return hashlib.sha256(priv_key + event_id.encode()).hexdigest()


@runtime_checkable
class NostrPublisherProtocol(Protocol):
    def publish_all(self, events: List[SignedEvent]) -> None: ...


@runtime_checkable
class OriginUploaderProtocol(Protocol):
    def upload(self, data: bytes, asset_id: str) -> None: ...


class SDKCore:
    def __init__(self, nostr_publisher: NostrPublisherProtocol, origin_uploader: OriginUploaderProtocol,
                 max_retries: int = 5, backoff_base: float = 1.0):
        self.chunker = Chunker()
        self.hasher = Hasher()
        self.manifest_builder = ManifestBuilder()
        self.policy_encoder = PolicyEncoder()
        self.signer = Signer()
        self.nostr_publisher = nostr_publisher
        self.origin_uploader = origin_uploader
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def upload(self, asset: bytes, policy: Policy, priv_key: bytes) -> None:
        state = UploadState(asset_id=hashlib.sha256(asset).hexdigest())
        steps = [
            ("chunk", lambda: self._run_chunk(asset, state)),
            ("hash", lambda: self._run_hash(state)),
            ("manifest", lambda: self._run_manifest(state, policy)),
            ("encode", lambda: self._run_encode(state, policy)),
            ("sign", lambda: self._run_sign(state, priv_key)),
            ("publish", lambda: self._run_publish(state)),
            ("upload", lambda: self._run_upload(asset, state)),
        ]
        for name, fn in steps:
            if state.completed_steps.get(name):
                continue
            self._with_retry(fn)
            state.completed_steps[name] = True

    def _with_retry(self, fn):
        last_err = None
        for i in range(self.max_retries):
            try:
                fn()
                return
            except Exception as e:
                last_err = e
                time.sleep(self.backoff_base * (2 ** i))
        raise last_err

    def _run_chunk(self, asset: bytes, state: UploadState):
        state.chunks = self.chunker.split(asset)

    def _run_hash(self, state: UploadState):
        state.merkle_root = self.hasher.compute_merkle_root(state.chunks)

    def _run_manifest(self, state: UploadState, policy: Policy):
        state.manifest = self.manifest_builder.build(state.chunks, state.merkle_root)

    def _run_encode(self, state: UploadState, policy: Policy):
        state.encoded_manifest = self.policy_encoder.encode(state.manifest, policy)

    def _run_sign(self, state: UploadState, priv_key: bytes):
        state.signed_events = self.signer.sign(state.encoded_manifest, priv_key)

    def _run_publish(self, state: UploadState):
        self.nostr_publisher.publish_all(state.signed_events)

    def _run_upload(self, asset: bytes, state: UploadState):
        self.origin_uploader.upload(asset, state.asset_id)
