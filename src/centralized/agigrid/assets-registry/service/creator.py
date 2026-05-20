import logging
from typing import Dict, Any, Tuple
from .db import AssetDB
from .parser import SpecParser
from .schema import Asset

logger = logging.getLogger("AssetCreator")
logger.setLevel(logging.INFO)

class AssetCreator:
    def __init__(self, db: AssetDB):
        self.db = db

    def create_asset(self, json_payload: Dict[str, Any]) -> Tuple[bool, str]:
        logger.info("[AssetCreator] Starting asset creation process")

        asset, error = SpecParser.parse_spec(json_payload)
        if error:
            logger.error(f"[AssetCreator] Spec validation failed: {error}")
            return False, error

        # Optional: check for duplication before insert
        existing = self.db.find_by_id(asset.asset_id)
        if existing:
            msg = f"Asset with ID '{asset.asset_id}' already exists"
            logger.warning(f"[AssetCreator] {msg}")
            return False, msg

        success = self.db.insert(asset)
        if success:
            logger.info(f"[AssetCreator] Asset {asset.asset_id} successfully inserted")
            return True, f"Asset '{asset.asset_id}' inserted successfully"
        else:
            logger.error(f"[AssetCreator] Asset insert failed for {asset.asset_id}")
            return False, f"Asset '{asset.asset_id}' insert failed due to DB error"
