import os
import logging
from typing import Dict, List, Tuple, Union

from pymongo import MongoClient, errors

from .schema import Exchange

logger = logging.getLogger("ExchangeDatabase")
logging.basicConfig(level=logging.INFO)


class ExchangeDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["inference"]
            self.collection = self.db["exchanges"]
            logger.info("MongoDB connection established for ExchangeDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, exchange: "Exchange") -> Tuple[bool, Union[str, None]]:
        try:
            document = exchange.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Exchange inserted with ID: {exchange.exchange_id}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting exchange: {e}")
            return False, str(e)

    def update(self, exchange_id: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"exchange_id": exchange_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Exchange with ID {exchange_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with ID {exchange_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating exchange: {e}")
            return False, str(e)

    def delete(self, exchange_id: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"exchange_id": exchange_id})
            if result.deleted_count > 0:
                logger.info(f"Exchange with ID {exchange_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with ID {exchange_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting exchange: {e}")
            return False, str(e)

    def query(self, query_filter: Dict) -> Tuple[bool, Union[List[Dict], str]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying exchanges: {e}")
            return False, str(e)

    def get_by_exchange_id(self, exchange_id: str) -> Tuple[bool, Union["Exchange", str]]:
        try:
            doc = self.collection.find_one({"exchange_id": exchange_id})
            if doc:
                doc.pop('_id', None)
                exchange = Exchange.from_dict(doc)
                logger.info(f"Exchange with ID {exchange_id} retrieved")
                return True, exchange
            else:
                logger.info(f"No exchange found with ID {exchange_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving exchange: {e}")
            return False, str(e)
