#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import os
from unittest import mock
from unittest.mock import patch, ANY

from moto import mock_aws
import boto3
import json

from test_lambda_migrationtracker_glue_base import mock_os_environ, StringContainsMatcher, \
    RequestsResponse, LambdaMigrationTrackerGlueBaseTest


SIMULATED_EXCEPTION_STRING = 'Simulated Exception'

@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaMigrationTrackerGlueTest(LambdaMigrationTrackerGlueBaseTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self):
        super().setUp()
        import lambda_migrationtracker_glue_execute
        self.glue_client = boto3.client('glue')
        for schema in lambda_migrationtracker_glue_execute.SCHEMAS:
            self.glue_client.create_crawler(Name=f"{os.environ['application']}-{os.environ['environment']}-{schema}-crawler",
                                            Role='RoleABC',
                                            Targets={
                                                'DynamoDBTargets': [
                                                    {
                                                        'Path': 'MyDatabase',
                                                    },
                                                ]
                                            })

        for schema in lambda_migrationtracker_glue_execute.SCHEMAS:
            self.glue_client.create_job(Name=f"{os.environ['application']}-{os.environ['environment']}-{schema}-extract",
                                        Role='RoleABC',
                                        Command={
                                            'Name': 'MyCommand',
                                            'ScriptLocation': 'MyS3location'
                                        })

    def assert_lambda_handler_create_success(self, lambda_event, mock_requests):
        import lambda_migrationtracker_glue_execute
        response_status = 'OK'
        mock_requests.put.return_value = RequestsResponse(response_status)
        response = lambda_migrationtracker_glue_execute.lambda_handler(lambda_event, self.lamda_context)
        self.assert_requests_called_with_success_part_match(mock_requests)
        self.assert_response(response)

    def assert_requests_called_with_success_part_match(self, mock_requests):
        # Contents of Data node could be different, so check only the characters before
        mock_requests.put.assert_called_once_with('http://example.com',
                                                  data=StringContainsMatcher(
                                                      json.dumps({'Status': 'SUCCESS',
                                                                  'PhysicalResourceId': self.test_aws_account_id,
                                                                  'Reason': 'Running the glue crawler and job',
                                                                  'StackId': 'MyStack',
                                                                  'RequestId': 'MyRequest',
                                                                  'LogicalResourceId': 'Resource101',
                                                                  'Data': {'JobRunId': '01',
                                                                           'ResponseMetadata': {
                                                                               'HTTPStatusCode': 200,
                                                                               'HTTPHeaders': {
                                                                                   'server': 'amazon.com'},
                                                                               'RetryAttempts': 0,
                                                                           }
                                                                           }
                                                                  })[:200]
                                                  ),
                                                  headers=ANY,
                                                  timeout=ANY)

    @patch('lambda_migrationtracker_glue_execute.time')
    @patch('lambda_migrationtracker_glue_execute.requests')
    def test_lambda_handler_create_success(self, mock_requests, mock_time):
        self.assert_lambda_handler_create_success(self.event_create, mock_requests)
        mock_time.sleep.assert_called_once()

    @patch('lambda_migrationtracker_glue_execute.time')
    @patch('lambda_migrationtracker_glue_execute.requests')
    def test_lambda_handler_update_success(self, mock_requests, mock_time):
        self.assert_lambda_handler_create_success(self.event_update, mock_requests)
        mock_time.sleep.assert_called_once()

    @patch('lambda_migrationtracker_glue_execute.requests')
    @patch('lambda_migrationtracker_glue_execute.run_glue_crawler_job')
    def test_lambda_handler_delete_success(self, mock_run_glue_crawler_job, mock_requests):
        import lambda_migrationtracker_glue_execute
        response = lambda_migrationtracker_glue_execute.lambda_handler(self.event_delete, self.lamda_context)
        mock_run_glue_crawler_job.assert_not_called()
        self.assert_response(response)
        self.assert_requests_called_with_success(mock_requests, 'No cleanup is required for this function')

    @patch('lambda_migrationtracker_glue_execute.requests')
    @patch('lambda_migrationtracker_glue_execute.run_glue_crawler_job')
    def test_lambda_handler_unknown_success(self, mock_run_glue_crawler_job, mock_requests):
        import lambda_migrationtracker_glue_execute
        response = lambda_migrationtracker_glue_execute.lambda_handler(self.event_unknown, self.lamda_context)
        mock_run_glue_crawler_job.assert_not_called()
        self.assert_response(response)
        self.assert_requests_called_with_success(mock_requests, 'Unknown request type')

    @patch('lambda_migrationtracker_glue_execute.time')
    @patch('lambda_migrationtracker_glue_execute.requests')
    def test_lambda_handler_create_swallowed_exception(self, mock_requests, mock_time):
        import lambda_migrationtracker_glue_execute
        mock_requests.put.side_effect = Exception(SIMULATED_EXCEPTION_STRING)
        response = lambda_migrationtracker_glue_execute.lambda_handler(self.event_create, self.lamda_context)
        self.assert_requests_called_with_success_part_match(mock_requests)
        self.assert_response(response)
        mock_time.sleep.assert_called_once()

    @patch('lambda_migrationtracker_glue_execute.requests')
    @patch('lambda_migrationtracker_glue_execute.run_glue_crawler_job')
    def test_lambda_handler_exception(self, mock_run_glue_crawler_job, mock_requests):
        import lambda_migrationtracker_glue_execute
        mock_run_glue_crawler_job.side_effect = Exception(SIMULATED_EXCEPTION_STRING)
        mock_requests.put.return_value = RequestsResponse('OK')
        response = lambda_migrationtracker_glue_execute.lambda_handler(self.event_create, self.lamda_context)
        self.assert_requests_called_with_failure(mock_requests, 'Exception: Simulated Exception')
        self.assert_response(response)

    @patch('lambda_migrationtracker_glue_execute.requests')
    @patch('lambda_migrationtracker_glue_execute.run_glue_crawler_job')
    def test_lambda_handler_exception_with_physical_resource_id(self, mock_run_glue_crawler_job, mock_requests):
        import lambda_migrationtracker_glue_execute
        mock_run_glue_crawler_job.side_effect = Exception(SIMULATED_EXCEPTION_STRING)
        mock_requests.put.return_value = RequestsResponse('OK')
        self.event_create['PhysicalResourceId'] = self.event_create['LogicalResourceId']
        response = lambda_migrationtracker_glue_execute.lambda_handler(self.event_create, self.lamda_context)
        self.assert_requests_called_with_failure(mock_requests, 'Exception: Simulated Exception')
        self.assert_response(response)
