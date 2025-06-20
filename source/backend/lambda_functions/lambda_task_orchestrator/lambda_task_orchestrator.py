#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import traceback
import cmf_boto
from boto3.dynamodb.conditions import Key, Attr
import botocore
from datetime import datetime, timezone
from cmf_logger import logger
import os
import json
from cmf_utils import send_anonymous_usage_data, publish_event
from cmf_pipeline import TaskExecutionStatus, STATUS_OK_TO_PROCEED, STATUS_OK_TO_RETRY, update_task_execution_status, get_task_execution_status
from cmf_types import NotificationDetailType, NotificationType

lambda_client = cmf_boto.client('lambda')
eventsClient = cmf_boto.client('events')
ssm_client = cmf_boto.client('ssm')

task_executions_table_name = os.environ['TASK_EXECUTIONS_TABLE_NAME']
task_executions_table = cmf_boto.resource('dynamodb').Table(task_executions_table_name)

pipelines_table_name = os.environ['PIPELINES_TABLE_NAME']
pipelines_table = cmf_boto.resource('dynamodb').Table(pipelines_table_name)

ssm_scripts_table_name = os.environ['SCRIPTS_TABLE_NAME']
ssm_scripts_table = cmf_boto.resource('dynamodb').Table(ssm_scripts_table_name)

application = os.environ['application']
environment = os.environ['environment']
eventBusName = os.environ["EVENT_BUS_NAME"]
eventSource = f'{application}-{environment}-task-orchestrator'

EMAIL_SCRIPT_NAME = 'Send Email'

SSM_AUTOMATION_DOCUMENT = 'SSM Automation Document'
class ScriptNotFound(Exception):
    pass


class PipelineNoTasks(Exception):
    pass

class InvokeLambdaFailure(Exception):
    pass


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


def update_pipeline_status(pipeline_id, pipeline_status: TaskExecutionStatus, current_task_id=None):
    pipeline_status_str = pipeline_status.value
    update_expr = 'SET #pipeline_status = :pipeline_status, #_history.#lastModifiedTimestamp = :lastModifiedTimestamp'
    update_expr_attribute_names = {
        '#pipeline_status': 'pipeline_status',
        '#lastModifiedTimestamp': 'lastModifiedTimestamp',
        '#_history': '_history'
    }
    update_expr_attribute_values = {
        ':pipeline_status': pipeline_status_str,
        ':lastModifiedTimestamp': datetime.now(timezone.utc).isoformat()
    }

    if current_task_id is not None:
        update_expr = update_expr + ', #current_task_id = :current_task_id'
        update_expr_attribute_names['#current_task_id'] = 'current_task_id'
        update_expr_attribute_values[':current_task_id'] = current_task_id

    try:
        pipelines_table.update_item(
            Key={
                'pipeline_id': pipeline_id
            },
            UpdateExpression=update_expr,
            ExpressionAttributeNames=update_expr_attribute_names,
            ExpressionAttributeValues=update_expr_attribute_values,
            ConditionExpression='attribute_exists(pipeline_id)'
        )
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            logger.info("Pipeline already deleted")
        else:
            raise e

def query_task_executions(pipeline_id):

    response = task_executions_table.query(
        IndexName='pipeline_id-index',
        KeyConditionExpression=Key('pipeline_id').eq(pipeline_id)
    )

    query_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluated key is " + str(response['LastEvaluatedKey']))
        response = task_executions_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        query_data.extend(response['Items'])
    return query_data


def get_pipeline_template_id(pipeline_id):
    pipeline = pipelines_table.get_item(Key={'pipeline_id': pipeline_id})
    if 'Item' not in pipeline:
        return None
    return pipeline['Item']['pipeline_template_id']


def get_task_execution(task_execution_id):
    try:
        response = task_executions_table.get_item(Key={'task_execution_id': task_execution_id})
        if 'Item' not in response:
            return None
        else:
            return response['Item']
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None


