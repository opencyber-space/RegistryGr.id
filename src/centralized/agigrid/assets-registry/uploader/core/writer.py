import logging
import requests
from typing import Dict, IO, Any
from .zip_parser import StreamingZipParser
from .s3 import S3UploaderPlugin

logger = logging.getLogger("ZipUploadProcessor")
logger.setLevel(logging.INFO)

class ZipUploadProcessor:
    def __init__(self, s3_uploader: S3UploaderPlugin):
        self.s3_uploader = s3_uploader

    def process(self, zip_stream: IO[bytes]) -> Dict:
        
        parser = StreamingZipParser(zip_stream)
        file_urls = []

        for filename, file_obj in parser.parse():
            url = self.s3_uploader.upload_file(filename, file_obj)
            file_entry = {
                "asset_file_id": filename,
                "asset_file_type": "binary",  # or infer from filename
                "asset_file_mime_type": "application/octet-stream",  # optional improvement
                "asset_file_url": url
            }
            file_urls.append(file_entry)

        asset_metadata = parser.asset_metadata
        asset_metadata["files"] = file_urls

        logger.info("[ZipUploadProcessor] Finished processing ZIP and uploading assets.")
        return asset_metadata



class WriteAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def submit_asset(self, asset_metadata: Dict[str, Any]) -> Dict[str, Any]:
       
        url = f"{self.base_url}/assets"
        try:
            logger.info(f"[WriteAPIClient] Sending asset metadata to {url}")
            response = requests.post(url, json=asset_metadata)
            response.raise_for_status()
            logger.info("[WriteAPIClient] Asset metadata submission successful")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"[WriteAPIClient] Failed to submit asset metadata: {e}")
            return {"success": False, "error": str(e)}