#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import boto3
from datetime import datetime
import json
import gzip
import base64
from moto import mock_aws
import os

from unittest import TestCase, mock

@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region':'us-east-1', 'application': 'cmf', 'environment': 'unittest'})
@mock_aws
class LambdaPipelineTaskExecutionOutputTest(TestCase):
    @mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region':'us-east-1', 'application': 'cmf', 'environment': 'unittest'})
    @mock_aws
    def setUp(self) -> None:
        self.task_executions_table_name = '{}-{}-'.format('cmf', 'unittest') + 'task_executions'
        boto3.setup_default_session()
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
        self.ddb_client.put_item(
            TableName=self.task_executions_table_name,
            Item={
                'task_execution_id': {
                    'S': '1'
                },
                'pipeline_id': {
                    'S': '1'
                },
                'task_execution_status': {
                    'S': 'Not Started'
                },
                'task_sequence_number': {
                    'S': '1'
                },
                'task_id': {
                    'S': '1'
                },
                '_history': {
                    'M': {
                        'lastModifiedTimestamp': {
                            'S': 'test'
                        },
                        'lastModifiedBy': {
                            'S': 'test'
                        }
                    }
                }
            }
        )

    def create_event(self, task_execution_id, status):
        payload = {
            'logEvents': [
                {
                    'ts': datetime.utcnow().isoformat(sep='T'),
                    'message': 'End Report'
                },
                {
                    'ts': datetime.utcnow().isoformat(sep='T'),
                    'message': f'[{task_execution_id}][{status}] Completed successfully'
                }
            ]
        }
        payload_str = json.dumps(payload)
        payload_compressed = gzip.compress(payload_str.encode())
        payload_encoded = base64.b64encode(payload_compressed)
        event = {
            'awslogs': {
                'data': payload_encoded
            }
        }
        return event

    def test_lambda_handler(self):
        import lambda_pipeline_task_execution_output
        task_execution_id = '1'
        status = 'Complete'
        lambda_pipeline_task_execution_output.lambda_handler(self.create_event(task_execution_id, status), None)

        item = self.ddb_client.get_item(
            TableName=self.task_executions_table_name,
            Key={'task_execution_id': { 'S': task_execution_id }}
        )['Item']
        self.assertEqual(' Completed successfully\n', item['outputLastMessage']['S'])
        self.assertTrue('Completed successfully' in item['output']['S'])
        self.assertEqual(status, item['task_execution_status']['S'])
