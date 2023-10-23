#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0




import unittest
import boto3
import logging
import os
from unittest import TestCase, mock
from moto import mock_dynamodb


# This is to get around the relative path import issue.
# Absolute paths are being used in this file after setting the root directory
import sys  
from pathlib import Path
file = Path(__file__).resolve()  
package_root_directory = file.parents [1]  
sys.path.append(str(package_root_directory))  
sys.path.append(str(package_root_directory)+'/lambda_layers/lambda_layer_policy/python/')
sys.path.append(str(package_root_directory)+'/lambda_layers/lambda_layer_items/python/')


# Set log level
loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)

default_http_headers = {
    'Access-Control-Allow-Origin': '*',
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


@mock.patch('lambda_item.MFAuth')
def mock_getUserResourceCreationPolicy():
    return {'action': 'allow'}

@mock.patch('lambda_item.MFAuth')
def mock_getUserAttributePolicy():
    return {'action': 'allow'}

@mock.patch('lambda_item.item_validation')
def mock_item_validation():
    return {'action': 'allow'}

# Setting the default AWS region environment variable required by the Python SDK boto3
@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1','region':'us-east-1', 'application': 'cmf', 'environment': 'unittest'})

@mock_dynamodb
class LambdaItemTestGet(TestCase):
    def setUp(self):
        # Setup dynamoDB tables and put items required for test cases
        self.table_name = '{}-{}-'.format('cmf', 'unittest') + 'apps'
        boto3.setup_default_session()
        self.event = {"httpMethod": 'GET', 'pathParameters': {'appid': '1', 'schema': 'app'}}
        self.table_name = '{}-{}-'.format('cmf', 'unittest') + 'apps'
        self.client = boto3.client("dynamodb",region_name='us-east-1')
        self.client.create_table(
            TableName='{}-{}-'.format('cmf', 'unittest') + 'apps',
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "app_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "app_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'app_id-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'app_id',
                                'KeyType': 'HASH'
                            },
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                    ]
        )
        self.client.put_item(
               TableName=self.table_name,
               Item={'app_id': {'S': '3'}, 'app_name': {'S': 'test app'}})
        self.schema_table_name = '{}-{}-'.format('cmf', 'unittest') + 'schema'
        # Creating schema table and creating schema item to test out schema types
        self.schema_client = boto3.client("dynamodb",region_name='us-east-1')
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
              Item={'schema_name': {'S': 'app'}, 'schema_type': {'S': 'user'},'attributes':{'L':[{'M': {'name': {'S': 'app_id'}, 'type': {'S' : 'string'}}},{'M': {'name': {'S': 'app_name'}, 'type': {'S' : 'string'}}}]}})

        self.role_table_name = '{}-{}-'.format('cmf', 'unittest') + 'roles'
        self.role_client = boto3.client("dynamodb",region_name='us-east-1')
        self.role_client.create_table(
            TableName=self.role_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "role_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "role_id", "AttributeType": "S"},
            ],
        )
        self.role_client.put_item(
              TableName=self.role_table_name,
              Item={'role_id': {'S': '1'}, 'role_name': {'S': 'FactoryAdmin'},'groups': {'L':[ { "M" : { "group_name" : { "S" : "admin" } } } ]}, 'policies':{"L" : [ { "M" : { "policy_id" : { "S" : "1" } } } ]}  })



        self.policy_table_name = '{}-{}-'.format('cmf', 'unittest') + 'policies'
        self.policy_client = boto3.client("dynamodb",region_name='us-east-1')
        self.policy_client.create_table(
            TableName=self.policy_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "policy_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "policy_id", "AttributeType": "S"},
            ],
        )
        self.policy_client.put_item(
              TableName=self.policy_table_name,
              Item={'policy_id': {'S': '1'}, 'policy_name': {'S': 'Administrator'}, \
                    'entity_access': {"L": [{"M": {"attributes": {"L": [{"M": {"attr_name": {"S": "app_id"},"attr_type": {"S": "application"}}}, \
                    {"M": {"attr_name": {"S": "app_name"},"attr_type": {"S": "application"}}}]}, \
                    "delete": {"BOOL": True },"update": {"BOOL": True },"create": {"BOOL": True },"read": {"BOOL": True },"schema_name": {"S": "application"}}}]}  })


    def tearDown(self):
        """
        Delete database resource and mock table
        """
        print("Tearing down")
        self.client.delete_table(TableName=self.table_name)
        self.policy_client.delete_table(TableName=self.policy_table_name)
        self.role_client.delete_table(TableName=self.role_table_name)
        self.schema_client.delete_table(TableName=self.schema_table_name)
        self.dynamodb = None
        print("Teardown complete")


    def test_lambda_handler_incorrect_id(self):
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item GET with incorrect app_id")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'body': '[]'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_correct_id(self):
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item GET with correct app_id")
        lambda_item.lambda_handler.data_table = None
        self.event = {"httpMethod": 'GET', 'pathParameters': {'appid': '3', 'schema': 'app'}}
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        print("Result data: ",data)
        expected_response = {'headers': {**default_http_headers}, 'body': '[{"app_id": "3", "app_name": "test app"}]'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_delete_app_id_unauthenticated_request(self):
        self.event = {"httpMethod": 'DELETE', 'pathParameters': {'id': '3', 'schema': 'app'}, 'requestContext': {'authorizer':{}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item DELETE by unauthenticated user")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'statusCode': 401, 'body': '{"errors": [{"action": "deny", "cause": "Request is not Authenticated"}]}'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_delete_app_id_user_not_in_group(self):
        self.event = {"httpMethod": 'DELETE', 'pathParameters': {'id': '3', 'schema': 'app'}, 'requestContext': {'authorizer':{'claims':{'cognito:username':'username','email':'username@example.com'}}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item DELETE by user not part of any group")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'statusCode': 401, 'body': '{"errors": [{"action": "deny", "cause": "User is not assigned to any group. Access denied."}]}'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_delete_correct_app_id(self):
        self.event = {"httpMethod": 'DELETE', 'pathParameters': {'id': '3', 'schema': 'app'}, 'requestContext': {'authorizer':{'claims':{'cognito:groups':'admin','cognito:username':'username','email':'username@example.com'}}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item DELETE with correct app_id")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers},'statusCode': 200, 'body': "Item was successfully deleted."}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_delete_wrong_app_id(self):
        self.event = {"httpMethod": 'DELETE', 'pathParameters': {'id': '1', 'schema': 'app'}, 'requestContext': {'authorizer':{'claims':{'cognito:groups':'admin','cognito:username':'username','email':'username@example.com'}}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item DELETE with wrong app_id")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'statusCode': 400, 'body': '{"errors": ["app Id: 1 does not exist"]}'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_put_unauthorized(self):
        self.event = {"httpMethod": 'PUT', 'pathParameters': {'id': '1', 'schema': 'app'}, 'requestContext': {'authorizer':{}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item PUT with unauthenticated user")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'statusCode': 401, 'body': '{"errors": [{"action": "deny", "cause": "Username not provided. Access denied."}]}'}
        print('Expected:', expected_response)
        self.assertEqual(data, expected_response)

    def test_lambda_handler_put_no_attribute(self):
        self.event = {"httpMethod": 'PUT', 'pathParameters': {'id': '1', 'schema': 'app'}, 'requestContext': {'authorizer':{'claims':{'cognito:groups':'admin','cognito:username':'username','email':'username@example.com'}}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item PUT with no attributes to PUT")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'statusCode': 401, 'body': '{"errors": [{"action": "deny", "cause": "There are no attributes to update"}]}'}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_put_system_attribute(self):
        self.event = {"httpMethod": 'PUT', 'pathParameters': {'id': '1', 'schema': 'app'},"body": "{\"app_name\":\"check\",\"app_id\":\"1\"}", 'requestContext': {'authorizer':{'claims':{'cognito:groups':'admin','cognito:username':'username','email':'username@example.com'}}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item PUT system managed attribute")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data = result
        #print("Result data: ", data)
        expected_response = {'headers': {**default_http_headers}, 'statusCode': 400, 'body': '{"errors": ["You cannot modify app_id, it is managed by the system"]}'}
        self.assertEqual(data, expected_response)


    def test_lambda_handler_put_no_attribute(self):
        self.event = {"httpMethod": 'PUT',"isBase64Encoded": False, 'pathParameters': {'id': '3', 'schema': 'app','schema_name':'app'},"body": "{\"app_name\":\"dummy\"}", 'requestContext': {'authorizer':{'claims':{'cognito:groups':'admin','cognito:username':'username','email':'username@example.com'}}}}
        from lambda_functions.lambda_item import lambda_item
        log.info("Testing lambda_app_item PUT attribute with authenticated user and valid attributes")
        lambda_item.lambda_handler.data_table = None
        result = lambda_item.lambda_handler(self.event,'')
        data=result.get('body')
        #print("Result data: ", data)
        expected_response = '"HTTPStatusCode": 200'
        self.assertIn(expected_response, data)