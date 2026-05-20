from __future__ import annotations
import hashlib
import json
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from http.server import BaseHTTPRequestHandler, HTTPServer


@dataclass
class ObjectMeta:
    asset_id: str
    checksum: str
    byte_size: int
    modified_at: float
    verified: bool


class MetadataDatabase:
    def __init__(self):
        self._lock = threading.RLock()
        self._records: Dict[str, ObjectMeta] = {}

    def record(self, asset_id: str, data: bytes):
        checksum = hashlib.sha256(data).hexdigest()
        meta = ObjectMeta(
            asset_id=asset_id,
            checksum=checksum,
            byte_size=len(data),
            modified_at=time.time(),
            verified=True,
        )
        with self._lock:
            self._records[asset_id] = meta

    def get(self, asset_id: str) -> Optional[ObjectMeta]:
        with self._lock:
            return self._records.get(asset_id)

    def verify(self, asset_id: str, data: bytes) -> bool:
        meta = self.get(asset_id)
        if not meta:
            return False
        return hashlib.sha256(data).hexdigest() == meta.checksum


class ObjectGateway:
    def __init__(self, meta_db: MetadataDatabase):
        self._lock = threading.RLock()
        self._objects: Dict[str, bytes] = {}
        self.meta_db = meta_db

    def store(self, asset_id: str, data: bytes):
        with self._lock:
            self._objects[asset_id] = data
        self.meta_db.record(asset_id, data)

    def get(self, asset_id: str) -> Optional[bytes]:
        with self._lock:
            return self._objects.get(asset_id)

    def serve_range(self, asset_id: str, start: int, end: int) -> Optional[bytes]:
        data = self.get(asset_id)
        if data is None:
            return None
        return data[start:end + 1]

    def make_handler(self):
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parts = self.path.strip("/").split("/")
                if len(parts) < 2:
                    self.send_response(400)
                    self.end_headers()
                    return
                asset_id = parts[1]
                data = gateway.get(asset_id)
                if data is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                range_header = self.headers.get("Range")
                if range_header:
                    start, end = parse_range(range_header, len(data))
                    body = data[start:end + 1]
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            def log_message(self, fmt, *args):
                pass

        return Handler


def parse_range(header: str, size: int) -> Tuple[int, int]:
    header = header.replace("bytes=", "")
    parts = header.split("-")
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if parts[1] else size - 1
    return start, end


class OriginUploader:
    def __init__(self, gateway_url: str, chunk_size: int = 4 * 1024 * 1024):
        self.gateway_url = gateway_url
        self.chunk_size = chunk_size

    def upload(self, data: bytes, asset_id: str):
        total = len(data)
        offset = 0
        while offset < total:
            end = min(offset + self.chunk_size, total)
            chunk = data[offset:end]
            self._upload_chunk(asset_id, offset, total - 1, chunk)
            offset = end
        self._commit(asset_id)

    def _upload_chunk(self, asset_id: str, start: int, end: int, data: bytes):
        url = f"{self.gateway_url}/upload/{asset_id}"
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Range": f"bytes {start}-{start + len(data) - 1}/*",
                "Content-Length": str(len(data)),
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError("chunk upload failed")

    def _commit(self, asset_id: str):
        url = f"{self.gateway_url}/upload/{asset_id}/commit"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError("commit failed")
