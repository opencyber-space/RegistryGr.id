from typing import Dict, Any
from .schema import RegistryCoreData, RegistrySearchData

class SpecParserValidator:
    @staticmethod
    def validate(spec: Dict[str, Any]) -> RegistryCoreData:
        if not isinstance(spec, dict):
            raise ValueError("Spec must be a dictionary")

        # Required top-level fields
        required_fields = ["registry_id"]
        for field in required_fields:
            if field not in spec or not isinstance(spec[field], str) or not spec[field].strip():
                raise ValueError(f"Missing or invalid required field: {field}")

        # Optional fields with type checks
        optional_str_fields = [
            "registry_url", "registry_api_index",
            "registry_documentation_s3_url", "registry_client_sdk_s3_url",
            "registry_asset_id", "health_check_api"
        ]
        for field in optional_str_fields:
            if field in spec and spec[field] is not None and not isinstance(spec[field], str):
                raise ValueError(f"Field {field} must be a string if provided")

        # registry_acl_config_info must be a dict[str, str] if present
        if "registry_acl_config_info" in spec:
            acl = spec["registry_acl_config_info"]
            if not isinstance(acl, dict):
                raise ValueError("registry_acl_config_info must be a dictionary")
            for k, v in acl.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ValueError("All keys and values in registry_acl_config_info must be strings")

        # Nested validation: registry_search_data
        if "registry_search_data" in spec:
            SpecParserValidator._validate_search_data(spec["registry_search_data"])

        try:
            return RegistryCoreData.from_dict(spec)
        except Exception as e:
            raise ValueError(f"Failed to construct RegistryCoreData: {e}")

    @staticmethod
    def _validate_search_data(data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("registry_search_data must be a dictionary")

        required_search_fields = ["registry_id"]
        for field in required_search_fields:
            if field not in data or not isinstance(data[field], str) or not data[field].strip():
                raise ValueError(f"Missing or invalid required search field: {field}")

        optional_str_fields = ["registry_type", "registry_sub_type", "registry_search_description"]
        for field in optional_str_fields:
            if field in data and data[field] is not None and not isinstance(data[field], str):
                raise ValueError(f"Field {field} in registry_search_data must be a string if provided")

        if "registry_metadata" in data:
            metadata = data["registry_metadata"]
            if not isinstance(metadata, dict):
                raise ValueError("registry_metadata must be a dictionary")
            for k, v in metadata.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ValueError("All keys and values in registry_metadata must be strings")

        if "registry_search_tags" in data:
            tags = data["registry_search_tags"]
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise ValueError("registry_search_tags must be a list of strings")
