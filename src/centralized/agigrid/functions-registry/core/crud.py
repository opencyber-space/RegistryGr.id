import logging
import os
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from .schema import FunctionEntry

# Setup logger
logger = logging.getLogger("FunctionsRegistryCRUD")
logger.setLevel(logging.INFO)

class FunctionsRegistryCRUD:
    mongo_uri: str
    db_name: str = "functions_registry"
    collection_name: str = "functions"

    def __init__(self):
        try:
            self.mongo_uri = os.getenv("MONGO_URL")
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection: Collection = self.db[self.collection_name]
            logger.info(f"Connected to MongoDB: {self.mongo_uri}, DB: {self.db_name}, Collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    def create_function(self, function: FunctionEntry) -> bool:
        try:
            if self.collection.find_one({"function_id": function.function_id}):
                logger.warning(f"Function with ID '{function.function_id}' already exists.")
                return False
            self.collection.insert_one(function.to_dict())
            logger.info(f"Function '{function.function_id}' inserted successfully.")
            return True
        except PyMongoError as e:
            logger.error(f"Failed to insert function '{function.function_id}': {e}")
            return False

    def get_function(self, function_id: str) -> Optional[FunctionEntry]:
        try:
            doc = self.collection.find_one({"function_id": function_id})
            if doc:
                logger.info(f"Function '{function_id}' retrieved successfully.")
                return FunctionEntry.from_dict(doc)
            logger.warning(f"Function '{function_id}' not found.")
            return None
        except PyMongoError as e:
            logger.error(f"Failed to retrieve function '{function_id}': {e}")
            return None

    def update_function(self, function_id: str, updates: Dict[str, Any]) -> bool:
        try:
            result = self.collection.update_one({"function_id": function_id}, {"$set": updates})
            if result.matched_count:
                logger.info(f"Function '{function_id}' updated successfully.")
                return True
            else:
                logger.warning(f"Function '{function_id}' not found for update.")
                return False
        except PyMongoError as e:
            logger.error(f"Failed to update function '{function_id}': {e}")
            return False

    def delete_function(self, function_id: str) -> bool:
        try:
            result = self.collection.delete_one({"function_id": function_id})
            if result.deleted_count:
                logger.info(f"Function '{function_id}' deleted successfully.")
                return True
            else:
                logger.warning(f"Function '{function_id}' not found for deletion.")
                return False
        except PyMongoError as e:
            logger.error(f"Failed to delete function '{function_id}': {e}")
            return False

    def list_functions(self, filter_query: Dict[str, Any] = {}) -> List[FunctionEntry]:
        try:
            docs = self.collection.find(filter_query)
            functions = [FunctionEntry.from_dict(doc) for doc in docs]
            logger.info(f"{len(functions)} functions fetched with filter: {filter_query}")
            return functions
        except PyMongoError as e:
            logger.error(f"Failed to list functions: {e}")
            return []

    def get_functions_by_type(self, function_type: str) -> List[FunctionEntry]:
        try:
            docs = self.collection.find({"function_type": function_type})
            results = [FunctionEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} functions with type '{function_type}'")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch functions by type '{function_type}': {e}")
            return []

    def get_functions_by_tag(self, tag: str) -> List[FunctionEntry]:
        try:
            docs = self.collection.find({"function_tags": tag})
            results = [FunctionEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} functions with tag '{tag}'")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch functions by tag '{tag}': {e}")
            return []

    def get_functions_by_search_text(self, keyword: str) -> List[FunctionEntry]:
        try:
            docs = self.collection.find({
                "function_search_description": {"$regex": keyword, "$options": "i"}
            })
            results = [FunctionEntry.from_dict(doc) for doc in docs]
            logger.info(f"Found {len(results)} functions matching keyword '{keyword}'")
            return results
        except PyMongoError as e:
            logger.error(f"Search query failed for keyword '{keyword}': {e}")
            return []

    def get_functions_by_system_flag(self, is_system: bool) -> List[FunctionEntry]:
        try:
            docs = self.collection.find({"is_system_action": is_system})
            results = [FunctionEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} system={is_system} functions")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch functions by system flag '{is_system}': {e}")
            return []

    def query_functions(self, query: Dict[str, Any]) -> List[FunctionEntry]:
        try:
            docs = self.collection.find(query)
            results = [FunctionEntry.from_dict(doc) for doc in docs]
            logger.info(f"Generic query returned {len(results)} results: {query}")
            return results
        except PyMongoError as e:
            logger.error(f"Generic query failed: {query}, error: {e}")
            return []
