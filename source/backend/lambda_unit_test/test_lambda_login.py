#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
import json
import os
from unittest import mock
from unittest.mock import patch

import boto3
from moto import mock_aws
from test_lambda_login_common import mock_boto_api_call_success, \
    mock_boto_api_call_exception, mock_boto_api_call_exception_unexpected
from test_common_utils import set_cors_flag, logger, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'clientId': 'test_client_id'
}


@mock.patch.dict('os.environ', mock_os_environ)
class LambdaLoginTest(unittest.TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self):
        self.user_name = 'testUserName'
        self.temporary_password = 'P2$Sword'
        self.mfa_code = 'testMfaCode'
        self.session = 'testSession'
        self.pool_name = 'testuserPool'
        self.client_name = 'testClientName'
        self.attribute1_name = 'testAttributeName'
        self.new_password = ''.join(reversed(self.temporary_password))
        self.user_pool_id = ''
        self.test_client = boto3.client('cognito-idp')
        self.event = {
            'body': json.dumps({
                'username': self.user_name,
                'password': self.new_password,
                'session': self.session,
            })
        }
        self.event_mfa = {
            'body': json.dumps({
                'username': self.user_name,
                'password': self.new_password,
                'session': self.session,
                'mfacode': 'MFA_CODE_123'
            })
        }

    def create_cognito_user(self):

        result = self.test_client.create_user_pool(
            PoolName=self.pool_name,
            AutoVerifiedAttributes=['email']
        )
        self.user_pool_id = result['UserPool']['Id']
        client_id = self.test_client.create_user_pool_client(
            UserPoolId=self.user_pool_id,
            ClientName=self.client_name,
            ReadAttributes=[self.attribute1_name],
            GenerateSecret=True,
        )['UserPoolClient']['ClientId']
        os.environ['clientId'] = client_id
        self.test_client.admin_create_user(
            UserPoolId=self.user_pool_id,
            Username=self.user_name,
            TemporaryPassword=self.temporary_password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': 'email@example.com'
                },
                {
                    'Name': 'User Name',
                    'Value': self.attribute1_name
                }
            ],
        )

        result = self.test_client.admin_initiate_auth(
            UserPoolId=self.user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": self.user_name, "PASSWORD": self.temporary_password},
        )
        result = self.test_client.respond_to_auth_challenge(
            Session=result["Session"],
            ClientId=client_id,
            ChallengeName="NEW_PASSWORD_REQUIRED",
            ChallengeResponses={"USERNAME": self.user_name, "NEW_PASSWORD": self.new_password},
        )
        logger.debug(result)
        result = self.test_client.admin_update_user_attributes(
            UserPoolId=self.user_pool_id,
            Username=self.user_name,
            UserAttributes=[
                {
                    'Name': 'email_verified',
                    'Value': 'true'
                },
            ],
        )
        logger.debug(result)
        result = self.test_client.admin_user_global_sign_out(
            UserPoolId=self.user_pool_id,
            Username=self.user_name
        )
        logger.debug(result)

    @mock_aws
    def test_lambda_login_with_password(self):
        import lambda_login
        self.create_cognito_user()
        response = lambda_login.lambda_handler(self.event, {})
        self.assertEqual(200, response['statusCode'])

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_success)
    def test_lambda_handler_next_challenge(self):
        import lambda_login
        response = lambda_login.lambda_handler(self.event, None)
        expected = {
            'headers': lambda_login.default_http_headers,
            'body': json.dumps({
                'ChallengeName': 'NEW_PASSWORD_REQUIRED',
                'Session': 'TEST_SESSION'
            }),
            'statusCode': 200,
        }
        self.assertEqual(expected, response)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_exception)
    def test_lambda_handler_exception(self):
        import lambda_login
        response = lambda_login.lambda_handler(self.event, None)
        expected = {
            'headers': lambda_login.default_http_headers,
            'body': 'Incorrect username or password',
            'statusCode': 400,
        }
        self.assertEqual(expected, response)


    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_exception)
    def test_lambda_handler_exception(self):
        import lambda_login
        response = lambda_login.lambda_handler(self.event, None)
        expected = {
            'headers': lambda_login.default_http_headers,
            'body': 'Incorrect username or password',
            'statusCode': 400,
        }
        self.assertEqual(expected, response)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_exception_unexpected)
    def test_lambda_handler_exception_unexpected(self):
        set_cors_flag('lambda_login', True)
        import lambda_login
        response = lambda_login.lambda_handler(self.event, None)
        self.assertEqual(None, response)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_success)
    def test_lambda_handler_mfa(self):
        set_cors_flag('lambda_login', False)
        import lambda_login
        response = lambda_login.lambda_handler(self.event_mfa, None)
        expected = {
            'headers': lambda_login.default_http_headers,
            'body': '"TOKEN_123"',
            'statusCode': 200,
        }
        self.assertEqual(expected, response)