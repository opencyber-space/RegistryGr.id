import os
import io
import uuid
import json
import logging
import mimetypes
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

ASSETS_SERVER_URL = os.getenv("ASSETS_SERVER_URL", "http://34.68.117.250:30186")


def upload_policy_zip_bytes(
    file_bytes: bytes,
    filename: str,
    upload_endpoint: str = ASSETS_SERVER_URL,
    remote_path: str = "."
) -> Tuple[bool, str]:
 
    try:
        files = {
            "file": (filename, file_bytes, "application/zip"),
            "path": (None, remote_path)
        }
        response = requests.post(upload_endpoint + "/upload", files=files)

        response.raise_for_status()

        # Expecting JSON with uploaded URL
        result = response.json()
        code_url = result.get("url") or result.get("path") or response.text
        logger.info(f"Uploaded {filename} successfully to {code_url}")
        return True, code_url

    except Exception as e:
        logger.error(f"Upload failed for {filename}: {e}")
        return False, str(e)


class S3Uploader:
  

    def __init__(self, public_url_base: Optional[str] = ASSETS_SERVER_URL):
        self.public_url_base = public_url_base.rstrip("/")
        self.upload_endpoint = f"{self.public_url_base}/upload"

    def upload_file(self, local_file_path: str, s3_key: str) -> Optional[str]:
        try:
            if not os.path.exists(local_file_path):
                logger.error("Local file not found: %s", local_file_path)
                return None

            data = open(local_file_path, 'rb').read()

            return self.upload_bytes(data, s3_key, content_type="")

        except Exception as e:
            logger.error("Failed to upload file '%s' as '%s': %s", local_file_path, s3_key, e)
            return None

    def upload_bytes(self, data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> Optional[str]:
        try:
            filename = str(uuid.uuid4())
            full_zip_file_name = f"{filename}.zip"

            logger.info(f"zip file UUID: {filename}")

            ok, code_url_or_err = upload_policy_zip_bytes(
                file_bytes=data,
                filename=full_zip_file_name,
                upload_endpoint=ASSETS_SERVER_URL,
                remote_path='.',
            )

            if not ok:
                raise RuntimeError(f"Upload failed: {code_url_or_err}")

            code_url = code_url_or_err
            logger.info(f"Assets server code URL: {code_url}")
            
            return code_url

        except Exception as e:
            logger.error("Failed to upload bytes to '%s': %s", s3_key, e)
            return None
            

    def _split_key(self, key: str) -> Tuple[str, str]:
        key = (key or "").strip().lstrip("/")
        remote_path = os.path.dirname(key) or "."
        filename = os.path.basename(key) or "upload.bin"
        return remote_path, filename

    def _guess_mime_type(self, source_path: Optional[str] = None, filename: Optional[str] = None) -> str:
        if source_path:
            t, _ = mimetypes.guess_type(source_path)
            if t:
                return t
        if filename:
            t, _ = mimetypes.guess_type(filename)
            if t:
                return t
        return "application/octet-stream"

    def _extract_url(self, response: requests.Response, remote_path: str, filename: str) -> str:
        # Prefer JSON fields returned by the server; otherwise build a fallback URL
        try:
            data = response.json()
            if isinstance(data, dict):
                for k in ("url", "path"):
                    v = data.get(k)
                    if isinstance(v, str) and v.strip():
                        return v
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback to a constructed URL
        if remote_path == ".":
            return f"{self.public_url_base}/{filename}"
        return f"{self.public_url_base}/{remote_path.strip('/')}/{filename}"
