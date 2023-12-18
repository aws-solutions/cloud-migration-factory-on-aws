#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import boto3
import json
import os
from unittest import TestCase, mock
from moto import mock_dynamodb

from test_common_utils import logger

default_http_headers = {
    'Access-Control-Allow-Origin': '*',
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


@mock.patch('lambda_items.MFAuth')
def mock_getUserResourceCreationPolicy():
    return {'action': 'allow'}


@mock.patch('lambda_items.MFAuth')
def mock_getUserAttributePolicy():
    return {'action': 'allow'}


@mock.patch('lambda_items.item_validation')
def mock_item_validation():
    return {'action': 'allow'}


# Setting the default AWS region environment variable required by the Python SDK boto3
@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region': 'us-east-1', 'application': 'cmf',
                              'environment': 'unittest'})
@mock_dynamodb
class LambdaSchemaTest(TestCase):
    def setUp(self):
        # Setup dynamoDB tables and put items required for test cases
        boto3.setup_default_session()
        self.schema_table_name = '{}-{}-'.format('cmf', 'unittest') + 'schema'
        # Creating schema table and creating schema item to test out schema types
        self.schema_client = boto3.client("dynamodb", region_name='us-east-1')
        self.schema_client.create_table(
            TableName=self.schema_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "schema_name", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "schema_name", "AttributeType": "S"},
            ],
        )
        self.schema_client.put_item(
            TableName=self.schema_table_name,
            Item={'schema_name': {'S': 'app'}, 'schema_type': {'S': 'user'}, 'attributes': {
                'L': [{'M': {'name': {'S': 'app_id'}, 'type': {'S': 'string'}}},
                      {'M': {'name': {'S': 'app_name'}, 'type': {'S': 'string'}}}]}})

    def tearDown(self):
        """
        Delete database resource and mock table
        """
        print("Tearing down")
        self.schema_client.delete_table(TableName=self.schema_table_name)
        self.dynamodb = None
        print("Teardown complete")

    def test_lambda_handler_get_schemas_metadata(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'GET', "pathParameters": None}
        logger.info("Testing lambda_schema GET schema metadata")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'body': '[{"schema_name": "app", "schema_type": '
                                                                          '"user"}]'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_put_without_schema(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": None}
        logger.info("Testing lambda_schema PUT without providing schema")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers},
                             'statusCode': 400, 'body': 'schema name not provided.'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_get_schema(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'GET', "pathParameters": {"schema_name": 'application'}}
        logger.info("Testing lambda_schema GET schema")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers},
                             'body': '{"schema_name": "app", "schema_type": "user", "attributes": '
                                     '[{"name": "app_id", "type": "string"}, {"name": "app_name", '
                                     '"type": "string"}]}'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_get_schema_non_existing(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'GET', "pathParameters": {"schema_name": 'bob'}}
        logger.info("Testing lambda_schema GET schema that does not exist")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers},
                             'body': '[]'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_post_schema(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'POST', "pathParameters": {"schema_name": 'bob'},
                      "body": '{"schema_name": "bob", "attributes": []}'}
        logger.info("Testing lambda_schema post schema new attribute")
        print(self.event)
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers},
                             'body': '[]'}
        self.assertEqual(data['statusCode'], 200)

    def test_lambda_handler_post_schema(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'POST', "pathParameters": {"schema_name": 'bob'},
                      "body": '{"schema_name": "bob", "attributes": []}'}
        logger.info("Testing lambda_schema post new schema")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result['statusCode'], 200)

    def test_lambda_handler_post_schema_duplicate(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'POST', "pathParameters": {"schema_name": 'bob'},
                      "body": '{"schema_name": "bob", "attributes": []}'}
        logger.info("Testing lambda_schema post new schema duplicate name")
        lambda_schema.lambda_handler.data_table = None
        # Create first schema record.
        result_create = lambda_schema.lambda_handler(self.event, '')
        # Create duplicate schema record.
        result = lambda_schema.lambda_handler(self.event, '')
        expected_response = {'headers': {**default_http_headers},
                             'statusCode': 400, 'body': 'bob schema already exists.'}
        self.assertEqual(result, expected_response)

    def test_lambda_handler_delete_schema(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'DELETE', "pathParameters": {"schema_name": 'bob'}}
        logger.info("Testing lambda_schema DELETE schema")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result['statusCode'], 200)

    def test_lambda_handler_put_schema_update_attributes(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'bob'},
                      "body": '{"schema_name": "application", "update_schema": {"friendly_name": "Apps", '
                              '"help_content": "Test content", "attributes": []}}'}
        logger.info("Testing lambda_schema put updated schema friendly name and help content")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        result_body = json.loads(result['body'])
        print("Result data: ", result)
        self.assertEqual(result_body['Attributes']['friendly_name'] +
                         result_body['Attributes']['help_content'],
                         "Apps" + "Test content")

    def test_lambda_handler_put_schema_no_updates_attributes(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'bob'},
                      "body": '{"schema_name": "application", "update_schema": {}}'}
        logger.info("Testing lambda_schema put updated schema no updates")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result, {'headers': {**default_http_headers},
                                  'body': 'No updates provided.'})

    def test_lambda_handler_put_schema_update_attributes_items(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"schema_name": "application", "update_schema": {"friendly_name": "Apps", '
                              '"help_content": "Test content", "attributes": []}}'}
        logger.info("Testing lambda_schema put updated schema friendly name and help content")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        result_body = json.loads(result['body'])
        print("Result data: ", result)
        self.assertEqual(result_body['Attributes']['friendly_name'] +
                         result_body['Attributes']['help_content'],
                         "Apps" + "Test content")

    def test_lambda_handler_put_schema_delete_attribute(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "DELETE", "name": "application"}'}
        logger.info("Testing lambda_schema put updated schema delete attribute")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        result_json = json.loads(result['body'])
        self.assertEqual(result_json['ResponseMetadata']['HTTPStatusCode'], 200)

    def test_lambda_handler_put_schema_add_attribute(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "POST", "new": {"name": "unittest_attrib", "type": "string", "description": "unit testing"}}'}
        logger.info("Testing lambda_schema put updated schema add new attribute")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        print(result)
        result_json = json.loads(result['body'])
        self.assertEqual(result_json['ResponseMetadata']['HTTPStatusCode'], 200)

    def test_lambda_handler_put_schema_update_attribute(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "PUT", "name": "unittest", "update": {"name": "unittest", "type": "string", "description": "unit testing"}}'}
        logger.info("Testing lambda_schema put updated schema update existing attribute")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        print(result)
        result_json = json.loads(result['body'])
        self.assertEqual(result_json['ResponseMetadata']['HTTPStatusCode'], 200)

    def test_lambda_handler_put_schema_update_attribute_no_type(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "PUT", "name": "unittest", "update": {"name": "unittest", "type": "", '
                              '"description": "unit testing"}}'}
        logger.info("Testing lambda_schema put updated schema update existing attribute no type")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result, {'headers': {**default_http_headers},
                                  'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"})

    def test_lambda_handler_put_schema_update_attribute_no_description(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "PUT", "name": "unittest", "update": {"name": "unittest", "type": "string", '
                              '"description": ""}}'}
        logger.info("Testing lambda_schema put updated schema update existing attribute no description")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result, {'headers': {**default_http_headers},
                                  'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"})

    def test_lambda_handler_put_schema_update_attribute_no_name(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "PUT", "name": "unittest", "update": {"name": "", "type": "string", '
                              '"description": "test description"}}'}
        logger.info("Testing lambda_schema put updated schema update existing attribute no name")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result, {'headers': {**default_http_headers},
                                  'statusCode': 400, 'body': "Attribute Name: 'Name' can not be empty"})

    def test_lambda_handler_put_schema_update_attribute_no_list(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "PUT", "name": "unittest", "update": {"name": "unittest", "type": "list", '
                              '"description": "test description", "listvalue": ""}}'}
        logger.info("Testing lambda_schema put updated schema update existing attribute no listvalues")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result, {'headers': {**default_http_headers},
                                  'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"})

    def test_lambda_handler_put_schema_update_attribute_no_list_missing(self):
        from lambda_functions.lambda_schema import lambda_schema

        self.event = {"httpMethod": 'PUT', "pathParameters": {"schema_name": 'application'},
                      "body": '{"event": "PUT", "name": "unittest", "update": {"name": "unittest", "type": "list", '
                              '"description": "test description"}}'}
        logger.info("Testing lambda_schema put updated schema update existing attribute no listvalues missing")
        lambda_schema.lambda_handler.data_table = None
        result = lambda_schema.lambda_handler(self.event, '')
        self.assertEqual(result, {'headers': {**default_http_headers},
                                  'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"})