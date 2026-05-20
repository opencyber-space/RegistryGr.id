from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class TaskEntry:
    task_id: str
    task_goal: str
    task_intent: str
    task_priority_value: int
    task_streeability_data: Dict[str, Any] = field(default_factory=dict)
    task_knowledgebase_ptr: Optional[str] = None
    submitter_subject_id: str = ''
    task_op_convertor_dsl_id: Optional[str] = None
    task_execution_dsl: Optional[str] = None
    task_submission_ts: str = ''
    task_completion_timeline: Dict[str, Any] = field(default_factory=dict)
    task_execution_mode: str = ''
    task_behavior_dsl_map: Dict[str, Any] = field(default_factory=dict)
    task_contracts_map: Dict[str, Any] = field(default_factory=dict)
    task_verification_subject_id: str = ''
    task_job_submission_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskEntry":
        return cls(
            task_id=data.get("task_id", ""),
            task_goal=data.get("task_goal", ""),
            task_intent=data.get("task_intent", ""),
            task_priority_value=data.get("task_priority_value", 0),
            task_streeability_data=data.get("task_streeability_data", {}),
            task_knowledgebase_ptr=data.get("task_knowledgebase_ptr"),
            submitter_subject_id=data.get("submitter_subject_id", ""),
            task_op_convertor_dsl_id=data.get("task_op_convertor_dsl_id"),
            task_execution_dsl=data.get("task_execution_dsl"),
            task_submission_ts=data.get("task_submission_ts", ""),
            task_completion_timeline=data.get("task_completion_timeline", {}),
            task_execution_mode=data.get("task_execution_mode", ""),
            task_behavior_dsl_map=data.get("task_behavior_dsl_map", {}),
            task_contracts_map=data.get("task_contracts_map", {}),
            task_verification_subject_id=data.get("task_verification_subject_id", ""),
            task_job_submission_data=data.get("task_job_submission_data", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubTaskEntry:
    sub_task_id: str
    task_id: str
    sub_task_goal: str
    sub_task_intent: str
    sub_task_priority_value: int
    sub_task_streeability_data: Dict[str, Any] = field(default_factory=dict)
    sub_task_knowledgebase_ptr: Optional[str] = None
    parent_subject_ids: List[str] = field(default_factory=list)
    parent_input_data_ptr: Optional[str] = None
    assigned_subject_ids: List[str] = field(default_factory=list)
    sub_task_submission_ts: str = ''
    sub_task_completion_timeline: Dict[str, Any] = field(default_factory=dict)
    sub_task_behavior_dsl_map: Dict[str, Any] = field(default_factory=dict)
    sub_task_contracts_map: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubTaskEntry":
        return cls(
            sub_task_id=data.get("sub_task_id", ""),
            task_id=data.get("task_id", ""),
            sub_task_goal=data.get("sub_task_goal", ""),
            sub_task_intent=data.get("sub_task_intent", ""),
            sub_task_priority_value=data.get("sub_task_priority_value", 0),
            sub_task_streeability_data=data.get("sub_task_streeability_data", {}),
            sub_task_knowledgebase_ptr=data.get("sub_task_knowledgebase_ptr"),
            parent_subject_ids=data.get("parent_subject_ids", []),
            parent_input_data_ptr=data.get("parent_input_data_ptr"),
            assigned_subject_ids=data.get("assigned_subject_ids", []),
            sub_task_submission_ts=data.get("sub_task_submission_ts", ""),
            sub_task_completion_timeline=data.get("sub_task_completion_timeline", {}),
            sub_task_behavior_dsl_map=data.get("sub_task_behavior_dsl_map", {}),
            sub_task_contracts_map=data.get("sub_task_contracts_map", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskOutputs:
    task_id: str
    task_output_ptr: Optional[str] = None
    task_output_template_id: Optional[str] = None
    task_output_streaming_channel: Optional[str] = None
    task_assets_data_map: Dict[str, Any] = field(default_factory=dict)
    ts: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskOutputs":
        return cls(
            task_id=data.get("task_id", ""),
            task_output_ptr=data.get("task_output_ptr"),
            task_output_template_id=data.get("task_output_template_id"),
            task_output_streaming_channel=data.get("task_output_streaming_channel"),
            task_assets_data_map=data.get("task_assets_data_map", {}),
            ts=data.get("ts", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubTaskOutputs:
    sub_task_id: str
    sub_task_output_ptrs: List[str] = field(default_factory=list)
    sub_task_output_template_ids: List[str] = field(default_factory=list)
    sub_task_assets_data_map: Dict[str, Any] = field(default_factory=dict)
    ts: str = ''
    subject_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubTaskOutputs":
        return cls(
            sub_task_id=data.get("sub_task_id", ""),
            sub_task_output_ptrs=data.get("sub_task_output_ptrs", []),
            sub_task_output_template_ids=data.get("sub_task_output_template_ids", []),
            sub_task_assets_data_map=data.get("sub_task_assets_data_map", {}),
            ts=data.get("ts", ""),
            subject_ids=data.get("subject_ids", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskStatus:
    task_id: str
    current_status: str
    latest_update_ts: str
    logging_stream_ws: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskStatus":
        return cls(
            task_id=data.get("task_id", ""),
            current_status=data.get("current_status", ""),
            latest_update_ts=data.get("latest_update_ts", ""),
            logging_stream_ws=data.get("logging_stream_ws")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubTaskStatus:
    sub_task_id: str
    current_status: str
    latest_update_ts: str
    logging_stream_ws: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubTaskStatus":
        return cls(
            sub_task_id=data.get("sub_task_id", ""),
            current_status=data.get("current_status", ""),
            latest_update_ts=data.get("latest_update_ts", ""),
            logging_stream_ws=data.get("logging_stream_ws")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskACLMapping:
    task_id: str
    task_allowed_functions_list: List[str] = field(default_factory=list)
    task_allowed_actions_list: List[str] = field(default_factory=list)
    task_allowed_tools_list: List[str] = field(default_factory=list)
    task_allowed_lims_list: List[str] = field(default_factory=list)
    tasks_credentials_map: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskACLMapping":
        return cls(
            task_id=data.get("task_id", ""),
            task_allowed_functions_list=data.get("task_allowed_functions_list", []),
            task_allowed_actions_list=data.get("task_allowed_actions_list", []),
            task_allowed_tools_list=data.get("task_allowed_tools_list", []),
            task_allowed_lims_list=data.get("task_allowed_lims_list", []),
            tasks_credentials_map=data.get("tasks_credentials_map", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubTaskReviewData:
    sub_task_id: str
    review_subject_ids: List[str] = field(default_factory=list)
    review_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubTaskReviewData":
        return cls(
            sub_task_id=data.get("sub_task_id", ""),
            review_subject_ids=data.get("review_subject_ids", []),
            review_data=data.get("review_data", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskReviewData:
    task_id: str
    review_subject_ids: List[str] = field(default_factory=list)
    review_data: Dict[str, Any] = field(default_factory=dict)
    ts: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskReviewData":
        return cls(
            task_id=data.get("task_id", ""),
            review_subject_ids=data.get("review_subject_ids", []),
            review_data=data.get("review_data", {}),
            ts=data.get("ts", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
