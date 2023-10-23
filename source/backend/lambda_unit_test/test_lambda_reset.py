#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
import json
from unittest import mock
from unittest.mock import patch


from test_common_utils import set_cors_flag, default_mock_os_environ
from test_lambda_login_common import mock_boto_api_call_success, mock_boto_api_call_incorrect_chanllenge, \
    mock_boto_api_call_exception, mock_boto_api_call_exception_unexpected


mock_os_environ = {
    **default_mock_os_environ,
    'clientId': 'test_client_id'
}


@mock.patch.dict('os.environ', mock_os_environ)
class LambdaResetTest(unittest.TestCase):

    def setUp(self) -> None:
        self.event = {
            'body': json.dumps({
                'username': 'user_name',
                'oldpassword': 'old_password',
                'newpassword': 'new_password'
            })
        }

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_success)
    def test_lambda_handler_success(self):
        set_cors_flag('lambda_reset', True)
        import lambda_reset
        response = lambda_reset.lambda_handler(self.event, None)
        expected = {
            'headers': lambda_reset.default_http_headers,
            'body': json.dumps({
                'AuthenticationResult': {
                    'IdToken': 'TOKEN_123'
                }
            }),
            'statusCode': 200,
        }
        self.assertEqual(expected, response)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_incorrect_chanllenge)
    def test_lambda_handler_incorrect_challenge(self):
        set_cors_flag('lambda_reset', True)
        import lambda_reset
        response = lambda_reset.lambda_handler(self.event, None)
        expected = {
            'headers': lambda_reset.default_http_headers,
            'body': json.dumps({
                'ChallengeName': 'NEW_PASSWORD_REQUIRED_INCORRECT',
                'Session': 'TEST_SESSION'
            }),
            'statusCode': 200,
        }
        self.assertEqual(expected, response)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_exception)
    def test_lambda_handler_exception(self):
        set_cors_flag('lambda_reset', False)
        import lambda_reset
        response = lambda_reset.lambda_handler(self.event, None)
        expected = {
            'headers': lambda_reset.default_http_headers,
            'body': 'Incorrect old username or password',
            'statusCode': 400,
        }
        self.assertEqual(expected, response)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call_exception_unexpected)
    def test_lambda_handler_exception_unexpected(self):
        set_cors_flag('lambda_reset', False)
        import lambda_reset
        self.assertRaises(UnboundLocalError,
                          lambda_reset.lambda_handler, self.event, None)
