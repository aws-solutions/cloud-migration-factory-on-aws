#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import cmf_boto
import boto3
from boto3.dynamodb.conditions import Key
import botocore
import logging
import os
from cmf_utils import send_anonymous_usage_data

DEFAULT_TASK_EXECUTION_STATUS = "Not Started"
DEFAULT_PIPELINE_EXECUTION_STATUS = "Not Started"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

pipeline_template_tasks_table_name = os.environ['PIPELINE_TEMPLATE_TASKS_TABLE_NAME']
pipeline_template_tasks_table = cmf_boto.resource('dynamodb').Table(pipeline_template_tasks_table_name)

task_executions_table_name = os.environ['TASK_EXECUTIONS_TABLE_NAME']
task_executions_table = cmf_boto.resource('dynamodb').Table(task_executions_table_name)

pipelines_table_name = os.environ['PIPELINES_TABLE_NAME']
pipelines_table = cmf_boto.resource('dynamodb').Table(pipelines_table_name)


def query_dynamodb_index(data_table, index_name, key_condition):
    response = data_table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition
    )
    query_data = response['Items']
    while 'LastEvaluatedKey' in response:
        logger.info("Last Evaluated key is " + str(response['LastEvaluatedKey']))
        response = data_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        query_data.extend(response['Items'])
    return query_data


def handle_creation_pipeline_event(dynamodb_image):
    pipeline_template_id = dynamodb_image['pipeline_template_id']['S']
    pipeline_template_tasks = query_dynamodb_index(
        pipeline_template_tasks_table,
        'pipeline_template_id-index',
        Key('pipeline_template_id').eq(pipeline_template_id)
    )

    # Expect inputs to already be validated in user API
    deserializer = boto3.dynamodb.types.TypeDeserializer()
    pipeline_tasks_inputs = {k: deserializer.deserialize(v) for k,v in dynamodb_image.get('task_arguments', {'M': {}})['M'].items()}
    pipeline_id = dynamodb_image['pipeline_id']['S']

    history_data = {k: deserializer.deserialize(v) for k,v in dynamodb_image['_history']['M'].items()}

    for pipeline_template_task in pipeline_template_tasks:
        task_id = pipeline_template_task['task_id']
        pipeline_template_task_id = pipeline_template_task['pipeline_template_task_id']
        task_version = pipeline_template_task.get('task_version',None)
        task_successors = pipeline_template_task.get('task_successors',[])

        def prefix_task_successors(task_successor_id):
            return f'{pipeline_id}-{task_successor_id}'

        task_successors = list(map(prefix_task_successors, task_successors))

        task_name = pipeline_template_task.get(
            'pipeline_template_task_name', f'{pipeline_id}-{pipeline_template_task_id}'
        )

        logger.info(f'Writing task execution for Task ID "{pipeline_template_task_id}" and Pipeline ID "{pipeline_id}"')
        task_execution_item = {
            "task_execution_id": f'{pipeline_id}-{pipeline_template_task_id}',
            "task_execution_name": task_name,
            "pipeline_id": pipeline_id,
            "task_id": task_id,
            "task_version": task_version,
            "task_execution_status": DEFAULT_TASK_EXECUTION_STATUS,
            "task_execution_inputs": pipeline_tasks_inputs,
            "task_successors": task_successors,
            "_history": history_data,
            "outputLastMessage": '[System Completed Provisioning]'
        }
        task_executions_table.put_item(
            Item=task_execution_item
        )

    logger.info(f'Updating status for pipeline ID "{pipeline_id}"')
    try:
        pipelines_table.update_item(
            Key={
                'pipeline_id': pipeline_id
            },
            UpdateExpression='SET #pipeline_status = :pipeline_status',
            ExpressionAttributeNames={
                '#pipeline_status': 'pipeline_status'
            },
            ExpressionAttributeValues={
                ':pipeline_status': DEFAULT_PIPELINE_EXECUTION_STATUS
            },
            ConditionExpression='attribute_exists(pipeline_id)'
        )
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            logger.info("Pipeline already deleted")
        else:
            raise e

    send_anonymous_usage_data('PipelineCreated')

def handle_deleted_pipeline_event(dynamodb_image):
    pipeline_id = dynamodb_image['pipeline_id']['S']
    task_executions = query_dynamodb_index(
        task_executions_table,
        'pipeline_id-index',
        Key('pipeline_id').eq(pipeline_id)
    )
    for task_execution in task_executions:
        task_executions_table.delete_item(Key={"task_execution_id": task_execution['task_execution_id']})


def lambda_handler(event, _):
    for record in event ['Records']:
        dynamodb_record = record['dynamodb']

        if 'OldImage' not in dynamodb_record:
            logger.info("Received pipeline creation event")
            handle_creation_pipeline_event(dynamodb_record['NewImage'])
        elif 'NewImage' not in dynamodb_record:
            logger.info("Received pipeline deletion event")
            handle_deleted_pipeline_event(dynamodb_record['OldImage'])