import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("AssetsDBService")
logger.setLevel(logging.INFO)

class AssetsDBService:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def create_asset(self, asset_payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.post(f"{self.base_url}/assets", json=asset_payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"[create_asset] Request failed: {e}")
            return {"success": False, "error": str(e)}

    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}/assets/{asset_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"[get_asset] Request failed: {e}")
            return {"success": False, "error": str(e)}

    def update_asset(self, asset_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.put(f"{self.base_url}/assets/{asset_id}", json=update_data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"[update_asset] Request failed: {e}")
            return {"success": False, "error": str(e)}

    def delete_asset(self, asset_id: str) -> Dict[str, Any]:
        try:
            response = requests.delete(f"{self.base_url}/assets/{asset_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"[delete_asset] Request failed: {e}")
            return {"success": False, "error": str(e)}
