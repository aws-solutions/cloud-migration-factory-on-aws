import json
import os
import traceback
from decimal import Decimal
from json import JSONDecodeError
from typing import Iterable
import uuid
import copy

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from mypy_boto3_dynamodb.service_resource import Table

import cmf_boto
import item_validation
from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers
from models import PipelineTemplate, PipelineTemplateTask, ClientException

application = os.environ['application']
environment = os.environ['environment']
pipeline_templates_table_name = '{}-{}-'.format(application, environment) + 'pipeline_templates'
pipeline_template_tasks_table_name = '{}-{}-'.format(application, environment) + 'pipeline_template_tasks'
PIPELINE_TEMPLATE_SCHEMA = 'pipeline_template'

lambda_client = cmf_boto.client('lambda')


def lambda_handler(e, _=None):
    log_event_received(e)

    event = APIGatewayProxyEvent(e)

    try:
        if event.http_method == 'GET':
            return process_get(event)
        elif event.http_method == 'POST':
            return process_post(event, e['requestContext'])
        else:
            raise ClientException('MethodNotAllowed', 'Method Not Allowed', 405)

    # catch intentional exceptions thrown by this lambda code and map to error response
    except ClientException as error:
        logger.error(f"Error: {error}")
        logger.error(traceback.format_exc())
        body = error.error
        return {
            'statusCode': error.status_code,
            'body': body,
            'headers': default_http_headers,
        }
    # map errors to 400 when client sends invalid body
    except (ValueError, TypeError) as error:
        logger.error(f"Error: {error}")
        logger.error(traceback.format_exc())
        body = error.msg
        return {
            'statusCode': 400,
            'body': body,
            'headers': default_http_headers,
        }
    # map all unexpected exceptions to 500
    except Exception as error:
        logger.error(f"Error: {error}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': "An unexpected error occurred",
            'headers': default_http_headers,
        }


def sanitize_pipeline_templates(templates: Iterable[PipelineTemplate]):
    for pipeline_template in templates:

        pipeline_template.pop('version', None)
        pipeline_template.pop('pipeline_template_id', None)
        pipeline_template.pop('_history', None)

    return templates


def sanitize_pipeline_template_tasks(template_tasks: Iterable[PipelineTemplateTask]):

    for task in template_tasks:
        task.pop('pipeline_template_id', None)
        task.pop('pipeline_template_task_id', None)
        task.pop('_history', None)

    return template_tasks


def process_get(event: APIGatewayProxyEvent):
    pipeline_template_ids: list[str] = event.multi_value_query_string_parameters.get('pipeline_template_id', [])

    pipeline_templates = get_all_pipeline_templates()
    tasks = get_all_pipeline_template_tasks()
    all_scripts = get_scripts()
    no_filter = len(pipeline_template_ids) == 0

    filtered_pipeline_templates = [
        with_tasks(pipeline_template, tasks, all_scripts) for pipeline_template in pipeline_templates
        if no_filter or (pipeline_template['pipeline_template_id'] in pipeline_template_ids)
    ]

    response = {
        'headers': default_http_headers,
        'statusCode': 200,
        'body': json.dumps(filtered_pipeline_templates, cls=JsonEncoder)
    }

    return response


def get_all_pipeline_templates() -> Iterable[PipelineTemplate]:
    pipeline_templates_table: Table = cmf_boto.resource('dynamodb').Table(pipeline_templates_table_name)
    pipeline_templates = item_validation.scan_dynamodb_data_table(pipeline_templates_table)
    return sorted(pipeline_templates, key=lambda it: it['pipeline_template_name'])


def get_all_pipeline_template_tasks() -> Iterable[PipelineTemplateTask]:
    tasks_table: Table = cmf_boto.resource('dynamodb').Table(pipeline_template_tasks_table_name)
    tasks = item_validation.scan_dynamodb_data_table(tasks_table)
    return sorted(tasks, key=lambda it: it['pipeline_template_task_name'])