def get_script(ssm_script_name, ssm_script_version):
    response = ssm_scripts_table.scan(FilterExpression=Attr('script_name').eq(ssm_script_name) & Attr('version').eq(ssm_script_version))
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        logger.info("Last Evaluated key is " + str(response['LastEvaluatedKey']))
        response = ssm_scripts_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])
    if len(scan_data) < 1:
        raise ScriptNotFound(f'No SSM scripts found with name: {ssm_script_name}')
    # all versions for the script should have same package_uuid
    return scan_data[0]


def sync_invoke_lambda(lambda_func_name, payload):
    logger.info(f'Invoking {lambda_func_name} with event: {payload}')
    try:
        response = lambda_client.invoke(FunctionName=lambda_func_name,
                                        InvocationType='RequestResponse',
                                        Payload=payload)
        logger.info(response)
        return response
    except Exception as e:
        logger.error(f'Failure invoking lambda function: {lambda_func_name}: {e}')
        raise InvokeLambdaFailure(f'Failure invoking lambda function: {lambda_func_name}: {e}')

def create_notification(task, task_execution, status) -> NotificationType: 
    notification: NotificationType = NotificationType(
        type = status,
        pipeline_id= task_execution.get('pipeline_id'),
        task_name=task_execution.get('task_execution_name'),
        task_id=task_execution.get('task_id'),
        lambda_function_name_suffix= task.get('lambda_function_name_suffix'),
        timestamp=datetime.now(timezone.utc).isoformat(sep='T'),
        uuid= task.get('package_uuid')
    )
    
    # Only add script-related fields for Automated tasks
    if task.get('type') == 'Automated':
        notification.update({
            'ssm_script_name': task.get('script_name'),
            'ssm_script_version': str(task.get('version', '1'))
        })

    return notification


def handle_lambda_based_task_execution(task, task_execution, auth_context):
    task_execution_id = task_execution['task_execution_id']
    update_task_execution_status(task_execution_id, TaskExecutionStatus.IN_PROGRESS)

    logger.info(f'{task_execution_id} is lambda based automation task. Invoking relevant lambda function...')

    automation_event = {
        'requestContext': auth_context,
        'httpMethod': 'POST',
        'body': json.dumps({
            **task_execution['task_execution_inputs'],
            'task_execution_id': task_execution_id,
            'action': task['script_name']
        }, cls=JsonEncoder)
    }

    automation_lambda_func_name = f'{application}-{environment}-{task["lambda_function_name_suffix"]}'

    try:
        response = sync_invoke_lambda(automation_lambda_func_name, json.dumps(automation_event, cls=JsonEncoder))

        # 200 StatusCode only guarantees a successful invocation but not successful execution on the invoked lambda
        if response['StatusCode'] != 200:
            update_task_execution_status(task_execution_id, TaskExecutionStatus.FAILED)

    except InvokeLambdaFailure:
        update_task_execution_status(task_execution_id, TaskExecutionStatus.FAILED)


def handle_ssm_script_based_task_execution(task, task_execution, auth_context):
    task_execution_id = task_execution['task_execution_id']
    ssm_script_name = task['script_name']
    ssm_script_version = task['version']
    logger.info(f'task execution: {task_execution}')
    update_task_execution_status(task_execution_id, TaskExecutionStatus.IN_PROGRESS)
    
    script = get_script(ssm_script_name, ssm_script_version)
    script_arg_names = [arg['name'] for arg in script['script_arguments']]
    # Extract only inputs that are required for this script.
    script_arguments = {k: v for k,v in task_execution['task_execution_inputs'].items() if k in script_arg_names}

    
    # Handle send email automations. 
    # Publishing an event of this type will allow us to send emails with customized body.
    if ssm_script_name == EMAIL_SCRIPT_NAME:
        notification: NotificationType = create_notification(task, task_execution, NotificationDetailType.TASK_SEND_EMAIL.value)
        notification['content'] = script_arguments
        update_task_execution_status(task_execution_id, TaskExecutionStatus.COMPLETE) # Marking this task complete does not guarantee delivery of emails to users
        publish_event(notification, eventsClient, eventSource, eventBusName)
        return

    # Direct SSM Document does not have a mi_id associated with it
    if script.get('compute_platform', None) == SSM_AUTOMATION_DOCUMENT:
        event_body_script_arguments = script_arguments
    else:
       event_body_script_arguments = {**script_arguments, 'mi_id': task_execution['task_execution_inputs']['mi_id']}

    automation_event = {
        'httpMethod': 'POST',
        'requestContext': auth_context,
        'body': json.dumps({
            'jobname': task_execution_id,
            'script': {
                "package_uuid": script['package_uuid'],
                "script_version": str(ssm_script_version),
                "script_arguments": event_body_script_arguments
            }
        }, cls=JsonEncoder)
    }

    automation_lambda_func_name = f'{application}-{environment}-{task["lambda_function_name_suffix"]}'
    try:
        logger.info(f'{task_execution_id} is a ssm script based automation task. Invoking lambda_ssm..')
        response = sync_invoke_lambda(automation_lambda_func_name, json.dumps(automation_event, cls=JsonEncoder))

        # 200 StatusCode only guarantees a successful invocation but not successful execution on the invoked lambda
        if response['StatusCode'] != 200:
            update_task_execution_status(task_execution_id, TaskExecutionStatus.FAILED)
    except InvokeLambdaFailure:
        update_task_execution_status(task_execution_id, TaskExecutionStatus.FAILED)



