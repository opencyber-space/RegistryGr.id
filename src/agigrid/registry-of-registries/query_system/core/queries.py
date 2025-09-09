import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import List, Dict, Any, Optional

# Configure logger
logger = logging.getLogger("QuerySystem")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class QuerySystem:
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017",
        db_name: str = "registry_system",
        collection_name: str = "registry_core_data"
    ):
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            logger.info(
                f"Connected to MongoDB: {mongo_uri}/{db_name}.{collection_name}")
        except Exception as e:
            logger.exception("Failed to connect to MongoDB")
            raise RuntimeError("MongoDB connection error") from e

    def get_by_id(self, registry_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.collection.find_one({"registry_id": registry_id})
            logger.info(f"get_by_id({registry_id}) -> found: {bool(result)}")
            return result
        except PyMongoError as e:
            logger.exception("get_by_id failed")
            raise RuntimeError("Query failed") from e

    def find_by_url(self, url_fragment: str) -> List[Dict[str, Any]]:
        try:
            query = {"registry_url": {"$regex": url_fragment, "$options": "i"}}
            results = list(self.collection.find(query))
            logger.info(
                f"find_by_url('{url_fragment}') -> {len(results)} results")
            return results
        except PyMongoError as e:
            logger.exception("find_by_url failed")
            raise RuntimeError("Query failed") from e

    def find_by_type(self, registry_type: str) -> List[Dict[str, Any]]:
        try:
            query = {"registry_search_data.registry_type": registry_type}
            results = list(self.collection.find(query))
            logger.info(
                f"find_by_type('{registry_type}') -> {len(results)} results")
            return results
        except PyMongoError as e:
            logger.exception("find_by_type failed")
            raise RuntimeError("Query failed") from e

    def find_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        try:
            query = {"registry_search_data.registry_search_tags": {"$in": tags}}
            results = list(self.collection.find(query))
            logger.info(f"find_by_tags({tags}) -> {len(results)} results")
            return results
        except PyMongoError as e:
            logger.exception("find_by_tags failed")
            raise RuntimeError("Query failed") from e

    def find_by_partial(self, field: str, fragment: str) -> List[Dict[str, Any]]:
        try:
            query = {field: {"$regex": fragment, "$options": "i"}}
            results = list(self.collection.find(query))
            logger.info(
                f"find_by_partial('{field}', '{fragment}') -> {len(results)} results")
            return results
        except PyMongoError as e:
            logger.exception("find_by_partial failed")
            raise RuntimeError("Query failed") from e

    def query(self, mongo_filter: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        try:
            results = list(self.collection.find(mongo_filter).limit(limit))
            logger.info(f"query({mongo_filter}) -> {len(results)} results")
            return results
        except PyMongoError as e:
            logger.exception("query failed")
            raise RuntimeError("Generic query failed") from e
