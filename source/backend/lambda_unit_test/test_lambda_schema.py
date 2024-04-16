#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from unittest import mock
from unittest.mock import ANY, patch

import boto3
from moto import mock_aws

import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ


@mock_aws
@mock.patch.dict('os.environ', mock_os_environ)
class LambdaSchemaTest(unittest.TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        self.ddb_client = boto3.client('dynamodb')
        self.schema_table_name = f'{os.environ["application"]}-{os.environ["environment"]}-schema'
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name)

    def test_get_schema_meta_data_success(self):
        import lambda_schema
        event_get = {
            "httpMethod": 'GET',
            "pathParameters": None
        }
        response_metadata = lambda_schema.lambda_handler(event_get, None)
        expected_metadata = [
            {'schema_name': 'server', 'schema_type': 'user'},
            {'schema_name': 'wave', 'schema_type': 'user'},
            {'schema_name': 'app', 'schema_type': 'user'},
            {'schema_name': 'automation', 'schema_type': 'automation'}
        ]
        expected_metadata.sort(key=lambda entry: entry['schema_name'])
        response_metadata = sorted(json.loads(response_metadata['body']), key=lambda entry: entry['schema_name'])
        self.assertEqual(expected_metadata, response_metadata)

    def test_non_get_with_no_schema(self):
        import lambda_schema
        event_get = {
            "httpMethod": 'POST',
            "pathParameters": None
        }
        response = lambda_schema.lambda_handler(event_get, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'schema name not provided.',
        }
        self.assertEqual(expected, response)

    def test_get_schema_app_success(self):
        import lambda_schema
        event_get = {
            "httpMethod": 'GET',
            "pathParameters": {
                'schema_name': 'application'
            }
        }
        response = lambda_schema.lambda_handler(event_get, None)
        expected_body = {
            'attributes': [
                {'name': 'app_id', 'type': 'string'},
                {'name': 'app_name', 'type': 'string'}
            ],
            'schema_name': 'app',
            'schema_type': 'user'
        }
        self.assertEqual(expected_body, json.loads(response['body']))

    def test_get_non_existing_schema(self):
        import lambda_schema
        event_get = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema_name': 'DONTEXIST'
            }
        }
        response = lambda_schema.lambda_handler(event_get, None)
        self.assertEqual([], json.loads(response['body']))

    def test_delete_schema_app_success(self):
        import lambda_schema
        event_delete = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'schema_name': 'application'
            }
        }
        response = lambda_schema.lambda_handler(event_delete, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        deleted_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'deleted-user',
            'schema_deleted': True,
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, deleted_schema)

    def test_delete_dont_exist(self):
        # TODO: this tests the current code as is, but the intent was to return 400
        import lambda_schema
        event_delete = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'schema_name': 'DONTEXIST'
            }
        }
        response = lambda_schema.lambda_handler(event_delete, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        deleted_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'DONTEXIST'})['Item']
        expected = {
            'schema_name': 'DONTEXIST',
            'schema_type': 'deleted-user',
            'schema_deleted': True,
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, deleted_schema)

    def test_post_success(self):
        import lambda_schema
        event_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema_name': 'test_schema'
            },
            'body': json.dumps({
                'schema_name': 'test_schema',
                'attributes': []
            })
        }
        response = lambda_schema.lambda_handler(event_post, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        added_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'test_schema'})['Item']
        expected = {
            'schema_name': 'test_schema',
            'schema_type': 'user',
            'lastModifiedTimestamp': ANY,
            'attributes': []
        }
        self.assertEqual(expected, added_schema)

    def test_post_already_existing(self):
        import lambda_schema
        event_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema_name': 'app'
            },
            'body': json.dumps({
                'schema_name': 'app',
                'attributes': []
            })
        }
        response = lambda_schema.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'app schema already exists.',
        }
        self.assertEqual(expected, response)

    def test_post_malformed(self):
        import lambda_schema
        event_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema_name': 'test_schema'
            },
            'body': 'malformed json'
        }
        response = lambda_schema.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'malformed json input',
        }
        self.assertEqual(expected, response)

    def test_post_no_schema_name(self):
        import lambda_schema
        event_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema_name': 'test_schema'
            },
            'body': json.dumps({
                'NO_schema_name': 'test_schema',
                'attributes': []
            })
        }
        response = lambda_schema.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'schema_name not provided.',
        }
        self.assertEqual(expected, response)

    def test_post_no_attributes(self):
        import lambda_schema
        event_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema_name': 'test_schema'
            },
            'body': json.dumps({
                'schema_name': 'test_schema',
                'NO_attributes': []
            })
        }
        response = lambda_schema.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'attributes not provided.',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_attributes_existing_item(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'schema_name': 'app',
                'update_schema': {
                    'friendly_name': 'Apps',
                    'help_content': 'Test content',
                    'attributes': []
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        response_attrs = json.loads(response['body'])['Attributes']
        expected = {
            'lastModifiedTimestamp': ANY,
            'friendly_name': 'Apps',
            'help_content': 'Test content'
        }
        self.assertEqual(expected, response_attrs)
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'friendly_name': 'Apps',
            'help_content': 'Test content',
            'lastModifiedTimestamp': ANY,
            'attributes': [
                {'name': 'app_id', 'type': 'string'},
                {'name': 'app_name', 'type': 'string'}
            ]
        }
        self.assertEqual(expected, updated_schema)

    @patch('lambda_schema.schema_table.update_item')
    def test_put_schema_update_attributes_update_item_exception(self, mock_update_item):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'schema_name': 'app',
                'update_schema': {
                    'friendly_name': 'Apps',
                    'help_content': 'Test content',
                    'attributes': []
                }
            })
        }
        mock_update_item.side_effect = Exception('test exception')
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'test exception',
        }
        self.assertEqual(expected, response)

    @patch('lambda_schema.schema_table.update_item')
    def test_put_schema_update_attributes_update_item_fail(self, mock_update_item):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'schema_name': 'app',
                'update_schema': {
                    'friendly_name': 'Apps',
                    'help_content': 'Test content',
                    'attributes': []
                }
            })
        }
        mock_update_item.return_value = {}
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Error updating schema.',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_attributes_existing_item_no_friendly_name(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'schema_name': 'app',
                'update_schema': {
                    'friendly_name': '',
                    'help_content': 'Test content',
                    'attributes': []
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        response_attrs = json.loads(response['body'])['Attributes']
        expected = {
            'lastModifiedTimestamp': ANY,
            'help_content': 'Test content'
        }
        self.assertEqual(expected, response_attrs)
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'help_content': 'Test content',
            'lastModifiedTimestamp': ANY,
            'attributes': [
                {'name': 'app_id', 'type': 'string'},
                {'name': 'app_name', 'type': 'string'}
            ]
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_update_attributes_new_item(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'test_item'},
            'body': json.dumps({
                'schema_name': 'app',
                'update_schema': {
                    'friendly_name': 'Apps',
                    'help_content': 'Test content',
                    'attributes': []
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        response_attrs = json.loads(response['body'])['Attributes']
        expected = {
            'lastModifiedTimestamp': ANY,
            'friendly_name': 'Apps',
            'help_content': 'Test content',
            'schema_name': 'test_item'
        }
        self.assertEqual(expected, response_attrs)
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'test_item'})['Item']
        expected = {
            'schema_name': 'test_item',
            'friendly_name': 'Apps',
            'help_content': 'Test content',
            'lastModifiedTimestamp': ANY,
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_no_updates(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'schema_name': 'app',
                'update_schema': {}
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'body': 'No updates provided.',
        }
        self.assertEqual(expected, response)

    def test_put_schema_delete_attr(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'DELETE',
                'name': 'app_name'
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'attributes': [
                {'name': 'app_id', 'type': 'string'}
            ],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_delete_attr_no_name(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'DELETE',
                'NO_name': 'app_name'
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: name is required',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'name': 'app_name_updated',
                    'type': 'string',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'attributes': [
                {'name': 'app_id', 'type': 'string'},
                {'description': 'app name updated by unittest', 'name': 'app_name_updated', 'type': 'string'}
            ],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_update_existing_attr_not_matching_names(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name_not_matching',
                'update': {
                    'name': 'app_name',
                    'type': 'string',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Name: app_name already exist',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr_list(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'listvalue': ['value1', 'value2'],
                    'name': 'app_name_updated',
                    'type': 'list',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'attributes':  [
                {'name': 'app_id', 'type': 'string'},
                {
                    'description': 'app name updated by unittest',
                    'listvalue': ['value1', 'value2'],
                    'name': 'app_name_updated',
                    'type': 'list'
                }
            ],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_update_existing_attr_relationship(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'listvalue': ['value1', 'value2'],
                    'name': 'app_name_updated',
                    'type': 'relationship',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'attributes':  [
                {'name': 'app_id', 'type': 'string'},
                {
                    'description': 'app name updated by unittest',
                    'listvalue': ['value1', 'value2'],
                    'name': 'app_name_updated',
                    'type': 'relationship'
                }
            ],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_update_existing_attr_string_with_list_value(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'listvalue': ['value1', 'value2'],
                    'name': 'app_name_updated',
                    'type': 'string',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'attributes':  [
                {'name': 'app_id', 'type': 'string'},
                {
                    'description': 'app name updated by unittest',
                    'name': 'app_name_updated',
                    'type': 'string'
                }
            ],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_update_existing_attr_list_no_value(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'name': 'app_name_updated',
                    'type': 'list',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'List Value\' can not be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr_list_empty_value(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'listvalue': '',
                    'name': 'app_name_updated',
                    'type': 'list',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'List Value\' can not be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_new_attr(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'test_attr'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'test_attr',
                'update': {
                    'name': 'test_attr',
                    'type': 'string',
                    'description': 'test attr updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'test_attr'})['Item']
        expected = {
            'schema_name': 'test_attr',
            'schema_type': 'user',
            'attributes': [],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_update_existing_attr_no_type(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'name': 'app_name_updated',
                    'type': '',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Type\' cannot be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr_no_description(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'name': 'app_name_updated',
                    'type': 'string',
                    'description': ''
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Description\' cannot be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr_no_update(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: update is required',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr_no_name_in_body(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'update': {
                    'name': 'app_name_updated',
                    'type': 'string',
                    'description': ''
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: name is required',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_existing_attr_no_name(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'PUT',
                'name': 'app_name',
                'update': {
                    'name': '',
                    'type': 'string',
                    'description': 'app name updated by unittest'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Name\' can not be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'type': 'string',
                    'description': 'unit testing attribute'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(200, json.loads(response['body'])['ResponseMetadata']['HTTPStatusCode'])
        updated_schema = lambda_schema.schema_table.get_item(Key={'schema_name': 'app'})['Item']
        expected = {
            'schema_name': 'app',
            'schema_type': 'user',
            'attributes': [
                {'name': 'app_id', 'type': 'string'},
                {'name': 'app_name', 'type': 'string'},
                {'description': 'unit testing attribute', 'name': 'test_attr', 'type': 'string'}
            ],
            'lastModifiedTimestamp': ANY
        }
        self.assertEqual(expected, updated_schema)

    def test_put_schema_add_attr_no_new(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'NO_new': {
                    'name': 'test_attr',
                    'type': 'string',
                    'description': 'unit testing attribute'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: new is required',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_no_name_in_new(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'NO_name': 'test_attr',
                    'type': 'string',
                    'description': 'unit testing attribute'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: name is required',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_existing_name(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'app_name',
                    'type': 'string',
                    'description': 'unit testing attribute'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Name: app_name already exists',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_empty_name(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': '',
                    'type': 'string',
                    'description': 'unit testing attribute'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name can not be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_empty_description(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'type': 'string',
                    'description': ''
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Description\' cannot be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_no_description(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'type': 'string'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Description\' cannot be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_empty_type(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'type': '',
                    'description': 'some description'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Type\' cannot be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_no_type(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'description': 'some description'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'Type\' cannot be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_list_no_value(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'description': 'some description',
                    'type': 'list'
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'List Value\' can not be empty',
        }
        self.assertEqual(expected, response)

    def test_put_schema_add_attr_list_empty_value(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'event': 'POST',
                'new': {
                    'name': 'test_attr',
                    'description': 'some description',
                    'type': 'list',
                    'listvalue': ''
                }
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: \'List Value\' can not be empty',
        }
        self.assertEqual(expected, response)

    def test_put_malformed(self):
        import lambda_schema
        event_post = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': 'malformed json'
        }
        response = lambda_schema.lambda_handler(event_post, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'malformed json input',
        }
        self.assertEqual(expected, response)

    def test_put_schema_update_attributes_existing_item_sys_schema(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'app_id': '11'
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'You cannot create app_id schema, this is managed by the system',
        }
        self.assertEqual(expected, response)

    def test_put_no_event(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'PUT',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'NO_event': 'POST',
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        expected = {
            'headers': lambda_schema.default_http_headers,
            'statusCode': 400,
            'body': 'Attribute Name: event is required',
        }
        self.assertEqual(expected, response)

    def test_unhandled_http_method(self):
        import lambda_schema
        event_put = {
            'httpMethod': 'OPTION',
            'pathParameters': {'schema_name': 'app'},
            'body': json.dumps({
                'NO_event': 'POST',
            })
        }
        response = lambda_schema.lambda_handler(event_put, None)
        self.assertEqual(None, response)