def handle_manual_task_execution(task, task_execution):
    task_execution_id = task_execution['task_execution_id']
    logger.info(f'{task_execution_id} is a manual task. Moving the task execution status to Pending Approval')
    update_task_execution_status(task_execution_id, TaskExecutionStatus.PENDING_APPROVAL)
    notification: NotificationType = create_notification(task, task_execution, NotificationDetailType.TASK_MANUAL_APPROVAL.value)
    publish_event(notification, eventsClient, eventSource, eventBusName)


def update_predecessors(task_executions):
    successors_to_predecessors_task_dict = {}
    for task_execution in task_executions:
        for task_successor in task_execution.get('task_successors', []):
            if task_successor in successors_to_predecessors_task_dict:
                # Append additional predecessor
                successors_to_predecessors_task_dict[task_successor].append(task_execution['task_execution_id'])
            else:
                # First predecessor
                successors_to_predecessors_task_dict[task_successor] = [task_execution['task_execution_id']]

    for task_execution in task_executions:
        task_execution['__task_predecessors'] = successors_to_predecessors_task_dict.get(task_execution['task_execution_id'],None)


# Check that the successors, predecessors are complete.
def check_successors_predecessors_complete(all_task_executions, task_execution_id):
    update_predecessors(all_task_executions)
    # Find current task
    current_task_execution = [task for task in all_task_executions if task['task_execution_id'] == task_execution_id]

    incomplete_predecessors_tasks = []
    ready_successor_tasks = []
    already_processed_successor_tasks = []
    abandon_successor_tasks = []

    if len(current_task_execution) > 0:
        for successor_task_id in current_task_execution[0].get('task_successors', []):
            successor_task_execution = [task for task in all_task_executions if
                                        task['task_execution_id'] == successor_task_id]

            successor_task_execution_status = get_task_execution_status(successor_task_execution[0])
            # check that successor task is not started if not then do not start it again.
            if successor_task_execution_status != TaskExecutionStatus.NOT_STARTED:
                already_processed_successor_tasks.append(successor_task_execution[0]['task_execution_id'])
                continue
            # check that all it's predecessors are complete
            if successor_task_execution[0].get('__task_predecessors', None):
                predecessors_tasks = filter_tasks(all_task_executions, successor_task_execution[0].get('__task_predecessors', []))
                successor_incomplete_predecessors_tasks = get_incomplete_predecessors(predecessors_tasks)
                    
                if all(get_task_execution_status(task) == TaskExecutionStatus.ABANDONED for task in predecessors_tasks):
                    abandon_successor_tasks.append(successor_task_execution[0]['task_execution_id'])
                elif len(successor_incomplete_predecessors_tasks) == 0:
                    ready_successor_tasks.append(successor_task_execution[0]['task_execution_id'])
                else:
                    incomplete_predecessors_tasks.extend(successor_incomplete_predecessors_tasks)
    else:
        logger.error(f'{task_execution_id} not found in tasks in pipeline.')

    return incomplete_predecessors_tasks, ready_successor_tasks, already_processed_successor_tasks, abandon_successor_tasks

