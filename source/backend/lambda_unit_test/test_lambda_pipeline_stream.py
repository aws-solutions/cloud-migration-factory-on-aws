#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import boto3
from moto import mock_aws
import os
from unittest import TestCase, mock

from cmf_logger import logger

mock_os_environ = {
    'application': 'cmf',
    'environment': 'unittest',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'PIPELINE_TEMPLATE_TASKS_TABLE_NAME': 'pipeline-template-tasks',
    'TASK_EXECUTIONS_TABLE_NAME': 'task-executions',
    'PIPELINES_TABLE_NAME': 'pipelines'
}

@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class PipelineWaveStreamTest(TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self):
        self.task_executions_table_name = os.environ['TASK_EXECUTIONS_TABLE_NAME']
        self.pipelines_template_tasks_table_name = os.environ['PIPELINE_TEMPLATE_TASKS_TABLE_NAME']
        self.pipelines_table_name = os.environ['PIPELINES_TABLE_NAME']
        self.ddb_client = boto3.client('dynamodb')

        self.ddb_client.create_table(
            TableName=self.task_executions_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {'AttributeName': 'task_execution_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'task_execution_id', 'AttributeType': 'S'},
                {'AttributeName': 'pipeline_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {"IndexName": "pipeline_id-index",
                 "KeySchema": [
                     {"AttributeName": "pipeline_id", "KeyType": "HASH"}
                 ],
                 "Projection": {
                     "ProjectionType": "ALL"}
                 }
            ]
        )
        self.ddb_client.create_table(
            TableName=self.pipelines_template_tasks_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {'AttributeName': 'pipeline_template_task_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pipeline_template_task_id', 'AttributeType': 'S'},
                {'AttributeName': 'pipeline_template_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {"IndexName": "pipeline_template_id-index",
                 "KeySchema": [
                     {"AttributeName": "pipeline_template_id", "KeyType": "HASH"}
                 ],
                 "Projection": {
                     "ProjectionType": "ALL"}
                 }
            ]
        )
        self.ddb_client.create_table(
            TableName=self.pipelines_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {'AttributeName': 'pipeline_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pipeline_id', 'AttributeType': 'S'},
            ]
        )

        self.ddb_client.put_item(
            TableName=self.task_executions_table_name,
            Item={
                'task_execution_id': {
                    'S': '10-1'
                },
                'pipeline_id': {
                    'S': '10'
                }
            }
        )
        self.task_executions_table = boto3.resource('dynamodb').Table(self.task_executions_table_name)
        self.ddb_client.put_item(
            TableName=self.pipelines_template_tasks_table_name,
            Item={
                'pipeline_template_task_id': {
                    'S': '1'
                },
                'pipeline_template_id': {
                    'S': '1'
                },
                'task_id': {
                    'S': '1'
                },
                'task_sequence_number': {
                    'S': '1'
                }
            }
        )
        self.ddb_client.put_item(
            TableName=self.pipelines_template_tasks_table_name,
            Item={
                'pipeline_template_task_id': {
                    'S': '2'
                },
                'pipeline_template_id': {
                    'S': '1'
                },
                'task_id': {
                    'S': '2'
                },
                'task_sequence_number': {
                    'S': '2'
                }
            }
        )
        self.pipeline_template_tasks_table = boto3.resource('dynamodb').Table(self.pipelines_template_tasks_table_name)
        self.ddb_client.put_item(
            TableName=self.pipelines_table_name,
            Item={
                'pipeline_id': {
                    'S': '1'
                },
                'pipeline_status': {
                    'S': 'Provisioning'
                }
            }
        )
        self.pipelines_table = boto3.resource('dynamodb').Table(self.pipelines_table_name)


    def tearDown(self):
        pass

    @mock.patch('botocore.client.BaseClient._make_api_call')
    def test_lambda_handler_with_updated_image_is_no_op(self, mock_boto_client):
        logger.info("Testing test_lambda_pipeline_stream: test_lambda_handler_with_updated_image_is_no_op")
        from lambda_pipeline_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'OldImage': {'pipeline_id': {'S': '1'}}, 'NewImage': {'pipeline_id': {'S': '1'}}}}]}

        lambda_handler(event, {})
        mock_boto_client.assert_not_called()

    def test_lambda_handler_with_only_old_image_deletes(self):
        logger.info("Testing test_lambda_pipeline_stream: test_lambda_handler_with_only_old_image_deletes")
        from lambda_pipeline_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'OldImage': {'pipeline_id': {'S': '10'}}}}]}

        lambda_handler(event, {})
        self.assertEqual(0, len(self.task_executions_table.scan()['Items']))

    def test_lambda_handler_with_only_new_image_creates(self):
        logger.info("Testing test_lambda_pipeline_stream: test_lambda_handler_with_only_new_image_creates")
        from lambda_pipeline_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'NewImage': {
            'pipeline_id':
                {'S': '1'},
            "pipeline_template_id":
                {'S': '1'},
            '_history': {
                'M': {}
            },
            "task_arguments": {
                "M": {
                    "home_region": {
                        "S": "us-west-2"
                    }
                }
            }
        }}}]}

        lambda_handler(event, {})
        self.assertEqual(2, len(self.pipeline_template_tasks_table.scan()['Items']))
        pipelines = self.pipelines_table.scan()['Items']
        self.assertEqual(1, len(pipelines))
        self.assertEqual('Not Started', pipelines[0]['pipeline_status'])

    def test_lambda_handler_with_concurrent_pipeline_delete_does_not_create_new_entity(self):
        logger.info("Testing test_lambda_pipeline_stream: test_lambda_handler_with_concurrent_pipeline_delete_does_not_create_new_entity")
        from lambda_pipeline_stream import lambda_handler

        event = {'Records': [{'dynamodb': {'NewImage': {
            'pipeline_id':
                {'S': '100'},
            "pipeline_template_id":
                {'S': '1'},
            '_history': {
                'M': {}
            },
            "task_arguments": {
                "M": {
                    "home_region": {
                        "S": "us-west-2"
                    }
                }
            }
        }}}]}

        lambda_handler(event, {})
        self.assertEqual(1, len(self.pipelines_table.scan()['Items']))