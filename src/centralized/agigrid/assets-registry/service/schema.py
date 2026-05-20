from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class AssetProfile:
    asset_profile_id: str
    asset_type: str
    asset_sub_type: str
    asset_id: str
    asset_metadata: Optional[Dict[str, Any]] = None
    asset_creator_info: Optional[Dict[str, Any]] = None
    asset_tags: Optional[List[str]] = field(default_factory=list)
    asset_description: Optional[str] = None
    asset_complete_docs_url: Optional[str] = None
    asset_man_page_url: Optional[str] = None
    asset_sample_input_json: Optional[Dict[str, Any]] = None
    asset_sample_output_json: Optional[Dict[str, Any]] = None
    asset_sample_input_data_url: Optional[str] = None
    asset_sample_output_data_url: Optional[str] = None
    asset_author_metadata: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AssetProfile':
        return AssetProfile(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssetPolicy:
    asset_policy_id: str
    asset_id: str
    asset_policy_type: str
    asset_policy_rule_uri: Optional[str] = None
    asset_policy_rule_config: Optional[Dict[str, Any]] = None
    asset_policy_rule_params: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AssetPolicy':
        return AssetPolicy(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssetFile:
    asset_file_id: str
    asset_file_type: str
    asset_file_mime_type: str
    asset_file_url: str
    asset_file_metadata: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AssetFile':
        return AssetFile(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssetAPI:
    asset_api_id: str
    asset_id: str
    asset_api_metadata: Optional[Dict[str, Any]] = None
    asset_api_svc: Optional[str] = None
    asset_api_route: Optional[str] = None
    asset_api_protocol: Optional[str] = None
    asset_protocol_specific_config: Optional[Dict[str, Any]] = None
    asset_api_man_page: Optional[str] = None
    asset_api_swagger_doc: Optional[str] = None
    asset_api_usage_samples: Optional[List[Dict[str, Any]]] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AssetAPI':
        return AssetAPI(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IndexMapping:
    json_doc_id: str
    mapping_field_index: int
    table_name: str
    field_name: str
    render_page_no: int
    render_order_no: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'IndexMapping':
        return IndexMapping(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Asset:
    asset_id: str
    asset_uri: str
    asset_version: str
    asset_profile_id: str
    asset_file_ids: List[str]
    asset_container_uri: Optional[str] = None
    asset_policy_ids: List[str] = field(default_factory=list)
    asset_container_registry_creds_config: Optional[Dict[str, Any]] = None
    asset_workflow_id: Optional[str] = None
    asset_api_ids: List[str] = field(default_factory=list)
    asset_brief_description: Optional[str] = None

    profiles: List[AssetProfile] = field(default_factory=list)
    policies: List[AssetPolicy] = field(default_factory=list)
    files: List[AssetFile] = field(default_factory=list)
    apis: List[AssetAPI] = field(default_factory=list)
    index_mappings: List[IndexMapping] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Asset':
        return Asset(
            asset_id=data['asset_id'],
            asset_uri=data['asset_uri'],
            asset_version=data['asset_version'],
            asset_profile_id=data['asset_profile_id'],
            asset_file_ids=data.get('asset_file_ids', []),
            asset_container_uri=data.get('asset_container_uri'),
            asset_policy_ids=data.get('asset_policy_ids', []),
            asset_container_registry_creds_config=data.get('asset_container_registry_creds_config'),
            asset_workflow_id=data.get('asset_workflow_id'),
            asset_api_ids=data.get('asset_api_ids', []),
            asset_brief_description=data.get('asset_brief_description'),
            profiles=[AssetProfile.from_dict(p) for p in data.get('profiles', [])],
            policies=[AssetPolicy.from_dict(p) for p in data.get('policies', [])],
            files=[AssetFile.from_dict(f) for f in data.get('files', [])],
            apis=[AssetAPI.from_dict(a) for a in data.get('apis', [])],
            index_mappings=[IndexMapping.from_dict(i) for i in data.get('index_mappings', [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_uri": self.asset_uri,
            "asset_version": self.asset_version,
            "asset_profile_id": self.asset_profile_id,
            "asset_file_ids": self.asset_file_ids,
            "asset_container_uri": self.asset_container_uri,
            "asset_policy_ids": self.asset_policy_ids,
            "asset_container_registry_creds_config": self.asset_container_registry_creds_config,
            "asset_workflow_id": self.asset_workflow_id,
            "asset_api_ids": self.asset_api_ids,
            "asset_brief_description": self.asset_brief_description,
            "profiles": [p.to_dict() for p in self.profiles],
            "policies": [p.to_dict() for p in self.policies],
            "files": [f.to_dict() for f in self.files],
            "apis": [a.to_dict() for a in self.apis],
            "index_mappings": [i.to_dict() for i in self.index_mappings],
        }
