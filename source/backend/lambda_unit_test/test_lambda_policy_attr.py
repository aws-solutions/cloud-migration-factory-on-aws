#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import unittest
from unittest import mock

import boto3
from moto import mock_dynamodb

import test_common_utils


@mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
@mock_dynamodb
class LambdaPolicyAttrTest(unittest.TestCase):

    @mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
    def setUp(self) -> None:
        import lambda_policy_attr
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_policies(self.ddb_client, lambda_policy_attr.policies_table_name)
        test_common_utils.create_and_populate_schemas(self.ddb_client, lambda_policy_attr.schema_table_name)

    def test_lambda_handler_get_success(self):
        import lambda_policy_attr
        event_get = {
            'httpMethod': 'GET',
            'pathParameters': {
                'policy_id': '1'
            }
        }
        response = lambda_policy_attr.lambda_handler(event_get, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'body': '{"policy_id": "1", "policy_name": "Administrator"}',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_get_not_found(self):
        import lambda_policy_attr
        event_get = {
            'httpMethod': 'GET',
            'pathParameters': {
                'policy_id': '11'
            }
        }
        response = lambda_policy_attr.lambda_handler(event_get, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'body': 'policy Id: 11 does not exist',
            'statusCode': 400,
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_post_not_handled(self):
        import lambda_policy_attr
        event_post_no_body = {
            'httpMethod': 'POST'
        }
        response = lambda_policy_attr.lambda_handler(event_post_no_body, None)
        self.assertEqual(None, response)

    def test_lambda_handler_put_no_body(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            }
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'malformed json input',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_policy_id(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id_NONE': '1'
            }
        }
        self.assertRaises(Exception, lambda_policy_attr.lambda_handler, event, None)

    def test_lambda_handler_put_no_entry_access(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entry_access_None': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'The attribute entity_access is required',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_entry_policy_not_found(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '11'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server'
                    }
                ]
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'policy Id: 11 does not exist',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_flags_false(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server'
                    }
                ]
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        self.assertEqual(lambda_policy_attr.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_item = lambda_policy_attr.policies_table.get_item(Key={'policy_id': '1'})['Item']
        expected = {
            'policy_id': '1',
            'policy_name': 'Administrator',
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
        self.assertEqual(expected, updated_item)

    def test_lambda_handler_put_flags_true(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
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
        response = lambda_policy_attr.lambda_handler(event, None)
        self.assertEqual(lambda_policy_attr.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_item = lambda_policy_attr.policies_table.get_item(Key={'policy_id': '1'})['Item']
        expected = {
            'policy_id': '1',
            'policy_name': 'Administrator',
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
        self.assertEqual(expected, updated_item)

    def test_lambda_handler_put_schema_application(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'application'
                    }
                ]
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        self.assertEqual(lambda_policy_attr.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_item = lambda_policy_attr.policies_table.get_item(Key={'policy_id': '1'})['Item']
        expected = {
            'policy_id': '1',
            'policy_name': 'Administrator',
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
        self.assertEqual(expected, updated_item)

    def test_lambda_handler_put_schema_type_automation(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'automation',
                    }
                ]
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        self.assertEqual(lambda_policy_attr.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_item = lambda_policy_attr.policies_table.get_item(Key={'policy_id': '1'})['Item']
        expected = {
            'policy_id': '1',
            'policy_name': 'Administrator',
            'entity_access': [
                {
                    'schema_name': 'automation',
                    'create': False,
                }
            ]
        }
        self.assertEqual(expected, updated_item)

    def test_lambda_handler_put_matching_policy(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server'
                    }
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        self.assertEqual(lambda_policy_attr.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_item = lambda_policy_attr.policies_table.get_item(Key={'policy_id': '1'})['Item']
        expected = {
            'policy_id': '1',
            'policy_name': 'Administrator',
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
        self.assertEqual(expected, updated_item)

    def test_lambda_handler_put_not_matching_policy_id(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '2'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server'
                    }
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'policy_name: Administrator already exist',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_with_attributes(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'attributes': [
                            {
                                'attr_name': 'server_id'
                            }
                        ]
                    },
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        self.assertEqual(lambda_policy_attr.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_item = lambda_policy_attr.policies_table.get_item(Key={'policy_id': '1'})['Item']
        expected = {
            'policy_id': '1',
            'policy_name': 'Administrator',
            'entity_access': [
                {
                    'schema_name': 'server',
                    'attributes': [
                        {
                            'attr_name': 'server_id'
                        }
                    ],
                    'create': False,
                    'delete': False,
                    'update': False,
                    'read': False
                }
            ]
        }
        self.assertEqual(expected, updated_item)

    def test_lambda_handler_put_update_with_no_attributes(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'update': True,
                        'attributes': [
                        ]
                    }
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'At least one attribute must be provided for server schema if allowing update rights.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_attribute_not_found(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server',
                        'update': True,
                        'attributes': [
                            {
                                'attr_name': 'server_id_NOT_FOUND'
                            }
                        ]
                    }
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'The following attributes: server : server_id_NOT_FOUND are not defined in schema.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_schema_not_found(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name': 'server_NOT_THERE',
                    }
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'server_NOT_THERE not a valid schema.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_put_no_schema(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'policy_id': '1'
            },
            'body': json.dumps({
                'entity_access': [
                    {
                        'schema_name_NOT': 'server',
                    }
                ],
                'policy_name': 'Administrator'
            })
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'Schema name key not found.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_delete_default_policies(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'policy_id': '1'
            }
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'Default policies Administrator and ReadOnly cannot be deleted.',
        }
        self.assertEqual(expected, response)

        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'policy_id': '2'
            }
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'Default policies Administrator and ReadOnly cannot be deleted.',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_delete_success(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'policy_id': '3'
            }
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 200,
            'body': 'policy: 3 was successfully deleted',
        }
        self.assertEqual(expected, response)

    def test_lambda_handler_delete_non_existent(self):
        import lambda_policy_attr
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'policy_id': '4'
            }
        }
        response = lambda_policy_attr.lambda_handler(event, None)
        expected = {
            'headers': lambda_policy_attr.default_http_headers,
            'statusCode': 400,
            'body': 'policy Id: 4 does not exist',
        }
        self.assertEqual(expected, response)
