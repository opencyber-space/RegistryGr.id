from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List
from datetime import datetime

@dataclass
class SpecVersion:
    version: str = ''
    release: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpecVersion':
        return cls(
            version=data.get('version', ''),
            release=data.get('release', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'release': self.release
        }


@dataclass
class SpecObject:
    spec_name: str = ''
    spec_version: SpecVersion = field(default_factory=SpecVersion)
    spec_metadata: Dict[str, Any] = field(default_factory=dict)
    spec_description: str = ''
    spec_search_tags: List[str] = field(default_factory=list)
    spec_data: Dict[str, Any] = field(default_factory=dict)
    spec_type: str = ''
    creation_time: str = ''
    last_update_time: str = ''
    template_id: str = ''
    backend_policy_rule_ids: Dict[str, Any] = field(default_factory=dict)
    actions: Dict[str, Any] = field(default_factory=dict)

    @property
    def spec_uri(self) -> str:
        return f"{self.spec_name}:{self.spec_version.version}-{self.spec_version.release}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpecObject':
        return cls(
            spec_name=data.get('spec_name', ''),
            spec_version=SpecVersion.from_dict(data.get('spec_version', {})),
            spec_metadata=data.get('spec_metadata', {}),
            spec_description=data.get('spec_description', ''),
            spec_search_tags=data.get('spec_search_tags', []),
            spec_data=data.get('spec_data', {}),
            spec_type=data.get('spec_type', ''),
            creation_time=data.get('creation_time', ''),
            last_update_time=data.get('last_update_time', ''),
            template_id=data.get('template_id', ''),
            backend_policy_rule_ids=data.get('backend_policy_rule_ids', {}),
            actions=data.get('actions', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'spec_name': self.spec_name,
            'spec_version': self.spec_version.to_dict(),
            'spec_uri': self.spec_uri,
            'spec_metadata': self.spec_metadata,
            'spec_description': self.spec_description,
            'spec_search_tags': self.spec_search_tags,
            'spec_data': self.spec_data,
            'spec_type': self.spec_type,
            'creation_time': self.creation_time,
            'last_update_time': self.last_update_time,
            'template_id': self.template_id,
            'backend_policy_rule_ids': self.backend_policy_rule_ids,
            'actions': self.actions
        }


@dataclass
class WorkflowVersion:
    version: str = ''
    release: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowVersion':
        return cls(
            version=data.get('version', ''),
            release=data.get('release', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'release': self.release
        }


@dataclass
class WorkflowObject:
    workflow_name: str = ''
    workflow_version: WorkflowVersion = field(default_factory=WorkflowVersion)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)
    workflow_description: str = ''
    workflow_search_tags: List[str] = field(default_factory=list)
    workflow_mock_input_data: Dict[str, Any] = field(default_factory=dict)
    workflow_spec_ids: List[str] = field(default_factory=list)
    workflow_graph_data: List[Dict[str, Any]] = field(default_factory=list)
    workflow_template_id: str = ''
    workflow_creation_time: str = ''
    workflow_last_update_time: str = ''
    workflow_type: str = ''
    workflow_sub_type: str = ''

    @property
    def workflow_uri(self) -> str:
        return f"{self.workflow_name}:{self.workflow_version.version}-{self.workflow_version.release}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowObject':
        return cls(
            workflow_name=data.get('workflow_name', ''),
            workflow_version=WorkflowVersion.from_dict(data.get('workflow_version', {})),
            workflow_metadata=data.get('workflow_metadata', {}),
            workflow_description=data.get('workflow_description', ''),
            workflow_search_tags=data.get('workflow_search_tags', []),
            workflow_mock_input_data=data.get('workflow_mock_input_data', {}),
            workflow_spec_ids=data.get('workflow_spec_ids', []),
            workflow_graph_data=data.get('workflow_graph_data', []),
            workflow_template_id=data.get('workflow_template_id', ''),
            workflow_creation_time=data.get('workflow_creation_time', ''),
            workflow_last_update_time=data.get('workflow_last_update_time', ''),
            workflow_type=data.get('workflow_type', ''),
            workflow_sub_type=data.get('workflow_sub_type', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'workflow_name': self.workflow_name,
            'workflow_version': self.workflow_version.to_dict(),
            'workflow_uri': self.workflow_uri,
            'workflow_metadata': self.workflow_metadata,
            'workflow_description': self.workflow_description,
            'workflow_search_tags': self.workflow_search_tags,
            'workflow_mock_input_data': self.workflow_mock_input_data,
            'workflow_spec_ids': self.workflow_spec_ids,
            'workflow_graph_data': self.workflow_graph_data,
            'workflow_template_id': self.workflow_template_id,
            'workflow_creation_time': self.workflow_creation_time,
            'workflow_last_update_time': self.workflow_last_update_time,
            'workflow_type': self.workflow_type,
            'workflow_sub_type': self.workflow_sub_type
        }


@dataclass
class TemplateObject:
    template_id: str = ''
    template_metadata: Dict[str, Any] = field(default_factory=dict)
    template_description: str = ''
    template_data: Dict[str, Any] = field(default_factory=dict)
    template_custom_validation_policy_rule_uri: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateObject':
        return cls(
            template_id=data.get('template_id', ''),
            template_metadata=data.get('template_metadata', {}),
            template_description=data.get('template_description', ''),
            template_data=data.get('template_data', {}),
            template_custom_validation_policy_rule_uri=data.get(
                'template_custom_validation_policy_rule_uri', ''
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'template_metadata': self.template_metadata,
            'template_description': self.template_description,
            'template_data': self.template_data,
            'template_custom_validation_policy_rule_uri': self.template_custom_validation_policy_rule_uri
        }

@dataclass
class DSLExecutors:
    executor_id: str
    executor_host_uri: str
    executor_metadata: Dict
    executor_hardware_info: Dict
    executor_status: str = field(default="healthy")

    @staticmethod
    def from_dict(data: Dict) -> 'DSLExecutors':
        return DSLExecutors(
            executor_id=data['executor_id'],
            executor_host_uri=data['executor_host_uri'],
            executor_metadata=data['executor_metadata'],
            executor_hardware_info=data['executor_hardware_info'],
            executor_status=data.get('executor_status', "healthy"),
        )

    def to_dict(self) -> Dict:
        return asdict(self)