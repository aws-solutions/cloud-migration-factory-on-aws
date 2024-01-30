#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
from unittest import mock

import botocore
from moto import mock_dynamodb, mock_s3
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
@mock_s3
@mock_dynamodb
class LambdaItemTest(LambdaItemCommonTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        super().setUp()
        self.init_event_objects()

    def init_event_objects(self):

        self.event_get_existing_app_item = {
            'app_id': '1',
            'app_name': 'Wordpress',
            'aws_accountid': test_common_utils.test_account_id,
            'aws_region': 'us-east-1',
            'wave_id': '1',
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
        self.event_get_success_app_id = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'app',
                'appid': '1'
            }
        }
        self.event_get_no_exit_app_id = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'app',
                'appid': 'NO_EXIST'
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
                'new_attr': 'new test attribute',
                'description': '',
                'tags': ['']
            })
        }
        self.event_put_app_id = {
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
        self.event_put_with_history = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'schema': 'app',
                'id': '1'
            },
            'body': json.dumps({
                'app_name': 'updated app name',
                'new_attr': 'new test attribute',
                'description': '',
                'tags': [''],
                '_history': {
                    'createdTimestamp': 'Now',
                    'createdBy': 'user1'
                }
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
        self.assertEqual('new test attribute', updated_item['new_attr'])
        self.assertEqual('1', updated_item['wave_id'])
        self.assertTrue('description' not in updated_item)
        self.assertTrue('tags' not in updated_item)
        self.assertEqual(len_history, len(updated_item['_history'].keys()))

    def test_lambda_handler_schema_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_schema_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['Invalid schema provided :NO_EXIST']}, json.loads(response['body']))

    def test_lambda_handler_get_success_id(self):
        import lambda_item
        self.assert_get_success(lambda_item, self.event_get_success_id)

    def test_lambda_handler_get_success_app_id(self):
        import lambda_item
        self.assert_get_success(lambda_item, self.event_get_success_app_id, True)

    def test_lambda_handler_get_app_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_get_app_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app Id NO_EXIST does not exist']}, json.loads(response['body']))

    def test_lambda_handler_get_app_id_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_get_no_exit_app_id, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        self.assertEqual([], json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_get_exception(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_get_success_app_id, None)
        print(response)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['Error getting data from table for appid: 1']},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_put_not_authorized(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual({'errors': [{'action': 'deny', 'cause': 'Request is not Authenticated'}]},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_not_app_id(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_app_id, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['You cannot modify app_id, it is managed by the system']},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_invalid_body(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_invalid_body, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['malformed json input']},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_in_valid)
    def test_lambda_handler_put_check_valid_item_create_in_valid(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': [['Simulated error, attribute x is required']]},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    def test_lambda_handler_put_success(self):
        import lambda_item
        self.assert_put_success(lambda_item, self.event_put)

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_item.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    def test_lambda_handler_put_success_with_existing_history(self):
        import lambda_item
        self.assert_put_success(lambda_item, self.event_put_with_history, 4)

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app Id: NO_EXIST does not exist']},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_attribute_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_dup(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_put_dup, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app_name: OFBiz already exist']},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_delete_not_authorized(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual({'errors': [{'action': 'deny', 'cause': 'Request is not Authenticated'}]},
                         json.loads(response['body']))

    @mock.patch('lambda_item.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_delete_success(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual('Item was successfully deleted.', response['body'])
        response = self.apps_table.get_item(Key={'app_id': '1'})
        self.assertTrue('Item' not in response)

    @mock.patch('lambda_item.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_delete_exception(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(500, response['statusCode'])
        self.assertEqual({"errors": [{"ResponseMetadata": {"HTTPStatusCode": 500}, "Error": "Unexpected Error"}]},
                         json.loads(response['body']))
        response = self.apps_table.get_item(Key={'app_id': '1'})
        self.assertTrue('Item' in response)

    @mock.patch('lambda_item.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_delete_no_exist(self):
        import lambda_item
        response = lambda_item.lambda_handler(self.event_delete_no_exist, None)
        self.assertEqual(lambda_item.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['app Id: NO_EXIST does not exist']},
                         json.loads(response['body']))
