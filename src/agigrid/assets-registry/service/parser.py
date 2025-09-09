import logging
from typing import Dict, Any, Tuple, Optional, List, Union
from .schema import Asset

logger = logging.getLogger("SpecParser")
logger.setLevel(logging.INFO)

def _validate_field_type(field_name: str, value: Any, expected_type: Union[type, tuple]) -> Optional[str]:
    if not isinstance(value, expected_type):
        return f"{field_name} must be of type {expected_type.__name__}"
    return None


class SpecParser:

    @staticmethod
    def validate_asset(data: Dict[str, Any]) -> List[str]:
        errors = []

        required_fields = ["asset_id", "asset_uri", "asset_version", "asset_profile_id", "asset_file_ids"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        field_types = {
            "asset_id": str,
            "asset_uri": str,
            "asset_version": str,
            "asset_profile_id": str,
            "asset_file_ids": list,
            "asset_policy_ids": list,
            "asset_api_ids": list,
            "asset_brief_description": (str, type(None)),
            "asset_container_uri": (str, type(None)),
            "asset_container_registry_creds_config": (dict, type(None)),
            "asset_workflow_id": (str, type(None)),
        }

        for field, expected in field_types.items():
            if field in data:
                error = _validate_field_type(field, data[field], expected)
                if error:
                    errors.append(error)

        # Nested component validations
        errors += SpecParser.validate_profiles(data.get("profiles", []))
        errors += SpecParser.validate_policies(data.get("policies", []))
        errors += SpecParser.validate_files(data.get("files", []))
        errors += SpecParser.validate_apis(data.get("apis", []))
        errors += SpecParser.validate_index_mappings(data.get("index_mappings", []))

        return errors

    @staticmethod
    def validate_profiles(profiles: List[Dict[str, Any]]) -> List[str]:
        errors = []
        for i, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                errors.append(f"profiles[{i}] must be a dict")
                continue
            for field in ["asset_profile_id", "asset_type", "asset_sub_type", "asset_id"]:
                if field not in profile:
                    errors.append(f"profiles[{i}]: missing {field}")
                elif not isinstance(profile[field], str):
                    errors.append(f"profiles[{i}]: {field} must be a string")
        return errors

    @staticmethod
    def validate_policies(policies: List[Dict[str, Any]]) -> List[str]:
        errors = []
        for i, policy in enumerate(policies):
            if not isinstance(policy, dict):
                errors.append(f"policies[{i}] must be a dict")
                continue
            for field in ["asset_policy_id", "asset_id", "asset_policy_type"]:
                if field not in policy:
                    errors.append(f"policies[{i}]: missing {field}")
                elif not isinstance(policy[field], str):
                    errors.append(f"policies[{i}]: {field} must be a string")
        return errors

    @staticmethod
    def validate_files(files: List[Dict[str, Any]]) -> List[str]:
        errors = []
        for i, file in enumerate(files):
            if not isinstance(file, dict):
                errors.append(f"files[{i}] must be a dict")
                continue
            for field in ["asset_file_id", "asset_file_type", "asset_file_mime_type", "asset_file_url"]:
                if field not in file:
                    errors.append(f"files[{i}]: missing {field}")
                elif not isinstance(file[field], str):
                    errors.append(f"files[{i}]: {field} must be a string")
        return errors

    @staticmethod
    def validate_apis(apis: List[Dict[str, Any]]) -> List[str]:
        errors = []
        for i, api in enumerate(apis):
            if not isinstance(api, dict):
                errors.append(f"apis[{i}] must be a dict")
                continue
            if "asset_api_id" not in api or not isinstance(api["asset_api_id"], str):
                errors.append(f"apis[{i}]: missing or invalid asset_api_id")
            if "asset_id" not in api or not isinstance(api["asset_id"], str):
                errors.append(f"apis[{i}]: missing or invalid asset_id")
        return errors

    @staticmethod
    def validate_index_mappings(mappings: List[Dict[str, Any]]) -> List[str]:
        errors = []
        for i, mapping in enumerate(mappings):
            if not isinstance(mapping, dict):
                errors.append(f"index_mappings[{i}] must be a dict")
                continue
            required = {
                "json_doc_id": str,
                "mapping_field_index": int,
                "table_name": str,
                "field_name": str,
                "render_page_no": int,
                "render_order_no": int,
            }
            for field, typ in required.items():
                if field not in mapping:
                    errors.append(f"index_mappings[{i}]: missing {field}")
                elif not isinstance(mapping[field], typ):
                    errors.append(f"index_mappings[{i}]: {field} must be of type {typ.__name__}")
        return errors

    @staticmethod
    def parse_spec(data: Dict[str, Any]) -> Tuple[Optional[Asset], Optional[str]]:
        logger.info("[SpecParser] Validating asset specification")

        errors = SpecParser.validate_asset(data)
        if errors:
            error_msg = "Validation failed:\n" + "\n".join(errors)
            logger.error(f"[SpecParser] Validation errors:\n{error_msg}")
            return None, error_msg

        try:
            asset = Asset.from_dict(data)
            logger.info(f"[SpecParser] Successfully parsed asset: {asset.asset_id}")
            return asset, None
        except Exception as e:
            logger.exception("[SpecParser] Failed during Asset.from_dict()")
            return None, f"Exception during parsing: {e}"