# Check if all tasks in the pipeline are in a STATUS_OK_TO_PROCEED.
def is_pipeline_complete(all_task_executions):
    completed_branch_task_ids = []
    incomplete_branch_task_ids = []
    for task in all_task_executions:
        if len(task.get('task_successors', [])) == 0 and get_task_execution_status(task) in STATUS_OK_TO_PROCEED:
            # last task in branch and branch is complete.
            completed_branch_task_ids.append(task['task_execution_id'])
        elif len(task.get('task_successors', [])) == 0 and get_task_execution_status(task) not in STATUS_OK_TO_PROCEED:
            # Found a task that is the last in a branch and not complete.
            incomplete_branch_task_ids.append(task['task_execution_id'])

    if len(incomplete_branch_task_ids) > 0:
        pipeline_complete = False
    else:
        pipeline_complete = True

    logger.debug(f'Pipeline will be complete when the tasks: {incomplete_branch_task_ids} are in one of the following status codes {STATUS_OK_TO_PROCEED}')

    return pipeline_complete, incomplete_branch_task_ids, completed_branch_task_ids

# Check if all end tasks in the pipeline are in ABANDONED state
def is_pipeline_abandoned(all_task_executions):
    end_tasks = [task for task in all_task_executions if len(task.get('task_successors', [])) == 0]
    
    # If there are no end tasks, we can't determine if pipeline should be abandoned
    if not end_tasks:
        return False
    
    # Check if all end tasks are in ABANDONED state
    all_abandoned = all(get_task_execution_status(task) == TaskExecutionStatus.ABANDONED for task in end_tasks)
    
    # Check if any end task is in COMPLETE state
    any_complete = any(get_task_execution_status(task) == TaskExecutionStatus.COMPLETE for task in end_tasks)
    
    # If all end tasks are abandoned and none are complete, pipeline should be abandoned
    return all_abandoned and not any_complete


def get_incomplete_predecessors(predecessors_tasks):
    incomplete_predecessors_tasks = []

    for predecessors_task in predecessors_tasks:
        if get_task_execution_status(predecessors_task) is not None and get_task_execution_status(predecessors_task) not in STATUS_OK_TO_PROCEED:
            incomplete_predecessors_tasks.append(predecessors_task['task_execution_id'])

    return incomplete_predecessors_tasks


def filter_tasks(all_task_executions, execution_task_ids):
    return [task for task in all_task_executions if task['task_execution_id'] in execution_task_ids]


def get_root_tasks(pipeline_id):
    task_executions = query_task_executions(pipeline_id)

    task_successor_ids = []
    for task_execution in task_executions:
        task_successor_ids.extend(task_execution.get('task_successors',None))

    root_tasks = []
    for task_execution in task_executions:
        if task_execution['task_execution_id'] not in task_successor_ids:
            root_tasks.append(task_execution)

    return root_tasks


def get_execution_tasks(task_execution_ids):
    task_executions = []
    for task_execution_id in task_execution_ids:
        task_execution = get_task_execution(task_execution_id)
        task_executions.append(task_execution)

    update_predecessors(task_executions)

    return task_executions


def handle_task_executions(pipeline_id, tasks_execution):
    for task_execution in tasks_execution:
        if task_execution:
            handle_task_execution(pipeline_id, task_execution)
        else:
            logger.warning(f'Task not found {task_execution}')
            update_pipeline_status(pipeline_id, TaskExecutionStatus.COMPLETE)

