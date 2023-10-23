#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from unittest import mock
from unittest.mock import patch, ANY

import boto3
from botocore.exceptions import ClientError

from moto import mock_s3
from test_common_utils import LambdaContextLogStream, RequestsResponse, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'SchemaDynamoDBTable': 'test_schema_table',
    'USER_API': 'https://example.com/user',
    'ADMIN_API': 'https://example.com/admin',
    'LOGIN_API': 'https://example.com/login',
    'TOOLS_API': 'https://example.com/tools',
    'SSM_WS_API': 'wss://example.com/ssm',
    'USER_POOL_ID': 'test_USER_POOL_ID',
    'VPCE_API_ID': 'fd00:ec2::253',
    'APP_CLIENT_ID': 'test_APP_CLIENT_ID',
    'COGNITO_HOSTED_UI_URL': 'https://example.com/cognito',
    'FRONTEND_BUCKET': 'test_FRONTEND_BUCKET',
    'SOURCE_BUCKET': 'test_SOURCE_BUCKET',
    'SOURCE_KEY': 'test_SOURCE_KEY',
    'VERSION': 'test_VERSION'
}

@mock_s3
@mock.patch.dict('os.environ', mock_os_environ)
class LambdaBuildTest(unittest.TestCase):

    CONST_SUCCESS = 'SUCCESS'
    CONST_FAILED = 'FAILED'

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        self.log_stream_name = 'testing'
        self.lambda_context = LambdaContextLogStream(self.log_stream_name)
        self.test_stack_id = 'testStackId'
        self.test_request_id = 'testRequestId'
        self.test_resource_id = 'testLogicalResourceId'
        self.test_url = 'https://example.com'
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
        self.event_unknown = self.event_create.copy()
        self.event_unknown['RequestType'] = 'Unknown'

        self.response_success = {
            'Response': LambdaBuildTest.CONST_SUCCESS
        }
        self.response_failed = {
            'Response': LambdaBuildTest.CONST_FAILED
        }

        self.s3_client = boto3.client('s3')
        self.frontend_bucket = os.getenv('FRONTEND_BUCKET')
        self.source_bucket = os.getenv('SOURCE_BUCKET')
        self.source_key = os.getenv('SOURCE_KEY')
        self.zipped_website = os.path.dirname(os.path.realpath(__file__)) + '/sample_data/build/website.zip'
        self.s3_client.create_bucket(Bucket=self.source_bucket)
        self.s3_client.create_bucket(Bucket=self.frontend_bucket)
        self.s3_client.upload_file(self.zipped_website, self.source_bucket, self.source_key)

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

    def assert_create_failed_returning_success(self, mock_requests):
        import lambda_build
        response = lambda_build.lambda_handler(self.event_create, self.lambda_context)
        self.assertEqual(self.response_success, response)
        s3_response = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)
        self.assertTrue('Contents' not in s3_response)
        self.assert_requests_called_with(mock_requests, 'Exception during processing', LambdaBuildTest.CONST_FAILED)

    def assert_create_update(self, event, mock_requests):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_build.lambda_handler(event, self.lambda_context)
        self.assertEqual(self.response_success, response)
        contents = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)['Contents']
        self.assertEqual(3, len(contents))
        file_names = sorted([content['Key'] for content in contents])
        self.assertEqual(['env.js', 'index.html', 'second_file.html'], file_names)

    @patch('lambda_build.requests')
    def test_lambda_handler_create_success(self, mock_requests):
        self.assert_create_update(self.event_create, mock_requests)
        self.assert_requests_called_with(mock_requests, 'Frontend deployment process complete.',
                                         LambdaBuildTest.CONST_SUCCESS)

    @patch('lambda_build.requests')
    def test_lambda_handler_update_success(self, mock_requests):
        self.assert_create_update(self.event_update, mock_requests)
        self.assert_requests_called_with(mock_requests, 'Frontend redeployed from AWS master.',
                                         LambdaBuildTest.CONST_SUCCESS)

    @patch('lambda_build.requests')
    def test_lambda_handler_delete_success(self, mock_requests):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        self.s3_client.upload_file(self.zipped_website, self.frontend_bucket, 'some_key')
        response = lambda_build.lambda_handler(self.event_delete, self.lambda_context)
        self.assertEqual(self.response_success, response)
        # s3_response = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)
        # self.assertTrue('Contents' not in s3_response)
        # the method deleting the contents is commented out
        # for now check there is no deletion and a separate test for delete function
        contents = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)['Contents']
        self.assertEqual(1, len(contents))
        file_names = sorted([content['Key'] for content in contents])
        self.assertEqual(['some_key'], file_names)
        self.assert_requests_called_with(mock_requests,
                                         f'S3 Bucket should be manually emptied : {self.frontend_bucket}',
                                         LambdaBuildTest.CONST_SUCCESS)

    def test_remove_static_site(self):
        import lambda_build
        self.s3_client.upload_file(self.zipped_website, self.frontend_bucket, 'some_key')
        lambda_build.remove_static_site()
        s3_response = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)
        self.assertTrue('Contents' not in s3_response)

    @patch('lambda_build.requests')
    def test_lambda_handler_unknown_success(self, mock_requests):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_build.lambda_handler(self.event_unknown, self.lambda_context)
        self.assertEqual(self.response_success, response)
        s3_response = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)
        self.assertTrue('Contents' not in s3_response)
        self.assert_requests_called_with(mock_requests, 'Unexpected event received from CloudFormation',
                                         LambdaBuildTest.CONST_SUCCESS)

    @patch('lambda_build.requests')
    def test_lambda_handler_create_requests_exception(self, mock_requests):
        import lambda_build
        mock_requests.put.side_effect = Exception('Simulated Exception')
        response = lambda_build.lambda_handler(self.event_create, self.lambda_context)
        self.assertEqual(self.response_failed, response)
        # but the contents are uploaded
        contents = self.s3_client.list_objects_v2(Bucket=self.frontend_bucket)['Contents']
        self.assertEqual(3, len(contents))
        file_names = sorted([content['Key'] for content in contents])
        self.assertEqual(['env.js', 'index.html', 'second_file.html'], file_names)

    @patch('lambda_build.requests')
    def test_lambda_handler_create_zip_too_big(self, mock_requests):
        import lambda_build
        lambda_build.ZIP_MAX_SIZE = 10
        # error ignored
        self.assert_create_update(self.event_create, mock_requests)
        self.assert_requests_called_with(mock_requests,
                                         'Frontend deployment process complete.', LambdaBuildTest.CONST_SUCCESS)

    @patch('lambda_build.requests')
    def test_lambda_handler_create_invalid_zip(self, mock_requests):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        invalid_zip_file = os.path.dirname(os.path.realpath(__file__)) + '/sample_data/build/index.html'
        self.s3_client.upload_file(invalid_zip_file, self.source_bucket, self.source_key)
        self.assert_create_failed_returning_success(mock_requests)

    @patch('lambda_build.requests')
    def test_lambda_handler_create_no_file_in_source(self, mock_requests):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        self.s3_client.delete_object(Bucket=self.source_bucket, Key=self.source_key)
        self.assert_create_failed_returning_success(mock_requests)

    @patch('lambda_build.mimetypes')
    @patch('lambda_build.requests')
    def test_lambda_handler_create_exception(self, mock_requests, mock_deploy_static_site):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        mock_deploy_static_site.side_effect = Exception('Simulated Exception')
        self.assert_create_failed_returning_success(mock_requests)

    @patch('lambda_build.mimetypes')
    @patch('lambda_build.requests')
    def test_lambda_handler_create_mime_type_none(self, mock_requests, mock_mimetypes):
        import lambda_build
        mock_requests.put.return_value = RequestsResponse(200)
        mock_mimetypes.guess_type.return_value = (None, None)
        self.assert_create_update(self.event_create, mock_requests)
        self.assert_requests_called_with(mock_requests, 'Frontend deployment process complete.',
                                         LambdaBuildTest.CONST_SUCCESS)

    @patch('lambda_build.mimetypes')
    @patch('lambda_build.requests')
    def test_lambda_handler_create_mime_type_exception(self, mock_requests, mock_mimetypes):
        import lambda_build
        mock_mimetypes.guess_type.side_effect = Exception('Simulated Exception')
        self.assert_create_failed_returning_success(mock_requests)

    @patch('lambda_build.mimetypes')
    @patch('lambda_build.requests')
    def test_lambda_handler_create_mime_type_client_error(self, mock_requests, mock_mimetypes):
        import lambda_build
        mock_mimetypes.guess_type.side_effect = ClientError(operation_name='s3_all',
                                                            error_response={
                                                                'Error': {
                                                                    'Code': 500,
                                                                    'Message': 'Simulated Error'
                                                                }
                                                            })
        self.assert_create_failed_returning_success(mock_requests)
