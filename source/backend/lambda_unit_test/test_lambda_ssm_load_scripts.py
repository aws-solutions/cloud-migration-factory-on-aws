#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from unittest.mock import patch, ANY

import boto3
from unittest import mock

from moto import mock_lambda, mock_s3, mock_iam
from test_common_utils import LambdaContextLogStream, RequestsResponse, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'code_bucket_name': 'test_code_bucket_name',
    'key_prefix': 'test_key_prefix'
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_s3
@mock_lambda
@mock_iam
class LambdaSSMLoadScriptsTest(unittest.TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        import lambda_ssm_load_scripts
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        self.iam_client = boto3.client('iam')
        self.bucket_name = os.getenv('code_bucket_name')
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        file_to_upload = os.path.dirname(os.path.realpath(__file__)) + '/sample_data/ssm_load_scripts' \
                                                                       '/sample_ssm_scripts.zip'
        self.s3_client.upload_file(file_to_upload, self.bucket_name,
                                   lambda_ssm_load_scripts.default_scripts_s3_key)

        test_role = self.iam_client.create_role(
            RoleName='cmf_test',
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }
            )
        )

        function_name = f'{lambda_ssm_load_scripts.application}-{lambda_ssm_load_scripts.environment}-ssm-scripts'
        self.lambda_client.create_function(
            FunctionName=function_name,
            Role=test_role['Role']['Arn'],
            Code={
                'S3Bucket': self.bucket_name,
                'S3Key': lambda_ssm_load_scripts.default_scripts_s3_key
            }
        )
        self.test_url = 'http://example.com'
        self.test_resource_id = 'LOGICAL_RESOURCE_ID_101'
        self.test_request_id = 'REQUEST_ID_101'
        self.test_stack_id = 'TEST_STACK_101'

        self.event_create = {
            'RequestType': 'Create',
            'StackId': self.test_stack_id,
            'RequestId': self.test_request_id,
            'LogicalResourceId': self.test_resource_id,
            'ResponseURL': self.test_url
        }
        self.event_update = self.event_create.copy()
        self.event_update['RequestType'] = 'Update'
        self.event_delete = self.event_create.copy()
        self.event_delete['RequestType'] = 'Delete'
        self.event_unexpected = self.event_create.copy()
        self.event_unexpected['RequestType'] = 'UnExpected'
        self.event_invalid = self.event_create.copy()
        del self.event_invalid['RequestType']

        self.log_stream_name = 'testing'
        self.lambda_context = LambdaContextLogStream(self.log_stream_name)

        self.status_success = 'SUCCESS'
        self.status_failed = 'FAILED'

    def assert_requests_called_with(self, mock_requests, message, status):
        mock_requests.put.assert_called_once_with(self.test_url,
                                                  data=json.dumps({'Status': status,
                                                                   'Reason': 'Details in: ' + self.log_stream_name,
                                                                   'PhysicalResourceId': self.log_stream_name,
                                                                   'StackId': self.test_stack_id,
                                                                   'RequestId': self.test_request_id,
                                                                   'LogicalResourceId': self.test_resource_id,
                                                                   'Data': {
                                                                       'Message': message
                                                                   }
                                                                   }),
                                                  headers=ANY,
                                                  timeout=ANY)

    def assert_events_success(self, event, mock_requests, status, message):
        import lambda_ssm_load_scripts
        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_ssm_load_scripts.lambda_handler(event, self.lambda_context)
        expected = {
            'Response': status
        }
        self.assertEqual(expected, response)
        self.assert_requests_called_with(mock_requests, message, status)

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_create_success(self, mock_requests):
        self.assert_events_success(self.event_create, mock_requests, self.status_success,
                                   'Default script packages loaded successfully')

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_update_success(self, mock_requests):
        # returns no update required, but does the same thing as create
        self.assert_events_success(self.event_update, mock_requests, self.status_success,
                                   'No update required')

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_delete_success(self, mock_requests):
        self.assert_events_success(self.event_delete, mock_requests, self.status_success,
                                   'No deletion required')
        mock_requests.asset_not_called()

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_unexpected_success(self, mock_requests):
        self.assert_events_success(self.event_unexpected, mock_requests, self.status_success,
                                   'Unexpected event received from CloudFormation')
        mock_requests.asset_not_called()

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_get_requests_exception(self, mock_requests):
        import lambda_ssm_load_scripts
        mock_requests.put.side_effect = Exception('Simulated Exception')
        status = 'FAILED'
        response = lambda_ssm_load_scripts.lambda_handler(self.event_create, self.lambda_context)
        expected = {
            'Response': status
        }
        self.assertEqual(expected, response)

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_get_zip_size_violation(self, mock_requests):
        # error logged and then continues ignoring the error
        import lambda_ssm_load_scripts
        lambda_ssm_load_scripts.ZIP_MAX_SIZE = 10
        self.assert_events_success(self.event_create, mock_requests, self.status_success,
                                   'Default script packages loaded successfully')

    @patch('lambda_ssm_load_scripts.import_script_packages')
    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_create_exception_in_main(self, mock_requests, mock_import_script_packages):
        import lambda_ssm_load_scripts
        mock_import_script_packages.side_effect = Exception('Simulated Exception')
        response = lambda_ssm_load_scripts.lambda_handler(self.event_create, self.lambda_context)
        expected = {
            'Response': self.status_success
        }
        self.assertEqual(expected, response)
        self.assert_requests_called_with(mock_requests, 'Exception during processing',
                                         self.status_failed)

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_invalid_event(self, mock_requests):
        import lambda_ssm_load_scripts
        response = lambda_ssm_load_scripts.lambda_handler(self.event_invalid, self.lambda_context)
        expected = {
            'Response': self.status_success
        }
        self.assertEqual(expected, response)
        self.assert_requests_called_with(mock_requests, 'Exception during processing',
                                         self.status_failed)

    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_bad_zip_file(self, mock_requests):
        import lambda_ssm_load_scripts
        # upload a non zip file
        file_to_upload = os.path.dirname(os.path.realpath(__file__)) + '/sample_data/apps.json'
        self.s3_client.upload_file(file_to_upload, self.bucket_name,
                                   lambda_ssm_load_scripts.default_scripts_s3_key)
        # error logged and then continues ignoring the error
        self.assert_events_success(self.event_create, mock_requests, self.status_success,
                                   'Default script packages loaded successfully')

    @patch('lambda_ssm_load_scripts.uuid')
    @patch('lambda_ssm_load_scripts.requests')
    def test_lambda_handler_fail_in_import_scripts(self, mock_requests, mock_uuid):
        import lambda_ssm_load_scripts
        mock_uuid.uuid4.side_effect = Exception('Simulated Exception')
        # error logged and then continues ignoring the error
        self.assert_events_success(self.event_create, mock_requests, self.status_success,
                                   'Default script packages loaded successfully')
