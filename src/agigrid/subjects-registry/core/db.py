import os
from typing import List, Dict, Optional
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import logging

from .schema import Subject, RuntimeSubject

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SubjectsDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL")
            if not db_url:
                raise ValueError("DB_URL environment variable is not set.")
            self.client = MongoClient(db_url)
            self.db = self.client["SubjectsDB"]
            self.collection = self.db["Subjects"]
            logger.info("Connected to MongoDB for Subjects.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB for Subjects: {e}")
            raise

    def create_subject(self, subject: Subject) -> bool:
        try:
            self.collection.insert_one(subject.to_dict())
            logger.info(f"Subject created with ID: {subject.subject_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Error creating subject: {e}")
            return False

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        try:
            result = self.collection.find_one({"subject_id": subject_id})
            if result:
                logger.info(f"Subject retrieved with ID: {subject_id}")
                return Subject.from_dict(result)
            logger.info(f"Subject with ID: {subject_id} not found.")
            return None
        except PyMongoError as e:
            logger.error(f"Error retrieving subject: {e}")
            return None

    def update_subject(self, subject_id: str, updated_data: dict) -> bool:
        try:
            result = self.collection.update_one(
                {"subject_id": subject_id},
                {"$set": updated_data}
            )
            if result.matched_count:
                logger.info(f"Subject updated with ID: {subject_id}")
                return True
            logger.info(f"Subject with ID: {subject_id} not found.")
            return False
        except PyMongoError as e:
            logger.error(f"Error updating subject: {e}")
            return False

    def delete_subject(self, subject_id: str) -> bool:
        try:
            result = self.collection.delete_one({"subject_id": subject_id})
            if result.deleted_count:
                logger.info(f"Subject deleted with ID: {subject_id}")
                return True
            logger.info(f"Subject with ID: {subject_id} not found.")
            return False
        except PyMongoError as e:
            logger.error(f"Error deleting subject: {e}")
            return False

    def list_subjects(self) -> List[Subject]:
        try:
            subjects = self.collection.find()
            subject_list = [Subject.from_dict(subject) for subject in subjects]
            logger.info(f"{len(subject_list)} subjects retrieved.")
            return subject_list
        except PyMongoError as e:
            logger.error(f"Error listing subjects: {e}")
            return []

    def query_subjects(self, query: Dict) -> List[Subject]:
        try:
            subjects = self.collection.find(query)
            subject_list = [Subject.from_dict(subject) for subject in subjects]
            logger.info(
                f"{len(subject_list)} subjects retrieved with query: {query}")
            return subject_list
        except PyMongoError as e:
            logger.error(f"Error querying subjects: {e}")
            return []


class RuntimeSubjectsDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL")
            if not db_url:
                raise ValueError("DB_URL environment variable is not set.")
            self.client = MongoClient(db_url)
            self.db = self.client["RuntimeSubjectsDB"]
            self.collection = self.db["RuntimeSubjects"]
            logger.info("Connected to MongoDB for RuntimeSubjects.")
        except Exception as e:
            logger.error(
                f"Failed to connect to MongoDB for RuntimeSubjects: {e}")
            raise

    def create_runtime_subject(self, runtime_subject: RuntimeSubject) -> bool:
        try:
            self.collection.insert_one(runtime_subject.to_dict())
            logger.info(
                f"RuntimeSubject created with ID: {runtime_subject.subject_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Error creating runtime subject: {e}")
            return False

    def get_runtime_subject(self, subject_id: str) -> Optional[RuntimeSubject]:
        try:
            result = self.collection.find_one({"subject_id": subject_id})
            if result:
                logger.info(f"RuntimeSubject retrieved with ID: {subject_id}")
                return RuntimeSubject.from_dict(result)
            logger.info(f"RuntimeSubject with ID: {subject_id} not found.")
            return None
        except PyMongoError as e:
            logger.error(f"Error retrieving runtime subject: {e}")
            return None

    def update_runtime_subject(self, subject_id: str, updated_data: dict) -> bool:
        try:
            result = self.collection.update_one(
                {"subject_id": subject_id},
                {"$set": updated_data}
            )
            if result.matched_count:
                logger.info(f"RuntimeSubject updated with ID: {subject_id}")
                return True
            logger.info(f"RuntimeSubject with ID: {subject_id} not found.")
            return False
        except PyMongoError as e:
            logger.error(f"Error updating runtime subject: {e}")
            return False

    def delete_runtime_subject(self, subject_id: str) -> bool:
        try:
            result = self.collection.delete_one({"subject_id": subject_id})
            if result.deleted_count:
                logger.info(f"RuntimeSubject deleted with ID: {subject_id}")
                return True
            logger.info(f"RuntimeSubject with ID: {subject_id} not found.")
            return False
        except PyMongoError as e:
            logger.error(f"Error deleting runtime subject: {e}")
            return False

    def list_runtime_subjects(self) -> List[RuntimeSubject]:
        try:
            runtime_subjects = self.collection.find()
            runtime_subject_list = [RuntimeSubject.from_dict(
                subject) for subject in runtime_subjects]
            logger.info(
                f"{len(runtime_subject_list)} runtime subjects retrieved.")
            return runtime_subject_list
        except PyMongoError as e:
            logger.error(f"Error listing runtime subjects: {e}")
            return []

    def query_runtime_subjects(self, query: Dict) -> List[RuntimeSubject]:
        try:
            runtime_subjects = self.collection.find(query)
            runtime_subject_list = [RuntimeSubject.from_dict(
                subject) for subject in runtime_subjects]
            logger.info(
                f"{len(runtime_subject_list)} runtime subjects retrieved with query: {query}")
            return runtime_subject_list
        except PyMongoError as e:
            logger.error(f"Error querying runtime subjects: {e}")
            return []


def create_runtime_version_of_subject(
    subject_id: str,
    runtime_data: Dict[str, Dict]
) -> bool:
    try:
        subject_db = SubjectsDB()
        subject = subject_db.get_subject(subject_id)
        if not subject:
            logger.error(f"Subject with ID {subject_id} not found.")
            return False

        runtime_subject = RuntimeSubject(
            subject_name=subject.subject_name,
            subject_type=subject.subject_type,
            subject_version=subject.subject_version,
            subject_description=subject.subject_description,
            subject_search_tags=subject.subject_search_tags,
            subject_traits=subject.subject_traits,
            subject_role=subject.subject_role,
            subject_dsls=subject.subject_dsls,
            runtime_info=runtime_data.get("runtime_info", {}),
            runtime_db_info=runtime_data.get("runtime_db_info", {}),
            orgs=runtime_data.get("orgs", [])
        )

        runtime_subjects_db = RuntimeSubjectsDB()
        success = runtime_subjects_db.create_runtime_subject(runtime_subject)
        if success:
            logger.info(
                f"Runtime version created for Subject ID: {subject_id}")
        return success
    except Exception as e:
        logger.error(f"Error creating runtime version of subject: {e}")
        return False


def update_orgs_for_subject(subject_id: str, orgs_to_add: List[str], orgs_to_remove: List[str]) -> bool:

    try:
        runtime_subjects_db = RuntimeSubjectsDB()
        runtime_subject = runtime_subjects_db.get_runtime_subject(subject_id)
        if not runtime_subject:
            logger.error(f"RuntimeSubject with ID {subject_id} not found.")
            return False

        current_orgs = set(runtime_subject.orgs)
        current_orgs.update(orgs_to_add)
        current_orgs.difference_update(orgs_to_remove)
        updated_orgs = list(current_orgs)

        success = runtime_subjects_db.update_runtime_subject(
            subject_id, {"orgs": updated_orgs}
        )

        if success:
            logger.info(
                f"Organizations updated for RuntimeSubject ID: {subject_id}")
        return success
    except Exception as e:
        logger.error(f"Error updating organizations for runtime subject: {e}")
        return False
