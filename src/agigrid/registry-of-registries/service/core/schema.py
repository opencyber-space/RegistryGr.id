from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class RegistrySearchData:
    registry_id: str
    registry_type: Optional[str] = None
    registry_sub_type: Optional[str] = None
    registry_metadata: Optional[Dict[str, str]] = field(default_factory=dict)
    registry_search_tags: Optional[List[str]] = field(default_factory=list)
    registry_search_description: Optional[str] = None

    def to_dict(self):
        return {
            "registry_id": self.registry_id,
            "registry_type": self.registry_type,
            "registry_sub_type": self.registry_sub_type,
            "registry_metadata": self.registry_metadata,
            "registry_search_tags": self.registry_search_tags,
            "registry_search_description": self.registry_search_description,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            registry_id=data.get("registry_id", ""),
            registry_type=data.get("registry_type"),
            registry_sub_type=data.get("registry_sub_type"),
            registry_metadata=data.get("registry_metadata", {}),
            registry_search_tags=data.get("registry_search_tags", []),
            registry_search_description=data.get("registry_search_description")
        )


@dataclass
class RegistryCoreData:
    registry_id: str
    registry_url: Optional[str] = None
    registry_api_index: Optional[str] = None
    registry_documentation_s3_url: Optional[str] = None
    registry_client_sdk_s3_url: Optional[str] = None
    registry_acl_config_info: Optional[Dict[str, str]] = field(default_factory=dict)
    registry_asset_id: Optional[str] = None
    health_check_api: Optional[str] = None
    registry_search_data: Optional[RegistrySearchData] = None

    def to_dict(self):
        return {
            "registry_id": self.registry_id,
            "registry_url": self.registry_url,
            "registry_api_index": self.registry_api_index,
            "registry_documentation_s3_url": self.registry_documentation_s3_url,
            "registry_client_sdk_s3_url": self.registry_client_sdk_s3_url,
            "registry_acl_config_info": self.registry_acl_config_info,
            "registry_asset_id": self.registry_asset_id,
            "health_check_api": self.health_check_api,
            "registry_search_data": self.registry_search_data.to_dict() if self.registry_search_data else None,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            registry_id=data.get("registry_id", ""),
            registry_url=data.get("registry_url"),
            registry_api_index=data.get("registry_api_index"),
            registry_documentation_s3_url=data.get("registry_documentation_s3_url"),
            registry_client_sdk_s3_url=data.get("registry_client_sdk_s3_url"),
            registry_acl_config_info=data.get("registry_acl_config_info", {}),
            registry_asset_id=data.get("registry_asset_id"),
            health_check_api=data.get("health_check_api"),
            registry_search_data=RegistrySearchData.from_dict(data["registry_search_data"])
            if data.get("registry_search_data") else None
        )
