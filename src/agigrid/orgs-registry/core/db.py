import os
from pymongo import MongoClient, errors
from typing import Tuple, Union, List, Dict
import logging
from .schema import OrgObject

logger = logging.getLogger(__name__)


class OrgStoreDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["orgs"]
            self.collection = self.db["orgs"]
            logger.info("MongoDB connection established for OrgStoreDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, org: OrgObject) -> Tuple[bool, Union[str, None]]:
        try:
            document = org.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Org inserted with org_uri: {org.org_uri}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting org: {e}")
            return False, str(e)

    def update(self, org_uri: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"org_uri": org_uri},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Org with org_uri {org_uri} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with org_uri {org_uri} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating org: {e}")
            return False, str(e)

    def delete(self, org_uri: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"org_uri": org_uri})
            if result.deleted_count > 0:
                logger.info(f"Org with org_uri {org_uri} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with org_uri {org_uri} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting org: {e}")
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
            logger.error(f"Error querying orgs: {e}")
            return False, str(e)

    def get_by_org_uri(self, org_uri: str) -> Tuple[bool, Union[OrgObject, str]]:
        try:
            doc = self.collection.find_one({"org_uri": org_uri})
            if doc:
                doc.pop('_id', None)
                org = OrgObject.from_dict(doc)
                logger.info(f"Org with org_uri {org_uri} retrieved")
                return True, org
            else:
                logger.info(f"No org found with org_uri {org_uri}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving org: {e}")
            return False, str(e)


class OrgStoreQueries:
    def __init__(self, collection):
        self.collection = collection

    def _execute_query(self, filter_query: Dict) -> Tuple[bool, Union[List[OrgObject], str]]:
        try:
            result = self.collection.find(filter_query)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(OrgObject.from_dict(doc))
            return True, documents
        except Exception as e:
            logger.error(f"MongoDB query error: {e}")
            return False, str(e)

    def find_by_org_id(self, org_id: str) -> Tuple[bool, Union[OrgObject, str]]:
        try:
            doc = self.collection.find_one({"org_id": org_id})
            if doc:
                doc.pop('_id', None)
                return True, OrgObject.from_dict(doc)
            return False, "Organization not found"
        except Exception as e:
            logger.error(f"Error fetching org by org_id: {e}")
            return False, str(e)

    def find_by_spec_id(self, spec_id: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({"org_spec_id": spec_id})

    def find_by_tag(self, tag: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({"org_tags": tag})

    def find_by_group_id(self, group_id: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({"org_group_ids": group_id})

    def find_by_asset_registry(self, registry_id: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({"org_asset_registry_id": registry_id})

    def search_by_name_keyword(self, keyword: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({"org_name": {"$regex": keyword, "$options": "i"}})

    def find_with_url_prefix(self, prefix: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({"org_service_gateway_url": {"$regex": f"^{prefix}"}})

    def find_by_metadata_key_value(self, key: str, value: Union[str, int]) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({f"org_metadata.{key}": value})

    def find_by_spec_data_key(self, key: str) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({f"org_spec_data.{key}": {"$exists": True}})

    def list_all(self) -> Tuple[bool, Union[List[OrgObject], str]]:
        return self._execute_query({})
