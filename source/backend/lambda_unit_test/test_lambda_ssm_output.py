#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import gzip
import base64
import os
import sys
from unittest.mock import patch

import boto3
from unittest import mock
from datetime import datetime

import botocore
from moto import mock_aws

from test_lambda_ssm_base import LambdaSSMBaseTest
import test_common_utils

mock_os_environ = {
    **test_common_utils.default_mock_os_environ,
    'socket_url': 'http://example.com'
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaSSMOutputTest(LambdaSSMBaseTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    @mock_aws
    def setUp(self) -> None:
        import lambda_ssm_output
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_ssm_jobs(self.ddb_client, lambda_ssm_output.ssm_jobs_table_name)
        test_common_utils.create_and_populate_connection_ids(self.ddb_client, lambda_ssm_output.connectionIds_table_name)

        self.log_message = 'test log entry'
        self.log_message_prefix = 'CMF-TEST:'
        self.log_message_suffix = 'suffix'

    def create_event(self, ssm_id):
        payload = {
            'logEvents': [
                {
                    'ts': datetime.utcnow().isoformat(sep='T'),
                    'message': f'{self.log_message_prefix} {self.log_message}[{ssm_id}]{self.log_message_suffix}'
                },
                {
                    'ts': datetime.utcnow().isoformat(sep='T'),
                    'message': f'the code processes only the first entry [{ssm_id + "__"}]'
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

    def test_lambda_handler_success_job_running(self):
        import lambda_ssm_output
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        item = lambda_ssm_output.ssm_jobs_table.get_item(Key={'SSMId': ssm_id})['Item']
        self.assertEqual(self.log_message + self.log_message_suffix, item['outputLastMessage'])
        self.assertEqual('RUNNING', item['status'])
        self.assertEqual('RUNNING', item['SSMData']['status'])

    def test_lambda_handler_success_job_timed_out(self):
        import lambda_ssm_output
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 50)
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        item = lambda_ssm_output.ssm_jobs_table.get_item(Key={'SSMId': ssm_id})['Item']
        self.assertEqual(self.log_message + self.log_message_suffix, item['outputLastMessage'])
        self.assertEqual('TIMED-OUT', item['status'])
        self.assertEqual('RUNNING', item['SSMData']['status'])

    def test_lambda_handler_success_job_complete(self):
        import lambda_ssm_output
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 50)
        self.log_message_suffix = 'JOB_COMPLETE'
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        item = lambda_ssm_output.ssm_jobs_table.get_item(Key={'SSMId': ssm_id})['Item']
        self.assertEqual(self.log_message + self.log_message_suffix, item['outputLastMessage'])
        self.assertEqual('COMPLETE', item['status'])
        self.assertEqual('RUNNING', item['SSMData']['status'])

    def test_lambda_handler_success_job_failed(self):
        import lambda_ssm_output
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 50)
        self.log_message_suffix = 'JOB_FAILED'
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        item = lambda_ssm_output.ssm_jobs_table.get_item(Key={'SSMId': ssm_id})['Item']
        self.assertEqual(self.log_message + self.log_message_suffix, item['outputLastMessage'])
        self.assertEqual('FAILED', item['status'])
        self.assertEqual('RUNNING', item['SSMData']['status'])

    def test_lambda_handler_existing_outcome_date(self):
        import lambda_ssm_output
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        item = lambda_ssm_output.ssm_jobs_table.get_item(Key={'SSMId': ssm_id})['Item']
        item['_history']['outcomeDate'] = datetime.utcnow().isoformat(sep='T')
        lambda_ssm_output.ssm_jobs_table.put_item(Item=item)
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        item = lambda_ssm_output.ssm_jobs_table.get_item(Key={'SSMId': ssm_id})['Item']
        self.assertEqual(self.log_message + self.log_message_suffix, item['outputLastMessage'])
        self.assertEqual('RUNNING', item['status'])
        self.assertEqual('RUNNING', item['SSMData']['status'])

    @patch('lambda_ssm_output.gatewayapi')
    def test_lambda_handler_wss_success(self, mock_getwaymgtapi):
        if 'lambda_ssm_output' in sys.modules:
            del sys.modules['lambda_ssm_output']
        os.environ['socket_url'] = 'wss://example.com'
        import lambda_ssm_output
        lambda_ssm_output.gatewayapi = mock_getwaymgtapi
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        self.assertEqual(2, mock_getwaymgtapi.post_to_connection.call_count)

    @patch('lambda_ssm_output.gatewayapi')
    def test_lambda_handler_wss_fail(self, mock_getwaymgtapi):
        if 'lambda_ssm_output' in sys.modules:
            del sys.modules['lambda_ssm_output']
        os.environ['socket_url'] = 'wss://example.com'
        import lambda_ssm_output
        lambda_ssm_output.gatewayapi = mock_getwaymgtapi
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        mock_getwaymgtapi.post_to_connection.side_effect = botocore.exceptions.ClientError({
            'Error': {
                'Code': 500,
                'Message': 'Simulated Exception'
            }
        },
            'post_to_connection')
        response = lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        self.assertEqual(None, response)
        self.assertEqual(2, mock_getwaymgtapi.post_to_connection.call_count)