def handle_task_execution(pipeline_id, task_execution):
    # presence of task with given task_execution is already validated prior to this call
    task_id = task_execution['task_id']
    task_version = task_execution['task_version']
    task = ssm_scripts_table.get_item(Key={'package_uuid': task_id, 'version' : int(task_version)})['Item']

    update_pipeline_status(pipeline_id, TaskExecutionStatus.IN_PROGRESS, task_id)

    history = pipelines_table.get_item(Key={'pipeline_id': pipeline_id})['Item']['_history']
    auth_context = {
        'authorizer': {
            'claims': {
                'cognito:groups': ['orchestrator'],
                'email': history['createdBy']['email'],
                'cognito:username': history['createdBy']['userRef']
            }
        }
    }

    if task['type'] == 'Automated':
        if "lambda_function_name_suffix" in task and task['lambda_function_name_suffix'] == 'ssm':
            handle_ssm_script_based_task_execution(task, task_execution, auth_context)
        else:
            handle_lambda_based_task_execution(task, task_execution, auth_context)
    elif task['type'] == 'Manual':
        handle_manual_task_execution(task, task_execution)



def process_pipeline_event(dynamodb_record):
    if 'OldImage' not in dynamodb_record:
        logger.info('Received pipeline creation event')
        logger.info('Ignoring this event and waiting for pipeline to complete provisioning all task executions')
    elif 'NewImage' not in dynamodb_record:
        logger.info('Received pipeline deletion event')
        logger.info('No further action as relevant task executions will be deleted')
    elif dynamodb_record['NewImage']['pipeline_status']['S'] == TaskExecutionStatus.NOT_STARTED.value and \
            dynamodb_record['OldImage']['pipeline_status']['S'] == 'Provisioning':
        logger.info('Pipeline is provisioned and ready for processing')

        pipeline_id = dynamodb_record['NewImage']['pipeline_id']['S']

        root_tasks = get_root_tasks(pipeline_id)

        if root_tasks:
            handle_task_executions(pipeline_id, root_tasks)
        else:
            update_pipeline_status(pipeline_id, TaskExecutionStatus.FAILED)
            logger.warning(f'No tasks founds for pipeline: {pipeline_id}')


def is_valid_failed_update(old_task_execution_status: TaskExecutionStatus, new_task_execution_status: TaskExecutionStatus):
    return old_task_execution_status != TaskExecutionStatus.IN_PROGRESS and new_task_execution_status == TaskExecutionStatus.FAILED


def is_valid_update(old_task_execution_status: TaskExecutionStatus, new_task_execution_status: TaskExecutionStatus):
     return (old_task_execution_status in [TaskExecutionStatus.IN_PROGRESS, TaskExecutionStatus.PENDING_APPROVAL] and new_task_execution_status == TaskExecutionStatus.COMPLETE) or (old_task_execution_status == TaskExecutionStatus.FAILED and new_task_execution_status == TaskExecutionStatus.SKIPPED)


def is_valid_retry(old_task_execution_status: TaskExecutionStatus, new_task_execution_status: TaskExecutionStatus):
    return old_task_execution_status in STATUS_OK_TO_RETRY and new_task_execution_status == TaskExecutionStatus.RETRY

def is_valid_abandon(old_task_execution_status: TaskExecutionStatus, new_task_execution_status: TaskExecutionStatus):
    return (old_task_execution_status in [TaskExecutionStatus.NOT_STARTED, TaskExecutionStatus.PENDING_APPROVAL] and new_task_execution_status == TaskExecutionStatus.ABANDONED)


