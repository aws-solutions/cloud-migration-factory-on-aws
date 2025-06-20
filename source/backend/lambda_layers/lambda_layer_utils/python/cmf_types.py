from enum import Enum
from typing import TypedDict, List

class NotificationDetailType(Enum):
    TASK_PENDING = "TaskPending"
    TASK_TIMED_OUT = "TaskTimedOut"
    TASK_FAILED = "TaskFailed"
    TASK_SUCCESS = "TaskSuccess"
    TASK_MANUAL_APPROVAL = "TaskManualApprovalNeeded"
    TASK_SEND_EMAIL = "EmailAutomationTaskType"


class NotificationType(TypedDict, total=False):
    type: str
    pipeline_template_id: str
    pipeline_id: str
    task_name: str
    pipeline_name: str
    task_id: str
    lambda_function_name_suffix: str
    ssm_script_name: str
    ssm_script_version: str
    dismissible: bool
    header: str
    content: str
    timestamp: str
    uuid: str

class NotificationEvent(TypedDict):
    version: str
    id: str
    detail_type: NotificationDetailType
    source: str
    account: str
    time: str
    region: str
    resources: list[str]
    detail: NotificationType

class CognitoGroupInfo(TypedDict):
    group_name: str

class TaskEmailConfig(TypedDict):
    email_body: str
    email_groups: List[CognitoGroupInfo]
    email_users: List[str]
    task_id: str
    enabled: bool
    override_defaults: bool

class Pipeline(TypedDict, total=False):  # total=False allows optional fields
    pipeline_id: str
    current_task_id: str
    default_email_groups: List[CognitoGroupInfo]
    default_email_recipients: List[str]
    description: str
    enable_email_notifications: bool
    name: str
    task_level_email_settings: List[TaskEmailConfig]