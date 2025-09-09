import logging
import os
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from .schema import ToolEntry

# Setup logger
logger = logging.getLogger("ToolsRegistryCRUD")
logger.setLevel(logging.INFO)

class ToolsRegistryCRUD:
    db_name: str = "tools_registry"
    collection_name: str = "tools"

    def __init__(self):
        try:
            self.mongo_uri = os.getenv("MONGO_URL", "")
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection: Collection = self.db[self.collection_name]
            logger.info(f"Connected to MongoDB: {self.mongo_uri}, DB: {self.db_name}, Collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    def create_tool(self, tool: ToolEntry) -> bool:
        try:
            if self.collection.find_one({"tool_id": tool.tool_id}):
                logger.warning(f"Tool with ID '{tool.tool_id}' already exists.")
                return False
            self.collection.insert_one(tool.to_dict())
            logger.info(f"Tool '{tool.tool_id}' inserted successfully.")
            return True
        except PyMongoError as e:
            logger.error(f"Failed to insert tool '{tool.tool_id}': {e}")
            return False

    def get_tool(self, tool_id: str) -> Optional[ToolEntry]:
        try:
            doc = self.collection.find_one({"tool_id": tool_id})
            if doc:
                logger.info(f"Tool '{tool_id}' retrieved successfully.")
                return ToolEntry.from_dict(doc)
            logger.warning(f"Tool '{tool_id}' not found.")
            return None
        except PyMongoError as e:
            logger.error(f"Failed to retrieve tool '{tool_id}': {e}")
            return None

    def update_tool(self, tool_id: str, updates: Dict[str, Any]) -> bool:
        try:
            result = self.collection.update_one({"tool_id": tool_id}, {"$set": updates})
            if result.matched_count:
                logger.info(f"Tool '{tool_id}' updated successfully.")
                return True
            else:
                logger.warning(f"Tool '{tool_id}' not found for update.")
                return False
        except PyMongoError as e:
            logger.error(f"Failed to update tool '{tool_id}': {e}")
            return False

    def delete_tool(self, tool_id: str) -> bool:
        try:
            result = self.collection.delete_one({"tool_id": tool_id})
            if result.deleted_count:
                logger.info(f"Tool '{tool_id}' deleted successfully.")
                return True
            else:
                logger.warning(f"Tool '{tool_id}' not found for deletion.")
                return False
        except PyMongoError as e:
            logger.error(f"Failed to delete tool '{tool_id}': {e}")
            return False

    def list_tools(self, filter_query: Dict[str, Any] = {}) -> List[ToolEntry]:
        try:
            docs = self.collection.find(filter_query)
            tools = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"{len(tools)} tools fetched with filter: {filter_query}")
            return tools
        except PyMongoError as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    def get_tools_by_type(self, tool_type: str) -> List[ToolEntry]:
        try:
            docs = self.collection.find({"tool_type": tool_type})
            results = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} tools with type '{tool_type}'")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch tools by type '{tool_type}': {e}")
            return []

    def get_tools_by_tag(self, tag: str) -> List[ToolEntry]:
        try:
            docs = self.collection.find({"tool_tags": tag})
            results = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} tools with tag '{tag}'")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch tools by tag '{tag}': {e}")
            return []

    def get_tools_by_search_text(self, keyword: str) -> List[ToolEntry]:
        try:
            docs = self.collection.find({
                "tool_search_description": {"$regex": keyword, "$options": "i"}
            })
            results = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"Found {len(results)} tools matching keyword '{keyword}'")
            return results
        except PyMongoError as e:
            logger.error(f"Search query failed for keyword '{keyword}': {e}")
            return []

    def get_tools_by_execution_mode(self, mode: str) -> List[ToolEntry]:
        try:
            docs = self.collection.find({"tool_execution_mode": mode})
            results = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} tools with execution mode '{mode}'")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch tools by execution mode '{mode}': {e}")
            return []

    def get_tools_by_policy_rule(self, policy_uri: str) -> List[ToolEntry]:
        try:
            docs = self.collection.find({"tool_policy_rule_uri": policy_uri})
            results = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(results)} tools with policy rule URI '{policy_uri}'")
            return results
        except PyMongoError as e:
            logger.error(f"Failed to fetch tools by policy URI '{policy_uri}': {e}")
            return []
    
    def query_tools(self, query: Dict[str, Any]) -> List[ToolEntry]:
        try:
            docs = self.collection.find(query)
            results = [ToolEntry.from_dict(doc) for doc in docs]
            logger.info(f"Generic query returned {len(results)} results: {query}")
            return results
        except PyMongoError as e:
            logger.error(f"Generic query failed: {query}, error: {e}")
            return []

