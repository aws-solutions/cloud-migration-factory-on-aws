#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import json
import jwt
import os
import unittest
from unittest.mock import patch

import boto3
from unittest import mock
from datetime import datetime, timedelta
import time
from contextlib import contextmanager

from moto import mock_aws

from test_common_utils import default_mock_os_environ
import test_common_utils

mock_os_environ = {
    **default_mock_os_environ,
    'userpool_id': 'test_userpool_id',
    'app_client_id': 'test_app_client_id'
}

with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/jwtRS256.key') as key_file:
    private_key = key_file.read()


def mock_urllib_urlopen():

    class UrlOpenResponse:
        def __init__(self, jwt_data):
            self.jwt_data = jwt_data

        def __enter__(self):
            self.clone_jwt_data = self.jwt_data.copy()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.jwt_data = self.clone_jwt_data
            else:
                print(f'@UrlOpenResponse: Error occurred while processing the jwt. The changes are discarded. {exc_type} - {exc_val} - {exc_tb}')
            return True

        def read(self):
            return json.dumps(self.jwt_data)

    with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/ssm_socket_cognito_jwks.json') \
            as json_file:
        jwt_sample = json.load(json_file)

    return UrlOpenResponse(jwt_sample)

def mock_urllib_urlopen_failure():

    class UrlOpenResponse:
        def __init__(self, jwt_data):
            self.jwt_data = jwt_data

        def __enter__(self):
            self.clone_jwt_data = self.jwt_data.copy()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.jwt_data = self.clone_jwt_data
            else:
                print(f'@UrlOpenResponse: Error occurred while processing the jwt. The changes are discarded. {exc_type} - {exc_val} - {exc_tb}')
            return True

        def read(self):
            return json.dumps(self.jwt_data)

    with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/ssm_socket_cognito_jwks_error.json') \
            as json_file:
        jwt_sample = json.load(json_file)

    return UrlOpenResponse(jwt_sample)