def with_tasks(pipeline_template: PipelineTemplate, all_tasks: Iterable[PipelineTemplateTask], all_scripts=None) -> dict:
    tasks_for_this_template = [task for task in all_tasks if
                               task['pipeline_template_id'] == pipeline_template['pipeline_template_id']]

    if all_scripts:
        #     Resolve task_ids to names
        for task in tasks_for_this_template:
            scripts = get_script_by_id(task['task_id'], all_scripts)
            if len(scripts) > 0:
                task['task_name'] = scripts[0].get('script_name')
                task.pop('task_id', None)
    return {
        **pipeline_template,
        'pipeline_template_tasks': tasks_for_this_template
    }


def process_post(event: APIGatewayProxyEvent, request_context):
    pipeline_templates = json.loads(event.body)
    if not isinstance(pipeline_templates, list):
        raise ClientException('ValidationError', 'Invalid request body')

    if not pipeline_templates:
        return {
            'statusCode': 201,
            'body': 'No template data provided.'
        }

    sanitized_pipeline_templates = sanitize_pipeline_templates(pipeline_templates)

    all_scripts = get_scripts()

    for template in sanitized_pipeline_templates:
        tasks = template.pop('pipeline_template_tasks', [])

        pipeline_template_response_payload = create_pipeline(template, request_context)

        pipeline_template_response_body = json.loads(pipeline_template_response_payload['body'])

        if pipeline_template_response_body.get('errors'):
            return {'statusCode': 401, **pipeline_template_response_payload}

        new_pipeline_template_id = pipeline_template_response_body['newItems'][0][f"{PIPELINE_TEMPLATE_SCHEMA}_id"]

        validation_errors = []
        new_to_old_ids = {}
        # add new ID to task and create dict of old to new mappings for successor update.
        for task in tasks:
            new_id = str(uuid.uuid4())
            new_to_old_ids[task['pipeline_template_task_id']] = new_id
            task['__pipeline_template_task_id'] = new_id

        sanitized_pipeline_template_tasks = sanitize_pipeline_template_tasks(tasks)

        update_task_template_ids(
            new_pipeline_template_id,
            template,
            sanitized_pipeline_template_tasks,
            validation_errors,
            new_to_old_ids,
            all_scripts
        )

        if validation_errors:
            rollback_pipeline_template_import(new_pipeline_template_id, request_context)
            return {
                'statusCode': 401,
                'body': json.dumps({'errors': {'validation_errors': validation_errors}})
            }

        # create write update without related successors to ensure records exist.
        sanitized_pipeline_template_tasks_no_successors = copy.deepcopy(list(sanitized_pipeline_template_tasks))

        for task in sanitized_pipeline_template_tasks_no_successors:
            task.pop('task_successors', None)

        pipeline_template_tasks_response_body, pipeline_template_tasks_response_payload = save_pipeline_task_templates(
            sanitized_pipeline_template_tasks_no_successors,
            request_context
        )

        if pipeline_template_tasks_response_body.get('errors'):
            rollback_pipeline_template_import(new_pipeline_template_id, request_context)
            return {'statusCode': 401, **pipeline_template_tasks_response_payload}

        # write related records.
        pipeline_template_tasks_response_body, pipeline_template_tasks_response_payload = save_pipeline_task_templates(
            sanitized_pipeline_template_tasks,
            request_context
        )

        if pipeline_template_tasks_response_body.get('errors'):
            rollback_pipeline_template_import(new_pipeline_template_id, request_context)
            return {'statusCode': 401, **pipeline_template_tasks_response_payload}

    return {
        'headers': default_http_headers,
        'statusCode': 201,
    }


def update_task_template_ids(new_pipeline_template_id, template, pipeline_template_tasks, validation_errors, new_to_old_ids, all_scripts):
    # Add new template ID to each task
    for task in pipeline_template_tasks:
        task['pipeline_template_id'] = new_pipeline_template_id
        # remap successor ids to new ids
        task_successors = task.get('task_successors', None)
        if task_successors:
            for i in range(len(task_successors)):
                new_successor_id = new_to_old_ids.get(task_successors[i], 'not_found')
                if new_successor_id == 'not_found':
                    validation_errors.append(
                        {f"{template['pipeline_template_name']}\\{task['pipeline_template_task_name']}": [
                            f"Task successor not found in imported template with Id: '{task_successors[i]}'"]})
                else:
                    task_successors[i] = new_successor_id

        validate_task(template['pipeline_template_name'], task, all_scripts, validation_errors)



