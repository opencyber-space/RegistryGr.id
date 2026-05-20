import os
import logging
from pymongo import MongoClient, errors
from typing import Dict, Any, Tuple, Union

from .schema import SpecObject, WorkflowObject, TemplateObject

logger = logging.getLogger(__name__)


class SpecDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["specs"]
            self.collection = self.db["specs"]
            logger.info("MongoDB connection to 'specs' database established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, spec: SpecObject) -> Tuple[bool, Union[str, Any]]:
        try:
            document = spec.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Spec inserted with URI: {spec.spec_uri}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting Spec: {e}")
            return False, str(e)

    def update(self, spec_uri: str, update_fields: Dict[str, Any]) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.update_one(
                {"spec_uri": spec_uri},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Spec with URI {spec_uri} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with spec_uri {spec_uri} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating Spec: {e}")
            return False, str(e)

    def delete(self, spec_uri: str) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.delete_one({"spec_uri": spec_uri})
            if result.deleted_count > 0:
                logger.info(f"Spec with URI {spec_uri} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with spec_uri {spec_uri} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting Spec: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Union[str, list]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying Specs: {e}")
            return False, str(e)

    def get_by_spec_uri(self, spec_uri: str) -> Tuple[bool, Union[str, SpecObject]]:
        try:
            doc = self.collection.find_one({"spec_uri": spec_uri})
            if doc:
                doc.pop('_id', None)
                spec = SpecObject.from_dict(doc)
                logger.info(f"Spec with URI {spec_uri} retrieved")
                return True, spec
            else:
                logger.info(f"No Spec found with URI {spec_uri}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving Spec: {e}")
            return False, str(e)


class WorkflowDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["workflows"]
            self.collection = self.db["workflows"]
            logger.info("MongoDB connection to 'workflows' database established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, workflow: WorkflowObject) -> Tuple[bool, Union[str, Any]]:
        try:
            document = workflow.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Workflow inserted with URI: {workflow.workflow_uri}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting Workflow: {e}")
            return False, str(e)

    def update(self, workflow_uri: str, update_fields: Dict[str, Any]) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.update_one(
                {"workflow_uri": workflow_uri},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Workflow with URI {workflow_uri} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with workflow_uri {workflow_uri} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating Workflow: {e}")
            return False, str(e)

    def delete(self, workflow_uri: str) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.delete_one({"workflow_uri": workflow_uri})
            if result.deleted_count > 0:
                logger.info(f"Workflow with URI {workflow_uri} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with workflow_uri {workflow_uri} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting Workflow: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Union[str, list]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying Workflows: {e}")
            return False, str(e)

    def get_by_workflow_uri(self, workflow_uri: str) -> Tuple[bool, Union[str, WorkflowObject]]:
        try:
            doc = self.collection.find_one({"workflow_uri": workflow_uri})
            if doc:
                doc.pop('_id', None)
                workflow = WorkflowObject.from_dict(doc)
                logger.info(f"Workflow with URI {workflow_uri} retrieved")
                return True, workflow
            else:
                logger.info(f"No Workflow found with URI {workflow_uri}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving Workflow: {e}")
            return False, str(e)

class TemplateDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["templates"]
            self.collection = self.db["templates"]
            logger.info("MongoDB connection to 'templates' database established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, template: TemplateObject) -> Tuple[bool, Union[str, Any]]:
        try:
            document = template.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Template inserted with ID: {template.template_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting Template: {e}")
            return False, str(e)

    def update(self, template_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.update_one(
                {"template_id": template_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Template with ID {template_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with template_id {template_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating Template: {e}")
            return False, str(e)

    def delete(self, template_id: str) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.delete_one({"template_id": template_id})
            if result.deleted_count > 0:
                logger.info(f"Template with ID {template_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with template_id {template_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting Template: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Union[str, list]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying Templates: {e}")
            return False, str(e)

    def get_by_template_id(self, template_id: str) -> Tuple[bool, Union[str, TemplateObject]]:
        try:
            doc = self.collection.find_one({"template_id": template_id})
            if doc:
                doc.pop('_id', None)
                template = TemplateObject.from_dict(doc)
                logger.info(f"Template with ID {template_id} retrieved")
                return True, template
            else:
                logger.info(f"No Template found with ID {template_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving Template: {e}")
            return False, str(e)


