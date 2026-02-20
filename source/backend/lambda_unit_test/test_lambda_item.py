#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda_functions'))

import json
from unittest import mock

import botocore
from moto import mock_aws
import test_common_utils
from test_lambda_item_common import LambdaItemCommonTest, mock_item_check_valid_item_create_valid, \
    mock_item_check_valid_item_create_in_valid
from test_common_utils import logger, default_mock_os_environ as mock_os_environ, \
    mock_get_mf_auth_policy_allow, mock_get_mf_auth_policy_default_deny


orig_boto_api_call = botocore.client.BaseClient._make_api_call


def mock_boto_api_call(obj, operation_name, kwarg):
    logger.debug(f'{obj}: operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'DeleteItem':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 500
            },
            'Error': 'Unexpected Error'
        }
    if operation_name == 'Query':
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 500
            },
            'Error': 'Unexpected Error'
        }
    else:
        return orig_boto_api_call(obj, operation_name, kwarg)


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaItemTest(LambdaItemCommonTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        super().setUp()
        self.init_event_objects()
    
    def tearDown(self) -> None:
        # Reset any module-level state
        import sys
        if 'lambda_item' in sys.modules:
            del sys.modules['lambda_item']
        if 'shared.items.common' in sys.modules:
            del sys.modules['shared.items.common']
        super().tearDown()

    def init_event_objects(self):
        self.event_get_existing_app_item = {
            'app_id': '1',
            'app_name': 'Wordpress',
            'aws_accountid': test_common_utils.test_account_id,
            'aws_region': 'us-east-1',
            'wave_ids': ['1'],
            'tags': ['tag1', 'tag2'],
            'description': 'The amazing wordpress'
        }
        
        self.event_get_success_id = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            }
        }
        
        self.event_get_app_no_exist = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'app',
                'id': 'NO_EXIST'
            }
        }
        
        self.event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'app_name': 'updated app name',
                'new_attr': 123,
                'description': '',
                'tags': ['']
            })
        }
        
        self.event_put_app_id_matching = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'schema': 'app',
                'app_id': '1'
            })
        }
        
        self.event_put_app_id_mismatch = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'schema': 'app',
                'app_id': '2'
            })
        }
        
        self.event_put_invalid_body = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': 'INVALID JSON'
        }
        
        self.event_put_no_exist = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': 'NO_EXIST'
            },
            'body': json.dumps({})
        }
        
        self.event_put_dup = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'app_name': 'OFBiz'
            })
        }
        
        self.event_put_without_id = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'app_name': 'Updated App Name',
                'description': 'Updated description'
            })
        }

        self.event_delete = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            }
        }
        
        self.event_delete_no_exist = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'schema': 'app',
                'id': 'NO_EXIST'
            }
        }
        
        # IAM request events
        self.event_iam_put_valid = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app'
            },
            'requestContext': {
                'identity': {
                    'userArn': 'arn:aws:iam::123456789012:user/test-user'
                }
            },
            'body': json.dumps({
                'auth_info': {
                    'claims': {
                        'sub': 'user123',
                        'email': 'testuser@example.com',
                        'cognito:groups': 'admin,users',
                        'cognito:username': 'testuser'
                    }
                },
                'data': [
                    {'app_id': '1', 'app_name': 'Updated App 1', 'description': 'Updated'},
                    {'app_id': '2', 'app_name': 'Updated App 2', 'description': 'Updated'}
                ]
            })
        }

    def assert_get_success(self, lambda_item, event, list_response=False):
        response = lambda_item.lambda_handler(event, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)

        if list_response:
            self.assertEqual([self.event_get_existing_app_item], json.loads(response['body']))
        else:
            self.assertEqual(self.event_get_existing_app_item, json.loads(response['body']))

    def assert_put_success(self, lambda_item, event, len_history=2):
        response = lambda_item.lambda_handler(event, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        body = json.loads(response['body'])
        self.assertEqual(200, body['ResponseMetadata']['HTTPStatusCode'])
        updated_item = self.apps_table.get_item(Key={'app_id': '1'})['Item']
        self.assertEqual('updated app name', updated_item['app_name'])
        self.assertEqual(123, updated_item['new_attr'])
        self.assertEqual(['1'], updated_item['wave_ids'])
        self.assertTrue('description' not in updated_item)
        self.assertTrue('tags' not in updated_item)
        self.assertEqual(len_history, len(updated_item['_history'].keys()))

    def test_lambda_handler_schema_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_schema_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Invalid schema provided :NO_EXIST', response['body'])

    def test_lambda_handler_get_success_id(self):
        import lambda_item
        self.assert_get_success(lambda_item, self.event_get_success_id)

    def test_lambda_handler_get_app_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_get_app_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app Id NO_EXIST does not exist']}, json.loads(response['body']))

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_put_not_authorized(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual({'errors': [{'action': 'deny', 'cause': 'Request is not Authenticated'}]},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    def test_lambda_handler_put_app_id_matching(self, mock_mfauth):
        """Test PUT request with app_id in body that matches path parameter"""
        mock_mfauth.return_value.get_user_attribute_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_app_id_matching, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response or response.get('statusCode') == 200)

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_app_id_mismatch(self):
        """Test PUT request with app_id in body that doesn't match path parameter"""
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_app_id_mismatch, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['The app_id in the request body (2) does not match the ID in the path parameter (1)']},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_invalid_body(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_invalid_body, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['malformed json input']},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    def test_lambda_handler_put_success(self, mock_mfauth):
        mock_mfauth.return_value.get_user_attribute_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_item
        self.assert_put_success(lambda_item, self.event_put)

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app Id: NO_EXIST does not exist']}, json.loads(response['body']))

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_dup(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_dup, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app_name: OFBiz already exist']},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.get_auth_response_for_deletion',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_delete_not_authorized(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual({'errors': [{'action': 'deny', 'cause': 'Request is not Authenticated'}]},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.get_auth_response_for_deletion',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_delete_success(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual('Item was successfully deleted.', response['body'])
        response = self.apps_table.get_item(Key={'app_id': '1'})
        self.assertTrue('Item' not in response)

    @mock.patch('shared.items.common.get_auth_response_for_deletion',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_delete_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app Id: NO_EXIST does not exist']},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.get_auth_response_for_deletion',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_delete_with_protection(self):
        import lambda_item
        
        # Add deletion protection to the item
        self.apps_table.update_item(
            Key={'app_id': '1'},
            UpdateExpression='SET deletion_protection = :val',
            ExpressionAttributeValues={':val': True}
        )
        
        response = lambda_item.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['Record has deletion protection flag enabled, and cannot be deleted.']},
                         json.loads(response['body']))

    # IAM Request Tests
    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.does_item_with_name_exist', return_value=False)
    def test_lambda_handler_iam_put_success(self, mock_name_exists, mock_mfauth):
        mock_mfauth.return_value.get_user_attribute_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_item
        response = lambda_item.lambda_handler(self.event_iam_put_valid, None)
        
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        
        body = json.loads(response['body'])
        self.assertIn('results', body)
        self.assertEqual(2, len(body['results']))

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_iam_put_bulk_auth_denied(self):
        """Test IAM PUT request when bulk authorization is denied"""
        import lambda_item
        response = lambda_item.lambda_handler(self.event_iam_put_valid, None)
        
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        
        body = json.loads(response['body'])
        self.assertIn('errors', body)

    def test_lambda_handler_iam_put_missing_auth_info(self):
        """Test IAM PUT request when auth_info is missing from body"""
        import lambda_item
        
        event_missing_auth = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema': 'app'},
            'requestContext': {
                'identity': {
                    'userArn': 'arn:aws:iam::123456789012:user/test-user'
                }
            },
            'body': json.dumps({
                'data': [{'app_id': '1', 'app_name': 'Updated App 1'}]
            })
        }
        
        response = lambda_item.lambda_handler(event_missing_auth, None)
        
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        
        body = json.loads(response['body'])
        self.assertIn('errors', body)

    def test_create_bulk_auth_event(self):
        """Test the create_bulk_auth_event function"""
        import lambda_item
        
        items = [
            {'app_id': '1', 'app_name': 'App1', 'description': 'Desc1'},
            {'app_id': '2', 'app_name': 'App2', 'tags': ['tag1']}
        ]
        auth_info = {'user': 'testuser'}
        
        result = lambda_item.create_bulk_auth_event(items, 'app', auth_info)
        
        self.assertEqual(result['pathParameters']['id'], 'bulk_auth_check')
        self.assertEqual(result['requestContext']['authorizer'], auth_info)
        
        body = json.loads(result['body'])
        expected_attrs = {'app_id', 'app_name', 'description', 'tags'}
        self.assertEqual(set(body.keys()), expected_attrs)
        
        # All values should be the placeholder
        for value in body.values():
            self.assertEqual(value, 'bulk_check_value')

    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    def test_lambda_handler_put_numeric_id_matching(self, mock_mfauth):
        """Test PUT request with numeric ID in body that matches path parameter"""
        mock_mfauth.return_value.get_user_attribute_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_item
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'app_id': 1,  # Numeric ID
                'app_name': 'Updated App'
            })
        }
        
        response = lambda_item.lambda_handler(event, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response or response.get('statusCode') == 200)

    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_numeric_id_mismatch(self):
        """Test PUT request with numeric ID in body that doesn't match path parameter"""
        import lambda_item
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'app_id': 2,  # Numeric ID that doesn't match
                'app_name': 'Updated App'
            })
        }
        
        response = lambda_item.lambda_handler(event, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['The app_id in the request body (2) does not match the ID in the path parameter (1)']},
                         json.loads(response['body']))

    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('shared.items.common.get_auth_response',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    def test_lambda_handler_put_without_id_field(self, mock_mfauth):
        """Test PUT request without ID field in body (should work normally)"""
        mock_mfauth.return_value.get_user_attribute_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_without_id, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response or response.get('statusCode') == 200)

    def test_lambda_handler_iam_put_invalid_s3_format(self):
        """Test IAM PUT request with invalid S3 format"""
        import lambda_item
        
        event_invalid_format = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema': 'app'},
            'requestContext': {
                'identity': {
                    'userArn': 'arn:aws:iam::123456789012:user/test-user'
                }
            },
            'body': json.dumps({
                'invalid_format': True
            })
        }
        
        response = lambda_item.lambda_handler(event_invalid_format, None)
        
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        
        body = json.loads(response['body'])
        self.assertIn('errors', body)
        self.assertEqual(['Invalid S3 import format'], body['errors'])

