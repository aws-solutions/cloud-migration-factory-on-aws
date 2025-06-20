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
    'EVENT_BUS_NAME': 'eventBusName'
}

@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaSSMOutputTest(LambdaSSMBaseTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    @mock_aws
    def setUp(self) -> None:
        import lambda_ssm_output
        import cmf_pipeline
        self.ddb_client = boto3.client('dynamodb')
        self.eventsClient = boto3.client('events')
        # Create the event bus
        self.eventsClient.create_event_bus(Name=mock_os_environ['EVENT_BUS_NAME'])
        test_common_utils.create_and_populate_ssm_jobs(self.ddb_client, lambda_ssm_output.ssm_jobs_table_name)
        test_common_utils.create_and_populate_tasks(self.ddb_client, cmf_pipeline.task_executions_table_name)

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
        
    @mock.patch('lambda_ssm_output.eventsClient.put_events')
    @mock.patch('lambda_ssm_output.logger')
    def test_missing_ssm_id(self, mock_logger, mock_put_events):
        import lambda_ssm_output
        # Call the handler and verify it handles the error
        with patch('lambda_ssm_output.logger') as mock_logger:
            lambda_ssm_output.lambda_handler(self.create_event(""), None)
            
            # Verify the event publication was attempted
            mock_put_events.assert_not_called()
            
            # Verify that the error was logged
            mock_logger.error.assert_called_with(
                "No SSMId or empty SSMId in Cloudwatch event."
            )

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

    @mock.patch('lambda_ssm_output.eventsClient.put_events')
    def test_lambda_handler_publish_event_success(self, mock_put_events):
        import lambda_ssm_output
        
        # Setup successful SSM job that will trigger event publishing
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        self.log_message_suffix = 'JOB_COMPLETE'
        
        # Mock successful response from EventBridge
        mock_put_events.return_value = {
            'FailedEntryCount': 0,
            'Entries': [{'EventId': 'test-event-id'}]
        }
        
        # Call the handler
        lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        
        # Verify the event was published with correct parameters
        mock_put_events.assert_called_once()
        call_args = mock_put_events.call_args[1]
        
        self.assertEqual(len(call_args['Entries']), 1)
        entry = call_args['Entries'][0]
        self.assertEqual(entry['Source'], f'{mock_os_environ["application"]}-{mock_os_environ["environment"]}-ssm-output')
        self.assertEqual(entry['DetailType'], 'TaskSuccess')
        self.assertEqual(entry['EventBusName'], mock_os_environ['EVENT_BUS_NAME'])

    @mock.patch('lambda_ssm_output.eventsClient.put_events')
    def test_lambda_handler_publish_event_failure(self, mock_put_events):
        import lambda_ssm_output
        
        # Setup SSM job that will trigger event publishing
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        self.log_message_suffix = 'JOB_COMPLETE'
        
        # Mock failed response from EventBridge
        mock_put_events.return_value = {
            'FailedEntryCount': 1,
            'Entries': [{
                'ErrorCode': 'TestError',
                'ErrorMessage': 'Test error message',
                'EventId': 'EventId'
            }]
        }
        
        # Call the handler and verify it handles the error
        with patch('cmf_utils.logger') as mock_logger:
            lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
            
            # Verify the event publication was attempted
            mock_put_events.assert_called_once()
            
            # Verify that the error was logged
            mock_logger.error.assert_called_with(
                "Failed to publish event to EventBridge: ErrorCode=TestError, ErrorMessage=Test error message, EventId=EventId"
            )

    @mock.patch('lambda_ssm_output.eventsClient.put_events')
    @mock.patch('cmf_utils.logger')
    def test_lambda_handler_publish_event_internal_exception(self, mock_logger, mock_put_events):
        import lambda_ssm_output
        
        # Setup SSM job that will trigger event publishing
        ssm_id = self.put_recent_job(lambda_ssm_output.ssm_jobs_table, 1, 5)
        self.log_message_suffix = 'JOB_COMPLETE'
        
        # Mock an internal exception
        mock_put_events.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'InternalException', 'Message': 'Internal error occurred'}},
            'put_events'
        )
        
        # Call the handler and verify it handles the exception
        lambda_ssm_output.lambda_handler(self.create_event(ssm_id), None)
        
        # Verify the event publication was attempted
        mock_put_events.assert_called_once()
        
        # Verify that the error was logged correctly
        mock_logger.error.assert_called_with(
            "EventBridge error occurred while publishing event: An error occurred (InternalException) when calling the put_events operation: Internal error occurred"
        )