@patch('urllib.request.urlopen', return_value=mock_urllib_urlopen())
@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaSSMSocketTest(unittest.TestCase):

    @patch('urllib.request.urlopen', return_value=mock_urllib_urlopen())
    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self, _) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        import lambda_ssm_socket
        self.test_conn_id = '1'
        self.next_conn_id = '3'
        self.event_connect = {
            'requestContext': {
                'eventType': 'CONNECT',
                'connectionId': self.test_conn_id
            }
        }
        self.event_disconnect = copy.deepcopy(self.event_connect)
        self.event_disconnect['requestContext']['eventType'] = 'DISCONNECT'
        self.event_unknown = copy.deepcopy(self.event_connect)
        self.event_unknown['requestContext']['eventType'] = 'UNKNOWN'

        exp_time = datetime.utcnow() + timedelta(hours=5)
        kid = 'UPSZ26EORotKU88HFmnKO6Z1NgTVteSRMVwvIfqmpKA='

        self.event_message = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            },
            'body': json.dumps({
                'type': 'auth',
                'token':  jwt.encode({
                    'cmf': 'some_secret',
                    'exp': exp_time,
                    'iss': f'https://cognito-idp.{os.getenv("region")}.amazonaws.com/{os.getenv("userpool_id")}',
                    'aud': os.getenv('app_client_id'),
                    'email': 'example@example.com'
                }, private_key,
                    algorithm='RS256',
                    headers={
                        'kid': kid
                    }
                )
            })
        }

        self.event_message_invalid_aud = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            },
            'body': json.dumps({
                'type': 'auth',
                'token':  jwt.encode({
                    'cmf': 'some_secret',
                    'exp': exp_time,
                    'iss': f'https://cognito-idp.{os.getenv("region")}.amazonaws.com/{os.getenv("userpool_id")}',
                    'aud': os.getenv('app_client_id') + 'INVALID',
                    'email': 'example@example.com'
                }, private_key,
                    algorithm='RS256',
                    headers={
                        'kid': kid
                    }
                )
            })
        }

        self.event_message_expired = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            },
            'body': json.dumps({
                'type': 'auth',
                'token':  jwt.encode({
                    'cmf': 'some_secret',
                    'exp': time.time(),
                    'iss': f'https://cognito-idp.{os.getenv("region")}.amazonaws.com/{os.getenv("userpool_id")}',
                    'aud': os.getenv('app_client_id'),
                    'email': 'example@example.com'
                }, private_key,
                    algorithm='RS256',
                    headers={
                        'kid': kid
                    }
                )
            })
        }

        self.event_message_invalid_kid = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            },
            'body': json.dumps({
                'type': 'auth',
                'token':  jwt.encode({
                    'cmf': 'some_secret',
                    'exp': exp_time,
                    'iss': f'https://cognito-idp.{os.getenv("region")}.amazonaws.com/{os.getenv("userpool_id")}',
                    'aud': os.getenv('app_client_id'),
                    'email': 'example@example.com'
                }, private_key,
                    algorithm='RS256',
                    headers={
                        'kid': kid + 'INVALID'
                    }
                )
            })
        }

        self.event_message_invalid_format = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            },
            'body': json.dumps({
                'type_NO': 'auth',
            })
        }

        self.event_message_invalid_body = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            }
        }

        self.event_message_type_unsupported = {
            'requestContext': {
                'eventType': 'MESSAGE',
                'connectionId': self.next_conn_id
            },
            'body': json.dumps({
                'type': 'unsupported',
            })
        }

        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_connection_ids(self.ddb_client,
                                                             lambda_ssm_socket.connectionIds_table_name)

    def test_lambda_handler_connect_success(self, mock_urlopen):
        import lambda_ssm_socket
        response = lambda_ssm_socket.lambda_handler(self.event_connect, None)
        expected = {
            'statusCode': 200,
            'body': 'Connection successful, authentication required.'
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_disconnect_success(self, mock_urlopen):
        import lambda_ssm_socket
        response = lambda_ssm_socket.lambda_handler(self.event_disconnect, None)
        expected = {
            'statusCode': 200,
            'body': 'Disconnect successful'
        }
        self.assertEqual(expected, response)
        conn_table = boto3.resource('dynamodb').Table(lambda_ssm_socket.connectionIds_table_name)
        response = conn_table.scan(Limit=10)
        self.assertEqual(1, len(response['Items']))
        response = conn_table.get_item(Key={'connectionId': self.test_conn_id})
        self.assertTrue('Item' not in response)

    def test_lambda_handler_message_success(self, mock_urlopen):
        import lambda_ssm_socket
        response = lambda_ssm_socket.lambda_handler(self.event_message, None)
        expected = {
            'statusCode': 200,
            'body': 'Authentication successful'
        }
        self.assertEqual(expected, response)
        conn_table = boto3.resource('dynamodb').Table(lambda_ssm_socket.connectionIds_table_name)
        response = conn_table.scan(Limit=10)
        self.assertEqual(3, len(response['Items']))
        new_conn = conn_table.get_item(Key={'connectionId': self.next_conn_id})['Item']
        self.assertEqual(self.next_conn_id, new_conn['connectionId'])
        self.assertEqual('example@example.com', new_conn['email'])

    def assert_invalid(self, event, message='Invalid token'):
        import lambda_ssm_socket
        response = lambda_ssm_socket.lambda_handler(event, None)
        print(response)
        expected = {
            'statusCode': 400,
            'body': message
        }
        self.assertEqual(expected, response)
        conn_table = boto3.resource('dynamodb').Table(lambda_ssm_socket.connectionIds_table_name)
        response = conn_table.scan(Limit=10)
        self.assertEqual(2, len(response['Items']))
        response = conn_table.get_item(Key={'connectionId': self.next_conn_id})
        self.assertTrue('Item' not in response)

    def test_lambda_handler_message_expired(self, mock_urlopen):
        self.assert_invalid(self.event_message_expired)

    def test_lambda_handler_message_invalid_aud(self, mock_urlopen):
        self.assert_invalid(self.event_message_invalid_aud)

    def test_lambda_handler_message_invalid_kid(self, mock_urlopen):
        self.assert_invalid(self.event_message_invalid_kid)

    def test_lambda_handler_message_invalid_format(self, mock_urlopen):
        self.assert_invalid(self.event_message_invalid_format, 'Invalid message format')

    def test_lambda_handler_message_invalid_body(self, mock_urlopen):
        self.assert_invalid(self.event_message_invalid_body, 'Error converting message to JSON')

    def test_lambda_handler_message_type_unsupported(self, mock_urlopen):
        self.assert_invalid(self.event_message_type_unsupported, 'Unsupported message type, full message:')

    def test_lambda_handler_unknown(self, mock_urlopen):
        self.assert_invalid(self.event_unknown, 'Unsupported event type.')

    def test_lambda_handler_message_verify_failure(self, mock_urlopen):
        import lambda_ssm_socket
        mock_urlopen.return_value = mock_urllib_urlopen_failure()
        response = lambda_ssm_socket.lambda_handler(self.event_message, None)
        expected = {
            'statusCode': 400,
            'body': 'Invalid token'
        }
        self.assertEqual(expected, response)
        conn_table = boto3.resource('dynamodb').Table(lambda_ssm_socket.connectionIds_table_name)
        response = conn_table.scan(Limit=10)
        self.assertEqual(2, len(response['Items']))
        response = conn_table.get_item(Key={'connectionId': self.next_conn_id})
        self.assertTrue('Item' not in response)

    def test_get_response(self, mock_urlopen):
        # added just to get higher coverage
        import lambda_ssm_socket
        message_ok = {
            'message': 'OK'
        }
        response = lambda_ssm_socket._get_response(200, message_ok)
        expected = {
            'statusCode': 200,
            'body': json.dumps(message_ok)
        }
        self.assertEqual(expected, response)


