#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from unittest import mock
from unittest.mock import patch, ANY

import boto3
from moto import mock_aws

import test_common_utils
from test_common_utils import LambdaContextLogStream, RequestsResponse, SerializedDictMatcher, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'SchemaDynamoDBTable': 'test_schema_table'
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaReplatformEc2SchemaTest(unittest.TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        import lambda_replatformec2schema
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_schemas(self.ddb_client, lambda_replatformec2schema.SCHEMA_TABLE)
        self.schema_table = boto3.resource('dynamodb').Table(lambda_replatformec2schema.SCHEMA_TABLE)
        self.lambda_context = LambdaContextLogStream('testing')
        self.event_create = {
            'RequestType': 'Create',
            'StackId': 'testStackId',
            'RequestId': 'testRequestId',
            'LogicalResourceId': 'testLogicalResourceId',
            'ResponseURL': 'http://example.com'
        }
        self.event_delete = {
            'RequestType': 'Delete',
            'StackId': 'testStackId',
            'RequestId': 'testRequestId',
            'LogicalResourceId': 'testLogicalResourceId',
            'ResponseURL': 'http://example.com'
        }
        self.event_update = {
            'RequestType': 'Update',
            'StackId': 'testStackId',
            'RequestId': 'testRequestId',
            'LogicalResourceId': 'testLogicalResourceId',
            'ResponseURL': 'http://example.com'
        }
        self.event_unexpected = {
            'RequestType': 'UnExpected',
            'StackId': 'testStackId',
            'RequestId': 'testRequestId',
            'LogicalResourceId': 'testLogicalResourceId',
            'ResponseURL': 'http://example.com'
        }

    def assert_schemas_create(self):
        response = self.schema_table.get_item(Key={'schema_name': 'server'})
        with open(os.path.dirname(os.path.realpath(__file__)) +
                  '/sample_data/schema_server_replatform_create_server.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])
        response = self.schema_table.get_item(Key={'schema_name': 'EC2'})
        with open(os.path.dirname(os.path.realpath(__file__)) +
                  '/sample_data/schema_server_replatform_create_ec2.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])

    def assert_schemas_delete(self):
        response = self.schema_table.get_item(Key={'schema_name': 'server'})
        with open(os.path.dirname(os.path.realpath(__file__)) + '/sample_data/schema_server_replatform_delete_server.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])
        response = self.schema_table.get_item(Key={'schema_name': 'EC2'})
        self.assertFalse('Item' in response)

    def assert_schemas_unchanged(self):
        response = self.schema_table.get_item(Key={'schema_name': 'server'})
        print(response['Item'])
        with open(os.path.dirname(os.path.realpath(__file__)) +
                  '/sample_data/schema_server_replatform_update_server.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])
        response = self.schema_table.get_item(Key={'schema_name': 'EC2'})
        self.assertFalse('Item' in response)

    def assert_schemas_create_with_attrs(self):
        response = self.schema_table.get_item(Key={'schema_name': 'server'})
        print(response['Item'])
        with open(os.path.dirname(os.path.realpath(__file__)) +
                  '/sample_data/schema_server_replatform_create_server_attrs.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])
        response = self.schema_table.get_item(Key={'schema_name': 'EC2'})
        with open(os.path.dirname(os.path.realpath(__file__)) +
                  '/sample_data/schema_server_replatform_create_ec2.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])

    def assert_schemas_delete_with_attrs(self):
        response = self.schema_table.get_item(Key={'schema_name': 'server'})
        print(response['Item'])
        with open(os.path.dirname(os.path.realpath(__file__)) +
                  '/sample_data/schema_server_replatform_delete_server_attrs.json') as json_file:
            server_schema = json.load(json_file)
        self.assertEqual(server_schema, response['Item'])
        response = self.schema_table.get_item(Key={'schema_name': 'EC2'})
        self.assertFalse('Item' in response)

    def call_lambda_and_assert_success(self, mock_requests, lambda_replatformec2schema, event):
        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_replatformec2schema.lambda_handler(event, self.lambda_context)
        mock_requests.put.assert_called_once_with(event['ResponseURL'],
                                                  data=SerializedDictMatcher('Status', 'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)
        expected = {
            'Response': 'SUCCESS'
        }
        self.assertEqual(expected, response)

    def call_lambda_and_assert_failed(self, mock_requests, lambda_replatformec2schema, event):
        mock_requests.put.side_effect = Exception('test exception')
        response = lambda_replatformec2schema.lambda_handler(event, self.lambda_context)
        mock_requests.put.assert_called_once_with(event['ResponseURL'],
                                                  data=SerializedDictMatcher('Status', 'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)
        expected = {
            'Response': 'FAILED'
        }
        self.assertEqual(expected, response)

    def insert_ec2_schema(self, lambda_replatformec2schema):
        for item in lambda_replatformec2schema.factory.schema:
            self.ddb_client.put_item(
                TableName=lambda_replatformec2schema.SCHEMA_TABLE,
                Item=item
            )

    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_create_success(self, mock_requests):
        import lambda_replatformec2schema
        self.call_lambda_and_assert_success(mock_requests, lambda_replatformec2schema, self.event_create)
        self.assert_schemas_create()

    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_create_requests_exception(self, mock_requests):
        import lambda_replatformec2schema
        self.call_lambda_and_assert_failed(mock_requests, lambda_replatformec2schema, self.event_create)
        self.assert_schemas_create()

    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_delete_success(self, mock_requests):
        import lambda_replatformec2schema
        self.insert_ec2_schema(lambda_replatformec2schema)
        self.call_lambda_and_assert_success(mock_requests, lambda_replatformec2schema, self.event_delete)
        self.assert_schemas_delete()

    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_delete_requests_exception(self, mock_requests):
        import lambda_replatformec2schema
        self.insert_ec2_schema(lambda_replatformec2schema)
        self.call_lambda_and_assert_failed(mock_requests, lambda_replatformec2schema, self.event_delete)
        self.assert_schemas_delete()


    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_update_success(self, mock_requests):
        import lambda_replatformec2schema
        self.call_lambda_and_assert_success(mock_requests, lambda_replatformec2schema, self.event_update)
        self.assert_schemas_unchanged()


    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_unexpected_success(self, mock_requests):
        import lambda_replatformec2schema
        self.call_lambda_and_assert_success(mock_requests, lambda_replatformec2schema, self.event_unexpected)
        self.assert_schemas_unchanged()

    @patch('lambda_replatformec2schema.requests')
    @patch('lambda_replatformec2schema.load_schema')
    def test_lambda_handler_exception(self, mock_load_schema, mock_requests):
        import lambda_replatformec2schema
        mock_load_schema.side_effect = Exception('test exception')
        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_replatformec2schema.lambda_handler(self.event_create, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status', 'FAILED'),
                                                  headers=ANY,
                                                  timeout=ANY)
        expected = {
            'Response': 'SUCCESS'
        }
        self.assertEqual(expected, response)
        self.assert_schemas_unchanged()

    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_create_attrs_success(self, mock_requests):
        import lambda_replatformec2schema
        # delete table and repopulate with data that has attributes
        test_common_utils.delete_table(self.ddb_client, lambda_replatformec2schema.SCHEMA_TABLE)
        test_common_utils.create_and_populate_schemas(self.ddb_client, lambda_replatformec2schema.SCHEMA_TABLE,
                                                 'schemas_server_replatform_with_attrs.json')
        self.call_lambda_and_assert_success(mock_requests, lambda_replatformec2schema, self.event_create)
        self.assert_schemas_create_with_attrs()

    @patch('lambda_replatformec2schema.requests')
    def test_lambda_handler_delete_attrs_success(self, mock_requests):
        import lambda_replatformec2schema
        # delete table and repopulate with data that has attributes
        test_common_utils.delete_table(self.ddb_client, lambda_replatformec2schema.SCHEMA_TABLE)
        test_common_utils.create_and_populate_schemas(self.ddb_client, lambda_replatformec2schema.SCHEMA_TABLE,
                                                 'schemas_server_replatform_with_attrs.json')
        self.insert_ec2_schema(lambda_replatformec2schema)
        self.call_lambda_and_assert_success(mock_requests, lambda_replatformec2schema, self.event_delete)
        self.assert_schemas_delete_with_attrs()



