import botocore
from datetime import datetime, timezone
from enum import Enum
import os

import cmf_boto
from cmf_logger import logger

application = os.environ["application"]
environment = os.environ["environment"]
task_executions_table_name = '{}-{}-task_executions'.format(application, environment)
dynamodb = cmf_boto.resource("dynamodb")
task_executions_table = dynamodb.Table(task_executions_table_name)

class TaskExecutionStatus(Enum):
    COMPLETE = "Complete"
    IN_PROGRESS = "In Progress"
    FAILED = "Failed"
    PENDING_APPROVAL = "Pending Approval"
    NOT_STARTED = "Not Started"
    SKIPPED = "Skip"
    RETRY = "Retry"

STATUS_OK_TO_PROCEED = [TaskExecutionStatus.COMPLETE, TaskExecutionStatus.SKIPPED]
STATUS_OK_TO_RETRY = [TaskExecutionStatus.COMPLETE, TaskExecutionStatus.SKIPPED, TaskExecutionStatus.FAILED]

def update_task_execution_output(task_execution_id, last_output_message, output):
    update_expr =  'SET #outputLastMessage = :outputLastMessage, #output = :output'
    update_expr_attributes = {
        '#outputLastMessage': 'outputLastMessage',
        '#output': 'output'
    }
    update_attribute_values = {
        ':outputLastMessage': last_output_message,
        ':output': output
    }
    update_task_execution(task_execution_id, update_expr, update_expr_attributes, update_attribute_values)
    
def get_task_execution_status(task_execution):
    status_str = task_execution.get('task_execution_status', '{not-set}')
    if status_str == '{not-set}':
        return None
    try:
        return TaskExecutionStatus(status_str)
    except ValueError:
        logger.warning(f"Invalid task execution status: {status_str}")
        return None 

def update_task_execution_status(task_execution_id, status: TaskExecutionStatus):
    update_expr = 'SET #task_execution_status = :task_execution_status'
    update_expr_attributes = {
        '#task_execution_status': 'task_execution_status'
    }
    update_attribute_values = {
        ':task_execution_status': status.value,
    }
    update_task_execution(task_execution_id, update_expr, update_expr_attributes, update_attribute_values)


def update_task_execution(task_execution_id, update_expr, update_expr_attributes, update_attribute_values):
    # Add history elements to update
    update_expr  = update_expr + ', #_history.#lastModifiedTimestamp = :lastModifiedTimestamp, #_history.#lastModifiedBy = :lastModifiedBy'
    update_expr_attributes['#lastModifiedTimestamp'] = 'lastModifiedTimestamp'
    update_expr_attributes['#lastModifiedBy'] = 'lastModifiedBy'
    update_expr_attributes['#_history'] = '_history'
    update_attribute_values[':lastModifiedTimestamp'] = datetime.now(timezone.utc).isoformat()
    update_attribute_values[':lastModifiedBy'] = {
        "email": "[system]"
    }

    try:
        task_executions_table.update_item(
            Key={
                'task_execution_id': task_execution_id
            },
            UpdateExpression=update_expr,
            ExpressionAttributeNames=update_expr_attributes,
            ExpressionAttributeValues=update_attribute_values,
            ConditionExpression='attribute_exists(task_execution_id)'
        )
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            logger.info(f'Task execution no longer exists {task_execution_id}')
        else:
            raise RuntimeError(f'Error updating task execution {task_execution_id}') from e