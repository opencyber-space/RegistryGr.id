import logging
from typing import Optional, Dict, Any
from pymongo import MongoClient, errors
from pymongo.collection import Collection
from .schema import Asset

logger = logging.getLogger("AssetDB")
logger.setLevel(logging.INFO)

class AssetDB:
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "asset_system",
        collection_name: str = "assets",
        external_client: Optional[MongoClient] = None,
    ):
        try:
            self.client = external_client or MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection: Collection = self.db[collection_name]
            logger.info(f"[AssetDB] Connected to MongoDB: {mongo_uri}, DB: {db_name}, Collection: {collection_name}")
        except errors.PyMongoError as e:
            logger.error(f"[AssetDB] Failed to connect to MongoDB: {e}")
            raise

    def insert(self, asset: Asset) -> bool:
        try:
            self.collection.insert_one(asset.to_dict())
            logger.info(f"[AssetDB] Inserted asset: {asset.asset_id}")
            return True
        except errors.PyMongoError as e:
            logger.error(f"[AssetDB] Insert failed for asset {asset.asset_id}: {e}")
            return False

    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        try:
            doc = self.collection.find_one({"asset_id": asset_id})
            if doc:
                logger.info(f"[AssetDB] Found asset: {asset_id}")
                return Asset.from_dict(doc)
            logger.warning(f"[AssetDB] Asset not found: {asset_id}")
            return None
        except errors.PyMongoError as e:
            logger.error(f"[AssetDB] Error retrieving asset {asset_id}: {e}")
            return None

    def update(self, asset_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            result = self.collection.update_one({"asset_id": asset_id}, {"$set": update_data})
            if result.matched_count == 0:
                logger.warning(f"[AssetDB] Update failed, no asset found: {asset_id}")
                return False
            logger.info(f"[AssetDB] Updated asset: {asset_id}")
            return True
        except errors.PyMongoError as e:
            logger.error(f"[AssetDB] Update failed for asset {asset_id}: {e}")
            return False

    def delete_by_id(self, asset_id: str) -> bool:
        try:
            result = self.collection.delete_one({"asset_id": asset_id})
            if result.deleted_count == 0:
                logger.warning(f"[AssetDB] Delete failed, no asset found: {asset_id}")
                return False
            logger.info(f"[AssetDB] Deleted asset: {asset_id}")
            return True
        except errors.PyMongoError as e:
            logger.error(f"[AssetDB] Delete failed for asset {asset_id}: {e}")
            return False
