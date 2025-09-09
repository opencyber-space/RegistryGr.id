import os
import pymongo
from pymongo.errors import PyMongoError
from typing import Optional, List

from .schema import DSLExecutors

class ExecutorsDB:
    def __init__(self):
        try:
            db_url = os.getenv("MONGO_URL",  "mongodb://localhost:27017/policies")
            if not db_url:
                raise ValueError("Environment variable 'DB_URL' is not set.")
            self.client = pymongo.MongoClient(db_url)
            self.db = self.client["policies"]
            self.collection = self.db["executors"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize database connection: {e}")

    def create(self, executor: DSLExecutors) -> bool:
        try:
            executor_dict = executor.to_dict()
            self.collection.insert_one(executor_dict)
            return True
        except PyMongoError as e:
            print(f"Error creating executor: {e}")
            return False

    def read(self, executor_id: str) -> Optional[DSLExecutors]:
        try:
            result = self.collection.find_one({"executor_id": executor_id})
            if result:
                return DSLExecutors.from_dict(result)
            return None
        except PyMongoError as e:
            print(f"Error reading executor: {e}")
            return None

    def update(self, executor_id: str, updated_executor: DSLExecutors) -> bool:
        try:
            updated_data = updated_executor.to_dict()
            result = self.collection.update_one(
                {"executor_id": executor_id}, {"$set": updated_data}
            )
            return result.matched_count > 0
        except PyMongoError as e:
            print(f"Error updating executor: {e}")
            return False

    def delete(self, executor_id: str) -> bool:
        try:
            result = self.collection.delete_one({"executor_id": executor_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting executor: {e}")
            return False

    def query(self, query_filter: dict) -> List[DSLExecutors]:
        try:
            results = self.collection.find(query_filter)
            return [DSLExecutors.from_dict(result) for result in results]
        except PyMongoError as e:
            print(f"Error executing query: {e}")
            return []