def save_pipeline_task_templates(pipeline_template_tasks, request_context):
    event_item_ptt = {
        'httpMethod': 'POST',
        'requestContext': request_context,
        'pathParameters':
            {
                'schema': "pipeline_template_task"
            },
        'body': json.dumps(pipeline_template_tasks),
    }

    # 'items' lambda will do the schema validation for the passed template task
    pipeline_template_tasks_response = lambda_client.invoke(
        FunctionName=f'{application}-{environment}-items',
        InvocationType='RequestResponse',
        Payload=json.dumps(event_item_ptt)
    )

    pipeline_template_tasks_response_payload = json.loads(
        pipeline_template_tasks_response['Payload'].read().decode("utf-8"))

    pipeline_template_tasks_response_body = json.loads(pipeline_template_tasks_response_payload['body'])

    return pipeline_template_tasks_response_body, pipeline_template_tasks_response_payload


def create_pipeline(template: PipelineTemplate, request_context):
    event_item_pt = {
        'httpMethod': 'POST',
        'requestContext': request_context,
        'pathParameters':
            {
                'schema': PIPELINE_TEMPLATE_SCHEMA
            },
        'body': json.dumps(template)
    }

    # 'items' lambda will do the schema validation for the passed pipeline template
    pipeline_template_response = lambda_client.invoke(
        FunctionName=f'{application}-{environment}-items',
        InvocationType='RequestResponse',
        Payload=json.dumps(event_item_pt)
    )
    pipeline_template_response_payload = json.loads(pipeline_template_response['Payload'].read().decode("utf-8"))
    return pipeline_template_response_payload


def get_pipeline_template_tasks_table() -> Table:
    return cmf_boto.resource('dynamodb').Table(pipeline_template_tasks_table_name)


def get_pipeline_templates_table() -> Table:
    return cmf_boto.resource('dynamodb').Table(pipeline_templates_table_name)


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)

def rollback_pipeline_template_import(new_pipeline_template_id, request_context):
    event_item_pt_delete = {
        'httpMethod': 'DELETE',
        'requestContext': request_context,
        'pathParameters':
            {
                'id': new_pipeline_template_id,
                'schema': PIPELINE_TEMPLATE_SCHEMA
            },
    }

    pipeline_template_delete_response = lambda_client.invoke(
        FunctionName=f'{application}-{environment}-item',
        InvocationType='RequestResponse',
        Payload=json.dumps(event_item_pt_delete)
    )

    return pipeline_template_delete_response


def get_scripts():
    # get list of scripts in the instance
    get_scripts_event = {
        'httpMethod': 'GET'
    }
    logger.info("Getting list of existing scripts..")
    all_scripts_response = lambda_client.invoke(FunctionName=f'{application}-{environment}-ssm-scripts',
                                                InvocationType='RequestResponse',
                                                Payload=json.dumps(get_scripts_event, cls=JsonEncoder))
    all_scripts_response_payload = json.loads(all_scripts_response['Payload'].read())

    all_scripts_response_body = json.loads(all_scripts_response_payload['body'])
    logger.info("get_scripts complete.")

    return all_scripts_response_body


def get_script_by_name(script_name, scripts):
    return [script for script in scripts if script['script_name'] == script_name]


def get_script_by_id(script_id, scripts):
    return [script for script in scripts if script['package_uuid'] == script_id]


def validate_task(pipeline_template_name, task, all_scripts, validation_errors):
    if 'task_name' in task and 'task_id' not in task:
        # convert task name to an id.
        scripts = get_script_by_name(task['task_name'], all_scripts)

        if scripts:
            task['task_id'] = scripts[0]['package_uuid']
        else:
            # Script not found.
            validation_errors.append(
                {
                    f"{pipeline_template_name}\\{task['pipeline_template_task_name']}":
                        [f"Script name not found for task_name: {task['task_name']}"]
                })
    else:
        # verify task id is a valid script.
        scripts = get_script_by_id(task['task_id'], all_scripts)
        if not scripts:
            # Script not found.
            validation_errors.append(
                {f"{pipeline_template_name}\\{task['pipeline_template_task_name']}": [f"Script name not found for task_id: {task['task_id']}"]})

    task.pop('task_name', None)