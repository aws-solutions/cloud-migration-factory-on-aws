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
class LambdaRoleTest(unittest.TestCase):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self) -> None:
        import lambda_role
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_policies(self.ddb_client, lambda_role.policies_table_name)
        test_common_utils.create_and_populate_roles(self.ddb_client, lambda_role.roles_table_name)

    def test_lambda_handler_get_success(self):
        import lambda_role
        event_get = {
            'httpMethod': 'GET'
        }
        response = lambda_role.lambda_handler(event_get, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': json.dumps([
                {
                    'role_id': '1',
                    'groups': [
                        {
                            'group_name': 'admin'
                        }
                    ],
                    'policies': [
                        {
                            'policy_id': '1'
                        }
                    ],
                    'role_name': 'FactoryAdmin'
                },
                {
                    'role_id': '2',
                    'groups': [
                        {
                            'group_name': 'readonly'
                        }
                    ],
                    'policies': [
                        {
                            'policy_id': '2'
                        }
                    ],
                    'role_name': 'FactoryReadOnly'
                },
                {
                    'role_id': '3',
                    'groups': [
                        {
                            'group_name': 'orchestrator'
                        }
                    ],
                    'policies': [
                        {
                            'policy_id': '3'
                        }
                    ],
                    'role_name': 'FactoryAutomationTaskOrchestrator'
                }
            ]),
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_no_body(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST'
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'malformed json input',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_no_role_name(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({})
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'attribute role_name is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_no_policies(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'FactoryReadOnly'
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'attribute policies is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_no_policy_id(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'FactoryReadOnly',
                'policies': [
                    {}
                ]
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'attribute policy_id is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)
        
    def test_event_handler_post_no_groups(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'FactoryReadOnly',
                'policies': [
                    {
                        'policy_id': '2'
                    }
                ]
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'attribute groups is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_no_group_name(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'FactoryReadOnly',
                'policies': [
                    {
                        'policy_id': '2'
                    }
                ],
                'groups': [
                    {}
                ]
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'attribute group_name is required',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_already_exists(self):
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'FactoryReadOnly',
                'policies': [
                    {
                        'policy_id': '2'
                    }
                ],
                'groups': [
                    {
                        'group_name': 'readonly'
                    }
                ]
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'role_name already exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_policy_doesnt_exist(self):
        set_cors_flag('lambda_role', True)
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'TestRole',
                'policies': [
                    {
                        'policy_id': '22'
                    }
                ],
                'groups': [
                    {
                        'group_name': 'readonly'
                    }
                ]
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_role.default_http_headers,
            'body': 'One or more policy_id in ' + str([{'policy_id': '22'}]) + ' does not exist',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_event_handler_post_success(self):
        set_cors_flag('lambda_role', False)
        import lambda_role
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'role_name': 'TestRole',
                'policies': [
                    {
                        'policy_id': '3'
                    }
                ],
                'groups': [
                    {
                        'group_name': 'orchestrator'
                    }
                ]
            })
        }
        response = lambda_role.lambda_handler(event_post, None)
        print("HEREE")
        print(response)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        inserted_item = lambda_role.roles_table.get_item(Key={'role_id': '4'})['Item']
        expected_item = {
            'role_id': '4',
            'role_name': 'TestRole',
            'policies': [
                {
                    'policy_id': '3'
                }
            ],
            'groups': [
                {
                    'group_name': 'orchestrator'
                }
            ]
        }
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_put_unexpected(self):
        import lambda_role
        event_put = {
            'httpMethod': 'PUT'
        }
        response = lambda_role.lambda_handler(event_put, None)
        self.assertEqual(None, response)
