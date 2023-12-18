#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import sys
import unittest
from unittest import mock
from unittest.mock import patch, ANY
import json

import boto3
from moto import mock_dynamodb

import test_common_utils
from test_common_utils import LambdaContextLogStream, RequestsResponse, SerializedDictMatcher, logger, \
    default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    'RoleDynamoDBTable': 'RoleDynamoDBTable',
    'SchemaDynamoDBTable': 'SchemaDynamoDBTable',
    'PolicyDynamoDBTable': 'PolicyDynamoDBTable',
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_dynamodb
class LambdaDefaultSchemaTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # read the json files before mock_open_file
        # find the lambda_defaultschema directory in sys.path and reuse the json files there
        dir_lambda_defaultschema = [d for d in sys.path if d.endswith('lambda_defaultschema')][0]
        logger.debug(f'dir_lambda_defaultschema : {dir_lambda_defaultschema}')
        cls.json_schema_file = open(dir_lambda_defaultschema + '/default_schema.json')
        cls.json_policies_file = open(dir_lambda_defaultschema + '/default_policies.json')
        cls.json_roles_file = open(dir_lambda_defaultschema + '/default_roles.json')

        # save the builtin open
        cls.builtin_open = open

    # the class level decorator is not applied here ?
    @mock.patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_SECURITY_TOKEN': 'testing',
        'AWS_SESSION_TOKEN': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'RoleDynamoDBTable': 'RoleDynamoDBTable',
        'SchemaDynamoDBTable': 'SchemaDynamoDBTable',
        'PolicyDynamoDBTable': 'PolicyDynamoDBTable',
    })
    def setUp(self):
        self.test_url = 'http://www.example.com'
        self.table_role = os.getenv('RoleDynamoDBTable')
        self.table_schema = os.getenv('SchemaDynamoDBTable')
        self.table_policy = os.getenv('PolicyDynamoDBTable')

        dir_lambda_defaultschema = [d for d in sys.path if d.endswith('lambda_defaultschema')][0]
        with open(dir_lambda_defaultschema + '/default_schema.json') as json_schema_file:
            self.json_schema = json.load(json_schema_file)
        with open(dir_lambda_defaultschema + '/default_policies.json') as json_policies_file:
            self.json_policies = json.load(json_policies_file)
        with open(dir_lambda_defaultschema + '/default_roles.json') as json_roles:
            self.json_roles = json.load(json_roles)

        # create the dynamodb tables
        self.ddb_client = boto3.client('dynamodb')
        self.ddb_client.create_table(
            TableName=self.table_role,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "role_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "role_id", "AttributeType": "S"},
            ],
        )
        self.ddb_client.create_table(
            TableName=self.table_schema,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "schema_name", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "schema_name", "AttributeType": "S"},
            ],
        )
        self.ddb_client.create_table(
            TableName=self.table_policy,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "policy_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "policy_id", "AttributeType": "S"},
            ],
        )

        self.event_create = {
            'RequestType': 'Create',
            'StackId': 'StackABC',
            'RequestId': 'REQUESTABC',
            'LogicalResourceId': 'RESOURCEABC',
            'ResponseURL': self.test_url,
        }
        self.event_update = {
            'RequestType': 'Update',
            'StackId': 'StackABC',
            'RequestId': 'REQUESTABC',
            'LogicalResourceId': 'RESOURCEABC',
            'ResponseURL': self.test_url,
        }
        self.event_delete = {
            'RequestType': 'Delete',
            'StackId': 'StackABC',
            'RequestId': 'REQUESTABC',
            'LogicalResourceId': 'RESOURCEABC',
            'ResponseURL': self.test_url,
        }
        self.event_unknown = {
            'RequestType': 'Unknown',
            'StackId': 'StackABC',
            'RequestId': 'REQUESTABC',
            'LogicalResourceId': 'RESOURCEABC',
            'ResponseURL': self.test_url,
        }
        self.lambda_context = LambdaContextLogStream('testing')

    def mock_file_open(*args, **kwargs):
        logger.debug(f'mock_file_open : {args}, {kwargs}')
        file_name = args[0]
        # the schema json files are already read in setUpClass,
        logger.debug(f'file to open : {file_name}')
        if file_name == 'default_schema.json':
            return LambdaDefaultSchemaTest.json_schema_file
        elif file_name == 'default_policies.json':
            return LambdaDefaultSchemaTest.json_policies_file
        elif file_name == 'default_roles.json':
            return LambdaDefaultSchemaTest.json_roles_file
        else:
            return LambdaDefaultSchemaTest.builtin_open(*args, **kwargs)

    def assert_table_contents(self):
        paginator = self.ddb_client.get_paginator('scan')
        roles = []
        for page in paginator.paginate(TableName=self.table_role):
            roles.extend(page['Items'])
        self.assertEqual(len(self.json_roles), len(roles))
        schemas = []
        for page in paginator.paginate(TableName=self.table_schema):
            schemas.extend(page['Items'])
        self.assertEqual(len(self.json_schema), len(schemas))
        policies = []
        for page in paginator.paginate(TableName=self.table_policy):
            policies.extend(page['Items'])
        self.assertEqual(len(self.json_policies), len(policies))

    def assert_table_contents_empty(self):
        paginator = self.ddb_client.get_paginator('scan')
        roles = []
        for page in paginator.paginate(TableName=self.table_role):
            roles.extend(page['Items'])
        self.assertEqual(0, len(roles))
        schemas = []
        for page in paginator.paginate(TableName=self.table_schema):
            schemas.extend(page['Items'])
        self.assertEqual(0, len(schemas))
        policies = []
        for page in paginator.paginate(TableName=self.table_policy):
            policies.extend(page['Items'])
        self.assertEqual(0, len(policies))

    @patch('lambda_defaultschema.requests')
    @patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_create(self, mock_requests):
        import lambda_defaultschema

        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_defaultschema.lambda_handler(self.event_create, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status',
                                                                                                     'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)
        self.assertEqual({
            'Response': 'SUCCESS'
            }, response)
        self.assert_table_contents()

    @patch('lambda_defaultschema.requests')
    @patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_create_exception(self, mock_requests):
        import lambda_defaultschema

        mock_requests.put.side_effect = Exception('test exception')
        response = lambda_defaultschema.lambda_handler(self.event_create, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status',
                                                                                                     'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)
        self.assertEqual({
            'Response': 'FAILED'
            }, response)
        # the contents are saved to the tables even with an error
        self.assert_table_contents()

    @patch('lambda_defaultschema.requests')
    @patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_update(self, mock_requests):
        import lambda_defaultschema

        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_defaultschema.lambda_handler(self.event_update, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status',
                                                                                                     'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)

        self.assertDictEqual({
            'Response': 'SUCCESS'
            }, response)
        self.assert_table_contents_empty()

    @patch('lambda_defaultschema.requests')
    @patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_delete(self, mock_requests):
        import lambda_defaultschema

        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_defaultschema.lambda_handler(self.event_delete, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status',
                                                                                                     'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)
        self.assertEqual({
            'Response': 'SUCCESS'
            }, response)
        self.assert_table_contents_empty()

    @patch('lambda_defaultschema.requests')
    @patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_unknown(self, mock_requests):
        import lambda_defaultschema

        mock_requests.put.return_value = RequestsResponse(200)
        response = lambda_defaultschema.lambda_handler(self.event_unknown, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status',
                                                                                                     'SUCCESS'),
                                                  headers=ANY,
                                                  timeout=ANY)
        self.assertEqual({
            'Response': 'SUCCESS'
            }, response)
        self.assert_table_contents_empty()


    @patch('lambda_defaultschema.requests')
    @patch('builtins.open', new=mock_file_open)
    def test_lambda_handler_exception(self, mock_requests):
        import lambda_defaultschema


        mock_requests.put.return_value = RequestsResponse(200)
        # simulate error by setting the wrong table name for all tables so that the test still good if the order changes
        lambda_defaultschema.SCHEMA_TABLE = self.table_schema + '_FAIL'
        lambda_defaultschema.ROLE_TABLE = self.table_role + '_FAIL'
        lambda_defaultschema.POLICY_TABLE = self.table_policy + '_FAIL'
        response = lambda_defaultschema.lambda_handler(self.event_create, self.lambda_context)
        mock_requests.put.assert_called_once_with(self.event_create['ResponseURL'],
                                                  data=SerializedDictMatcher('Status',
                                                                                                     'FAILED'),
                                                  headers=ANY,
                                                  timeout=ANY)
        # the final response though is SUCCESS
        self.assertEqual({
            'Response': 'SUCCESS'
            }, response)
        self.assert_table_contents_empty()
