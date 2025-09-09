import logging
import requests
from typing import Dict, Any, Optional
import zipfile
import io
from typing import Generator, Tuple, IO


logger = logging.getLogger("ReadAPIClient")
logger.setLevel(logging.INFO)

class ReadAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def fetch_asset_metadata(self, asset_id: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/assets/{asset_id}"
            logger.info(f"[ReadAPIClient] Fetching metadata: {url}")
            response = requests.get(url)
            response.raise_for_status()
            return response.json().get("asset")
        except Exception as e:
            logger.error(f"[ReadAPIClient] Failed to fetch asset {asset_id}: {e}")
            return None


class StreamingZipArchiver:
    def __init__(self):
        self.buffer = io.BytesIO()

    def archive(self, files: Generator[Tuple[str, IO[bytes]], None, None]) -> Generator[bytes, None, None]:
        with zipfile.ZipFile(self.buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for filename, file_obj in files:
                zf.writestr(filename, file_obj.read())

        self.buffer.seek(0)
        while chunk := self.buffer.read(8192):
            yield chunk