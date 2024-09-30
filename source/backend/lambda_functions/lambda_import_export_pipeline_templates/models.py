from typing import TypedDict, Optional, List


class PipelineTemplateTask(TypedDict):
    pipeline_template_task_id: str
    pipeline_template_task_name: str
    pipeline_template_id: str
    task_id: Optional[str]
    task_name: Optional[str]
    task_successors: List[str]
    _history: dict


class PipelineTemplate(TypedDict):
    pipeline_template_id: str
    pipeline_template_description: str
    pipeline_template_name: str
    pipeline_template_tasks: Optional[List[PipelineTemplateTask]]
    _history: dict


class ClientException(Exception):
    def __init__(self, error: str, message: str, status_code: int = 400):
        self.error = error
        self.message = message
        self.status_code = status_code
