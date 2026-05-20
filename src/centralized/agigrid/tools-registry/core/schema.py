from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class ToolEntry:
    tool_id: str = ''
    tool_metadata: Dict[str, Any] = field(default_factory=dict)
    tool_search_description: str = ''
    tool_tags: List[str] = field(default_factory=list)
    tool_type: str = ''
    tool_man_page_doc: str = ''
    tool_api_spec: Dict[str, Any] = field(default_factory=dict)
    tool_custom_actions_dsl_map: Dict[str, Any] = field(default_factory=dict)
    default_tool_usage_credentials: Dict[str, Any] = field(default_factory=dict)
    tool_settings: Dict[str, Any] = field(default_factory=dict)
    tool_parameters: Dict[str, Any] = field(default_factory=dict)

    tool_execution_mode: str = ''
    tool_policy_rule_uri: str = ''
    tool_source_code_link: str = ''
    tool_runtime_type: str = ''
    tool_service_url: str = ''
    tool_system_function_rpc_id: str = ''
    tool_validation_policy_rule_uri: str = ''
    tool_validation_mode: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolEntry":
        return cls(
            tool_id=data.get("tool_id", ""),
            tool_metadata=data.get("tool_metadata", {}),
            tool_search_description=data.get("tool_search_description", ""),
            tool_tags=data.get("tool_tags", []),
            tool_type=data.get("tool_type", ""),
            tool_man_page_doc=data.get("tool_man_page_doc", ""),
            tool_api_spec=data.get("tool_api_spec", {}),
            tool_custom_actions_dsl_map=data.get("tool_custom_actions_dsl_map", {}),
            default_tool_usage_credentials=data.get("default_tool_usage_credentials", {}),

            tool_execution_mode=data.get("tool_execution_mode", ""),
            tool_policy_rule_uri=data.get("tool_policy_rule_uri", ""),
            tool_source_code_link=data.get("tool_source_code_link", ""),
            tool_service_url=data.get("tool_service_url", ""),
            tool_system_function_rpc_id=data.get("tool_system_function_rpc_id", ""),
            tool_validation_policy_rule_uri=data.get("tool_validation_policy_rule_uri", ""),
            tool_validation_mode=data.get("tool_validation_mode", ""),
            tool_runtime_type=data.get('tool_runtime_type', ''),
            tool_settings=data.get('tool_settings', {}),
            tool_parameters=data.get('tool_parameters', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_metadata": self.tool_metadata,
            "tool_search_description": self.tool_search_description,
            "tool_tags": self.tool_tags,
            "tool_type": self.tool_type,
            "tool_man_page_doc": self.tool_man_page_doc,
            "tool_api_spec": self.tool_api_spec,
            "tool_custom_actions_dsl_map": self.tool_custom_actions_dsl_map,
            "default_tool_usage_credentials": self.default_tool_usage_credentials,

            "tool_execution_mode": self.tool_execution_mode,
            "tool_policy_rule_uri": self.tool_policy_rule_uri,
            "tool_source_code_link": self.tool_source_code_link,
            "tool_service_url": self.tool_service_url,
            "tool_system_function_rpc_id": self.tool_system_function_rpc_id,
            "tool_validation_policy_rule_uri": self.tool_validation_policy_rule_uri,
            "tool_validation_mode": self.tool_validation_mode,
            "tool_runtime_type": self.tool_runtime_type,
            "tool_settings": self.tool_settings,
            "tool_parameters": self.tool_parameters
        }
