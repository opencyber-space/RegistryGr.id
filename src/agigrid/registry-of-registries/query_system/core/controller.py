import logging
from typing import Dict, Any, List, Optional
from query_system import QuerySystem

logger = logging.getLogger("QueryController")
logger.setLevel(logging.INFO)

class QueryController:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017"):
        try:
            self.query_system = QuerySystem(mongo_uri=mongo_uri)
            logger.info("QueryController initialized successfully")
        except Exception as e:
            logger.exception("Failed to initialize QuerySystem")
            raise

    def get_registry_by_id(self, registry_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.query_system.get_by_id(registry_id)
        except Exception as e:
            logger.exception(f"get_registry_by_id failed for '{registry_id}'")
            raise

    def find_registries_by_type(self, registry_type: str) -> List[Dict[str, Any]]:
        try:
            return self.query_system.find_by_type(registry_type)
        except Exception as e:
            logger.exception(f"find_registries_by_type failed for '{registry_type}'")
            raise

    def find_registries_by_url(self, url_fragment: str) -> List[Dict[str, Any]]:
        try:
            return self.query_system.find_by_url(url_fragment)
        except Exception as e:
            logger.exception(f"find_registries_by_url failed for '{url_fragment}'")
            raise

    def find_registries_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        try:
            return self.query_system.find_by_tags(tags)
        except Exception as e:
            logger.exception(f"find_registries_by_tags failed for {tags}")
            raise

    def find_partial_match(self, field: str, fragment: str) -> List[Dict[str, Any]]:
        try:
            return self.query_system.find_by_partial(field, fragment)
        except Exception as e:
            logger.exception(f"find_partial_match failed for {field} ~ {fragment}")
            raise

  
    def query_raw(self, mongo_filter: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        try:
            return self.query_system.query(mongo_filter, limit=limit)
        except Exception as e:
            logger.exception(f"query_raw failed for filter: {mongo_filter}")
            raise
