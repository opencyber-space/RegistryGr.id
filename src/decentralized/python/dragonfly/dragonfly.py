from __future__ import annotations
import hashlib
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple


@dataclass
class Chunk:
    content_id: str
    index: int
    data: bytes
    hash: str


class OriginFetcher:
    def __init__(self, gateway_url: str):
        self._gateway_url = gateway_url

    def fetch_range(self, asset_id: str, start: int, end: int) -> bytes:
        url = f"{self._gateway_url}/object/{asset_id}"
        req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()


class DiskCache:
    def __init__(self, max_size: int = 10 * 1024 * 1024 * 1024):
        self._lock = threading.RLock()
        self._store: Dict[str, bytes] = {}
        self._max_size = max_size
        self._used = 0

    def store(self, key: str, data: bytes):
        with self._lock:
            if self._used + len(data) > self._max_size:
                self._evict(len(data))
            self._store[key] = data
            self._used += len(data)

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            return self._store.get(key)

    def evict(self, key: str):
        with self._lock:
            data = self._store.pop(key, None)
            if data:
                self._used -= len(data)

    def _evict(self, needed: int):
        for k in list(self._store.keys()):
            if self._max_size - self._used >= needed:
                break
            data = self._store.pop(k)
            self._used -= len(data)


class PieceServer:
    def __init__(self, cache: DiskCache):
        self._cache = cache

    def serve(self, key: str) -> Optional[bytes]:
        return self._cache.get(key)

    def make_wsgi_app(self):
        cache = self._cache

        def app(environ, start_response):
            path = environ.get("PATH_INFO", "")
            key = path.lstrip("/piece/")
            data = cache.get(key)
            if data is None:
                start_response("404 Not Found", [])
                return [b"not found"]
            start_response("200 OK", [("Content-Length", str(len(data)))])
            return [data]

        return app


class CacheGarbageCollector:
    def __init__(self, cache: DiskCache, interval: float = 60.0, max_size: int = 10 * 1024 * 1024 * 1024):
        self._cache = cache
        self._interval = interval
        self._max_size = max_size

    def run(self):
        while True:
            time.sleep(self._interval)
            self._collect()

    def _collect(self):
        with self._cache._lock:
            if self._cache._used < self._max_size:
                return
            excess = self._cache._used - self._max_size
            for k in list(self._cache._store.keys()):
                if excess <= 0:
                    break
                data = self._cache._store.pop(k)
                excess -= len(data)
                self._cache._used -= len(data)


class IntegrityVerifier:
    def verify(self, chunk: Chunk) -> bool:
        actual = hashlib.sha256(chunk.data).hexdigest()
        return actual == chunk.hash


class LocalCache:
    def __init__(self):
        self._lock = threading.RLock()
        self._store: Dict[str, Chunk] = {}

    def write(self, chunk: Chunk):
        key = f"{chunk.content_id}:{chunk.index}"
        with self._lock:
            self._store[key] = chunk

    def read(self, content_id: str, index: int) -> Optional[Chunk]:
        key = f"{content_id}:{index}"
        with self._lock:
            return self._store.get(key)


class PeerSourceProtocol(Protocol):
    def fetch_chunk(self, content_id: str, index: int) -> Chunk: ...


class PieceDownloader:
    def __init__(self, peers: List[PeerSourceProtocol], verifier: IntegrityVerifier, local_cache: LocalCache):
        self._peers = peers
        self._verifier = verifier
        self._local_cache = local_cache

    def download(self, content_id: str, index: int) -> Chunk:
        cached = self._local_cache.read(content_id, index)
        if cached:
            return cached
        for peer in self._peers:
            try:
                chunk = peer.fetch_chunk(content_id, index)
                if self._verifier.verify(chunk):
                    self._local_cache.write(chunk)
                    return chunk
            except Exception:
                continue
        raise RuntimeError(f"no peer could serve chunk {content_id}:{index}")


class PeerSinkProtocol(Protocol):
    def send_chunk(self, chunk: Chunk): ...
    def id(self) -> str: ...


class PieceUploader:
    def __init__(self, peers: List[PeerSinkProtocol]):
        self._peers = peers

    def redistribute(self, chunk: Chunk):
        for peer in self._peers:
            t = threading.Thread(target=self._send, args=(peer, chunk), daemon=True)
            t.start()

    def _send(self, peer: PeerSinkProtocol, chunk: Chunk):
        try:
            peer.send_chunk(chunk)
        except Exception:
            pass


class RetryEngine:
    def __init__(self, downloader: PieceDownloader, max_retries: int = 3, backoff: float = 1.0):
        self._downloader = downloader
        self._max_retries = max_retries
        self._backoff = backoff

    def download(self, content_id: str, index: int) -> Chunk:
        last_err = None
        for i in range(self._max_retries):
            try:
                return self._downloader.download(content_id, index)
            except Exception as e:
                last_err = e
                time.sleep(self._backoff * (i + 1))
        raise RuntimeError(f"max retries exceeded: {last_err}")
