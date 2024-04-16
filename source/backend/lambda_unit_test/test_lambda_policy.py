#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import unittest
from unittest import mock

import boto3
from moto import mock_aws

import test_common_utils


@mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
@mock_aws
class LambdaPolicyTest(unittest.TestCase):

    @mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
    def setUp(self) -> None:
        import lambda_policy
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_policies(self.ddb_client, lambda_policy.policies_table_name)
        test_common_utils.create_and_populate_schemas(self.ddb_client, lambda_policy.schema_table_name)

    def test_lambda_handler_get_success(self):
        import lambda_policy
        event_get = {
            'httpMethod': 'GET'
        }
        response = lambda_policy.lambda_handler(event_get, None)
        expected = [
            {
                'policy_id': '1',
                'policy_name': 'Administrator'
            },
            {
                'policy_id': '2',
                'policy_name': 'ReadOnly'
            },
            {
                'policy_id': '3',
                'policy_name': 'CustomPolicy'
            }
        ]
        self.assertEqual(expected, json.loads(response['body']))

    def test_lambda_handler_post_no_body(self):
        import lambda_policy
        event_post_no_body = {
            'httpMethod': 'POST'
        }
        response = lambda_policy.lambda_handler(event_post_no_body, None)
        expected = {
                'headers': lambda_policy.default_http_headers,
                'statusCode': 400,
                'body': 'malformed json input',
            }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_no_policy_name(self):
        import lambda_policy
        event_post_no_policy_name = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name_X': 'Administrator'
            })
        }
        response = lambda_policy.lambda_handler(event_post_no_policy_name, None)
        expected = {
                'headers': lambda_policy.default_http_headers,
                'statusCode': 400,
                'body': 'attribute policy_name is required',
            }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_no_entity_access(self):
        import lambda_policy
        event_post_no_entity_access = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy.lambda_handler(event_post_no_entity_access, None)
        expected = {
                'headers': lambda_policy.default_http_headers,
                'statusCode': 400,
                'body': 'Empty policy, aborting save.',
            }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_policy_name_exists(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'Administrator',
                'entity_access': [
                    {
                        'schema_name': 'server'
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected = {
                'headers': lambda_policy.default_http_headers,
                'statusCode': 400,
                'body': 'policy_name: Administrator already exist.',
            }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_no_schema_name(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_policy.default_http_headers,
            'statusCode': 400,
            'body': 'Schema name key not found.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_schema_not_found(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'server_NOT_THERE'
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_policy.default_http_headers,
            'statusCode': 400,
            'body': 'server_NOT_THERE not a valid schema.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_flags_true(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'create': True,
                        'delete': False,
                        'update': False,
                        'read': True
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected_item = {
            'policy_name': 'test_policy',
            'policy_id': '4',
            'entity_access': [
                {
                    'schema_name': 'server',
                    'create': True,
                    'delete': False,
                    'update': False,
                    'read': True
                }
            ]
        }
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': json.dumps(expected_item),
        }
        self.assertEqual(expected, response)
        inserted_item = lambda_policy.policy_table.get_item(Key={'policy_id': '4'})['Item']
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_post_flags_false(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'server'
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected_item = {
            'policy_name': 'test_policy',
            'policy_id': '4',
            'entity_access': [
                {
                    'schema_name': 'server',
                    'create': False,
                    'delete': False,
                    'update': False,
                    'read': False
                }
            ]
        }
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': json.dumps(expected_item),
        }
        self.assertEqual(expected, response)
        inserted_item = lambda_policy.policy_table.get_item(Key={'policy_id': '4'})['Item']
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_post_schema_application(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'application'
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected_item = {
            'policy_name': 'test_policy',
            'policy_id': '4',
            'entity_access': [
                {
                    'schema_name': 'application',
                    'create': False,
                    'delete': False,
                    'update': False,
                    'read': False
                }
            ]
        }
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': json.dumps(expected_item),
        }
        self.assertEqual(expected, response)
        inserted_item = lambda_policy.policy_table.get_item(Key={'policy_id': '4'})['Item']
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_post_schema_type_automation(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'automation',
                        'schema_type': 'automation'
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected_item = {
            'policy_name': 'test_policy',
            'policy_id': '4',
            'entity_access': [
                {
                    'schema_name': 'automation',
                    'create': False,
                }
            ]
        }
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': json.dumps(expected_item),
        }
        self.assertEqual(expected, response)
        inserted_item = lambda_policy.policy_table.get_item(Key={'policy_id': '4'})['Item']
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_with_attributes(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'attributes': [
                            {
                                'attr_name': 'server_id'
                            }
                        ]
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected_item = {
            'policy_name': 'test_policy',
            'policy_id': '4',
            'entity_access': [
                {
                    'schema_name': 'server',
                    'create': False,
                    'delete': False,
                    'update': False,
                    'read': False,
                    'attributes': [
                        {
                            'attr_name': 'server_id'
                        }
                    ]
                }
            ]
        }
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': json.dumps(expected_item),
        }
        self.assertEqual(expected, response)
        inserted_item = lambda_policy.policy_table.get_item(Key={'policy_id': '4'})['Item']
        self.assertEqual(expected_item, inserted_item)

    def test_lambda_handler_update_with_no_attributes(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'update': True,
                        'attributes': [
                        ]
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': 'At least one attribute must be provided for server schema if allowing update rights.',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_attribute_not_found(self):
        import lambda_policy
        event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'policy_name': 'test_policy',
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'attributes': [
                            {
                                'attr_name': 'server_id_NOT_FOUND'
                            }
                        ]
                    }
                ]
            })
        }
        response = lambda_policy.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_policy.default_http_headers,
            'body': 'The following attributes: server : server_id_NOT_FOUND are not defined in schema.',
            'statusCode': 400
        }
        self.assertEqual(expected, response)

    def test_get_next_id(self):
        import lambda_policy
        ids = [1, 2, 3]
        next_id = lambda_policy.get_next_id(ids)
        self.assertEqual(4, next_id)

        ids = [1, 3]
        next_id = lambda_policy.get_next_id(ids)
        self.assertEqual(2, next_id)

        ids = [-2, -1]
        next_id = lambda_policy.get_next_id(ids)
        self.assertEqual(1, next_id)