def process_task_execution_event(dynamodb_record):
    if 'OldImage' not in dynamodb_record or 'NewImage' not in dynamodb_record:
        logger.info('Received Task Execution creation or deletion event. Ignoring..')
        return

    new_dynamodb_record = dynamodb_record['NewImage']
    logger.info(new_dynamodb_record)
    task_execution_id = new_dynamodb_record['task_execution_id']['S']
    new_task_execution_status = TaskExecutionStatus(new_dynamodb_record['task_execution_status']['S'])
    old_task_execution_status = TaskExecutionStatus(dynamodb_record['OldImage']['task_execution_status']['S'])

    pipeline_id = new_dynamodb_record['pipeline_id']['S']

    if new_task_execution_status == TaskExecutionStatus.FAILED:
        task_execution = get_task_execution(task_execution_id)
        task_id = task_execution['task_id']
        task_version = task_execution['task_version']
        task = ssm_scripts_table.get_item(Key={'package_uuid': task_id, 'version' : int(task_version)})['Item']
        notification: NotificationType = create_notification(task, task_execution, NotificationDetailType.TASK_FAILED.value)
        publish_event(notification, eventsClient, eventSource, eventBusName)

    if is_valid_failed_update(old_task_execution_status, new_task_execution_status):
        logger.info(f'Received failed update for {task_execution_id}')
        update_pipeline_status(pipeline_id, TaskExecutionStatus.FAILED)
    elif is_valid_update(old_task_execution_status, new_task_execution_status):
        logger.info(f'Received task {new_task_execution_status} update for {task_execution_id}')

        # Get all pipeline tasks for evaluation.
        all_task_executions = query_task_executions(pipeline_id)

        # get successor tasks based on the currently processing task id.
        incomplete_predecessor_task_ids, ready_successor_task_ids, already_processed_successor_tasks, _ = check_successors_predecessors_complete(all_task_executions, task_execution_id)

        if len(ready_successor_task_ids) > 0:
            logger.info(f'All predecessors complete for {", ".join(ready_successor_task_ids)} starting task.')
            task_execution_successors = get_execution_tasks(ready_successor_task_ids)
            handle_task_executions(pipeline_id, task_execution_successors)

        if len(incomplete_predecessor_task_ids) > 0:
            logger.info(f'Waiting on predecessors: {",".join(incomplete_predecessor_task_ids)}')

        if len(already_processed_successor_tasks) > 0:
            logger.warning(f'Successors will not be processed, as already in state other than {TaskExecutionStatus.NOT_STARTED}: {",".join(incomplete_predecessor_task_ids)}')

        pipeline_complete, _, _ = is_pipeline_complete(all_task_executions)

        if pipeline_complete:
            logger.info(f'Pipeline Id: {pipeline_id} is complete.')
            update_pipeline_status(pipeline_id, TaskExecutionStatus.COMPLETE)
            send_anonymous_usage_data('PipelineComplete')
    elif is_valid_retry(old_task_execution_status, new_task_execution_status):
        logger.info(f'Retrying previously task execution {task_execution_id}')
        task_execution = get_task_execution(task_execution_id)
        handle_task_execution(pipeline_id, task_execution)
    elif is_valid_abandon(old_task_execution_status, new_task_execution_status):
        # Get all pipeline tasks for evaluation.
        all_task_executions = query_task_executions(pipeline_id)
        abandon_successor_tasks = check_successors_predecessors_complete(all_task_executions, task_execution_id)[3]
        if len(abandon_successor_tasks) > 0:
            for task_id in abandon_successor_tasks:
                logger.info(f'Abandoning task execution: {task_id}')
                update_task_execution_status(task_id, TaskExecutionStatus.ABANDONED)
        
        # After abandoning tasks, check if the pipeline should be marked as complete or abandoned
        all_task_executions = query_task_executions(pipeline_id)  # Refresh task executions after updates
        pipeline_complete, _, _ = is_pipeline_complete(all_task_executions)
        
        if pipeline_complete:
            # Check if pipeline should be marked as abandoned (all end tasks are abandoned)
            if is_pipeline_abandoned(all_task_executions):
                logger.info(f'Pipeline Id: {pipeline_id} is being marked as Abandoned as all end tasks are abandoned.')
                update_pipeline_status(pipeline_id, TaskExecutionStatus.ABANDONED)
            else:
                logger.info(f'Pipeline Id: {pipeline_id} is complete.')
                update_pipeline_status(pipeline_id, TaskExecutionStatus.COMPLETE)
                send_anonymous_usage_data('PipelineComplete')


def lambda_handler(event, _):
    for record in event ['Records']:
        dynamodb_record = record['dynamodb']
        event_source = record['eventSourceARN']
        logger.info(f'Event source is {event_source}')
        logger.info(dynamodb_record)

        try:
            if 'pipelines' in event_source:
                process_pipeline_event(dynamodb_record)
            elif 'task_executions' in event_source:
                process_task_execution_event(dynamodb_record)
        except Exception as task_error:
            # Catch all errors produced in processing to stop exception being passed to stream causing duplication of event.
            # Stream processing for the update is most likely not been processed.
            logger.error(task_error)
            traceback.print_exc()
