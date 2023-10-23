#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
from unittest import mock
from unittest.mock import patch, ANY

from test_lambda_cognito_base import CognitoTestsBase

import boto3
from moto import mock_cognitoidp, mock_secretsmanager
from test_common_utils import LambdaContextLogStream, RequestsResponse, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'ServiceAccountEmail': 'test_email@example.com',
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_cognitoidp
@mock_secretsmanager
class LambdaServiceAccountTest(CognitoTestsBase):

    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        super().setUp()
        self.create_user_pool_and_group()
        self.set_env_vars()
        self.test_url = 'http://example.com'
        self.test_resource_id = 'SA_LOGICAL_RESOURCE_ID_101'
        self.test_request_id = 'SA_REQUEST_ID_101'
        self.test_stack_id = 'SA_TEST_STACK_101'
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
        self.event_unexpected['RequestType'] = 'Unexpected'

        self.log_stream_name = 'testing'
        self.lambda_context = LambdaContextLogStream(self.log_stream_name)

    def create_user_pool_and_group(self):
        self.create_user_pool()
        self.create_group(self.test_group_name_1)

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
        import lambda_service_account
        self.set_global_vars(lambda_service_account)
        mock_requests.put.return_value = RequestsResponse(status)
        response = lambda_service_account.lambda_handler(event, self.lambda_context)
        expected = {
            'Response': status
        }
        self.assertEqual(expected, response)
        self.assert_requests_called_with(mock_requests, message, status)

    def assert_service_account_and_secret_created(self):
        import lambda_service_account
        user_created = self.boto_cognito_client.admin_get_user(
            UserPoolId=lambda_service_account.PoolId,
            Username=lambda_service_account.ServiceAccountEmail
        )
        self.assertEqual(lambda_service_account.ServiceAccountEmail, user_created['Username'])
        secrets_manager_client = boto3.client('secretsmanager')
        secret_id = 'MFServiceAccount-' + lambda_service_account.PoolId
        secret = secrets_manager_client.get_secret_value(SecretId=secret_id)
        self.assertEqual(secret_id, secret['Name'])

    def assert_service_account_and_secret_not_created(self):
        import lambda_service_account
        self.assertRaises(self.boto_cognito_client.exceptions.UserNotFoundException,
                          self.boto_cognito_client.admin_get_user,
                          UserPoolId=lambda_service_account.PoolId,
                          Username=lambda_service_account.ServiceAccountEmail)
        secrets_manager_client = boto3.client('secretsmanager')
        secret_id = 'MFServiceAccount-' + lambda_service_account.PoolId
        self.assertRaises(secrets_manager_client.exceptions.ResourceNotFoundException,
                          secrets_manager_client.get_secret_value,
                          SecretId=secret_id)

    def set_global_vars(self, module_imported):
        module_imported.PoolId = self.user_pool_id
        module_imported.CognitoGroup = self.test_group_name_1

    def set_env_vars(self):
        os.environ['UserPoolId'] = self.user_pool_id
        os.environ['CognitoGroupName'] = self.test_group_name_1

    @patch('lambda_service_account.requests')
    def test_lambda_handler_create_success(self, mock_requests):
        self.assert_events_success(self.event_create, mock_requests,
                                   'SUCCESS', 'Migration Factory Service Account created successfully')
        self.assert_service_account_and_secret_created()

    @patch('lambda_service_account.requests')
    def test_lambda_handler_update_success(self, mock_requests):
        self.assert_events_success(self.event_update, mock_requests,
                                   'SUCCESS', 'No update required')
        self.assert_service_account_and_secret_not_created()

    @patch('lambda_service_account.requests')
    def test_lambda_handler_delete_success(self, mock_requests):
        self.assert_events_success(self.event_delete, mock_requests,
                                   'SUCCESS', 'No deletion required')
        self.assert_service_account_and_secret_not_created()

    @patch('lambda_service_account.requests')
    def test_lambda_handler_unexpected_success(self, mock_requests):
        self.assert_events_success(self.event_unexpected, mock_requests,
                                   'SUCCESS', 'Unexpected event received from CloudFormation')
        self.assert_service_account_and_secret_not_created()

    @patch('lambda_service_account.requests')
    @patch('lambda_service_account.create_service_account')
    def test_lambda_handler_create_service_exception(self, mock_create_service_account, mock_requests):
        import lambda_service_account
        self.set_global_vars(lambda_service_account)
        mock_create_service_account.side_effect = Exception('Simulated Exception')
        response = lambda_service_account.lambda_handler(self.event_create, self.lambda_context)
        expected = {
            'Response': 'SUCCESS'
        }
        self.assertEqual(expected, response)
        self.assert_requests_called_with(mock_requests, 'Exception during processing', 'FAILED')
        self.assert_service_account_and_secret_not_created()

    @patch('lambda_service_account.requests')
    def test_lambda_handler_create_request_exception(self, mock_requests):
        import lambda_service_account
        self.set_global_vars(lambda_service_account)
        mock_requests.put.side_effect = Exception('Simulated Exception')
        response = lambda_service_account.lambda_handler(self.event_create, self.lambda_context)
        expected = {
            'Response': 'FAILED'
        }
        self.assertEqual(expected, response)
        self.assert_service_account_and_secret_created()
