from pymongo import MongoClient, ReturnDocument
from typing import Optional, Dict, Any
from dataclasses import asdict

from .schema import RegistryCoreData 
from .parser import SpecParserValidator

class RegistryDB:
    def __init__(self, mongo_uri="mongodb://localhost:27017", db_name="registry_system"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db["registry_core_data"]

    def create_registry(self, registry: RegistryCoreData) -> str:
        try:
            data = registry.to_dict()
            result = self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            raise RuntimeError(f"Failed to create registry: {e}")

    def update_registry(self, registry_id: str, updated_data: Dict[str, Any]) -> bool:
        try:
            result = self.collection.find_one_and_update(
                {"registry_id": registry_id},
                {"$set": updated_data},
                return_document=ReturnDocument.AFTER
            )
            return result is not None
        except Exception as e:
            raise RuntimeError(f"Failed to update registry: {e}")

    def delete_registry(self, registry_id: str) -> bool:
        try:
            result = self.collection.delete_one({"registry_id": registry_id})
            return result.deleted_count == 1
        except Exception as e:
            raise RuntimeError(f"Failed to delete registry: {e}")

    def get_registry(self, registry_id: str) -> Optional[RegistryCoreData]:
        try:
            data = self.collection.find_one({"registry_id": registry_id})
            if data:
                return RegistryCoreData.from_dict(data)
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to fetch registry: {e}")



class CreateRegistryController:
    def __init__(self, db: RegistryDB):
        self.db = db

    def create(self, registry_spec: Dict[str, Any]) -> str:
        try:
            # Step 1: Validate input
            registry_obj: RegistryCoreData = SpecParserValidator.validate(registry_spec)

            # Step 2: Persist to MongoDB
            registry_id = self.db.create_registry(registry_obj)

            return registry_id
        except Exception as e:
            raise RuntimeError(f"CreateRegistryController Error: {e}")


class UpdateRegistryController:
    def __init__(self, db: RegistryDB):
        self.db = db

    def update(self, registry_spec: Dict[str, Any]) -> bool:
        try:
            # Validate incoming spec
            registry_obj: RegistryCoreData = SpecParserValidator.validate(registry_spec)

            # Get registry ID to update
            registry_id = registry_obj.registry_id
            updated_data = registry_obj.to_dict()

            # Do not update the ID field itself
            updated_data.pop("registry_id", None)

            return self.db.update_registry(registry_id, updated_data)
        except Exception as e:
            raise RuntimeError(f"UpdateRegistryController Error: {e}")

class DeleteRegistryController:
    def __init__(self, db: RegistryDB):
        self.db = db

    def delete(self, registry_id: str) -> bool:
        if not registry_id or not isinstance(registry_id, str):
            raise ValueError("Invalid registry_id")

        try:
            result = self.db.delete_registry(registry_id)
            if not result:
                raise ValueError("Registry not found or already deleted")
            return True
        except Exception as e:
            raise RuntimeError(f"DeleteRegistryController Error: {e}")