from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class OrgObject:
    org_uri: str = ''
    org_id: str = ''
    org_spec_id: str = ''
    org_local_db_url: str = ''
    org_service_gateway_url: str = ''
    org_asset_registry_id: str = ''
    org_group_ids: List[str] = field(default_factory=list)
    org_name: str = ''
    org_description: str = ''
    org_metadata: Dict[str, Any] = field(default_factory=dict)
    org_url_map: Dict[str, str] = field(default_factory=dict)
    org_tags: List[str] = field(default_factory=list)
    org_spec_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrgObject":
        org_name = data.get("org_name", "")
        org_spec_id = data.get("org_spec_id", "")

        inferred_org_uri = (
            f"{org_name}:{org_spec_id}"
            if org_name and org_spec_id
            else ""
        )

        return cls(
            org_uri=inferred_org_uri,
            org_id=data.get("org_id", ""),
            org_spec_id=org_spec_id,
            org_local_db_url=data.get("org_local_db_url", ""),
            org_service_gateway_url=data.get("org_service_gateway_url", ""),
            org_asset_registry_id=data.get("org_asset_registry_id", ""),
            org_group_ids=data.get("org_group_ids", []),
            org_name=org_name,
            org_description=data.get("org_description", ""),
            org_metadata=data.get("org_metadata", {}),
            org_url_map=data.get("org_url_map", {}),
            org_tags=data.get("org_tags", []),
            org_spec_data=data.get("org_spec_data", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "org_uri": self.org_uri,
            "org_id": self.org_id,
            "org_spec_id": self.org_spec_id,
            "org_local_db_url": self.org_local_db_url,
            "org_service_gateway_url": self.org_service_gateway_url,
            "org_asset_registry_id": self.org_asset_registry_id,
            "org_group_ids": self.org_group_ids,
            "org_name": self.org_name,
            "org_description": self.org_description,
            "org_metadata": self.org_metadata,
            "org_url_map": self.org_url_map,
            "org_tags": self.org_tags,
            "org_spec_data": self.org_spec_data
        }
