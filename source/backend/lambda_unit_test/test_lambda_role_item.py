#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import unittest
from unittest import mock

import boto3
from moto import mock_aws
from test_common_utils import set_cors_flag, default_mock_os_environ
import test_common_utils


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_aws
class LambdaRoleItemTest(unittest.TestCase):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self) -> None:
        import lambda_role
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_policies(self.ddb_client, lambda_role.policies_table_name)
        test_common_utils.create_and_populate_roles(self.ddb_client, lambda_role.roles_table_name)

    def test_lambda_handler_get_success(self):
        set_cors_flag('lambda_role_item', True)
        import lambda_role_item
        event = {
            'httpMethod': 'GET',
            'pathParameters': {
                'role_id': '2',
            },
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': json.dumps({
                "role_id": "2",
                "groups": [{
                    "group_name": "readonly"
                }
                ],
                "policies": [{
                    "policy_id": "2"
                }
                ],
                "role_name": "FactoryReadOnly",
            }),
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_get_role_id_doesnt_exist(self):
        set_cors_flag('lambda_role_item', False)
        import lambda_role_item
        event = {
            'httpMethod': 'GET',
            'pathParameters': {
                'role_id': '22'
            },
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'role Id: 22 does not exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_body(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'malformed json input',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_with_role_id(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
                'role_id': '2',
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'You cannot modify role_id, this is managed by the system',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_policies(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'attribute policies is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_policy_id(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
                'policies': [{
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'attribute policy_id is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_role_name(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
                'policies': [{
                    'policy_id': '2'
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'attribute role_name is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_groups(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
                'policies': [{
                    'policy_id': '2'
                }],
                'role_name': 'FactoryReadOnly',
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'attribute groups is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_group_name(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
                'policies': [{
                    'policy_id': '2'
                }],
                'role_name': 'FactoryReadOnly',
                'groups': [{
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'attribute group_name is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_role_id_doesnt_exist(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'role_id': '22',
            },
            'body': json.dumps({
                'policies': [{
                    'policy_id': '2'
                }],
                'role_name': 'FactoryReadOnly',
                'groups': [{
                    'group_name': 'readonly'
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'role Id: 22 does not exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_policy_id_doesnt_exist(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'role_id': '2',
            },
            'body': json.dumps({
                'policies': [{
                    'policy_id': '22'
                }],
                'role_name': 'FactoryReadOnly',
                'groups': [{
                    'group_name': 'readonly'
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'One or more policy_id in ' + str([{'policy_id': '22'}]) + ' does not exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_duplicate_role_name(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'role_id': '1',
            },
            'body': json.dumps({
                'policies': [{
                    'policy_id': '2'
                }],
                'role_name': 'FactoryReadOnly',
                'groups': [{
                    'group_name': 'readonly'
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'role_name: FactoryReadOnly already exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_success(self):
        import lambda_role_item
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'role_id': '2',
            },
            'body': json.dumps({
                'policies': [{
                    'policy_id': '2'
                }],
                'role_name': 'TestRole',
                'groups': [{
                    'group_name': 'TestGroup'
                }]
            }),
        }
        response = lambda_role_item.lambda_handler(event, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        inserted_item = lambda_role_item.role_table.get_item(Key={'role_id': '2'})['Item']
        expected_item = {
            'role_id': '2',
            'role_name': 'TestRole',
            'policies': [
                {
                    'policy_id': '2'
                }
            ],
            'groups': [
                {
                    'group_name': 'TestGroup'
                }
            ]
        }
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_delete_success(self):
        import lambda_role_item
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'role_id': '2',
            },
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'Role ' + str({
                'role_id': '2',
                'groups': [{
                    'group_name': 'readonly'
                }
                ],
                'policies': [{
                    'policy_id': '2'
                }],
                'role_name': 'FactoryReadOnly'
            }) + ' was successfully deleted',
            'statusCode': 200
        }
        self.assertEqual(expected, response)
        deleted_item = lambda_role_item.role_table.get_item(Key={'role_id': '2'})
        self.assertFalse('Item' in deleted_item)

    def test_lambda_handler_delete_doesnt_exist(self):
        import lambda_role_item
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'role_id': '11',
            },
        }
        response = lambda_role_item.lambda_handler(event, None)
        expected = {
            'headers': lambda_role_item.default_http_headers,
            'body': 'role Id: 11 does not exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)
