#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda_functions'))

import json
from time import sleep
from unittest import mock

from moto import mock_aws
from test_lambda_item_common import LambdaItemCommonTest, mock_item_check_valid_item_create_valid, \
    mock_item_check_valid_item_create_in_valid
from test_common_utils import logger, default_mock_os_environ as mock_os_environ, \
    mock_get_mf_auth_policy_allow, mock_get_mf_auth_policy_default_deny, mock_get_mf_auth_policy_allow_no_user


def mock_scan_dynamodb_data_table(table):
    return table.scan(Limit=5)['Items']


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaItemsTest(LambdaItemCommonTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        super().setUp()
        self.init_event_objects()
    
    def tearDown(self) -> None:
        # Reset any module-level state
        import sys
        if 'lambda_items' in sys.modules:
            del sys.modules['lambda_items']
        if 'shared.items.common' in sys.modules:
            del sys.modules['shared.items.common']
        super().tearDown()

    def init_event_objects(self):
        self.event_no_schema_provided = {
            'pathParameters': {}
        }

        self.event_get = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'app',
            }
        }
        
        self.event_post_id = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps({
                'app_name': 'App Number 3',
                'new_attr': 123,
                'description': '',
                'tags': ['']
            })
        }
        
        self.event_post_invalid_body = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': 'INVALID JSON'
        }
        
        self.event_post_no_app_name = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps({
                'new_attr': 'new test attribute',
                'description': '',
                'tags': ['']
            })
        }
        
        self.event_post_app_name_exists = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps({
                'app_name': 'Wordpress',
                'new_attr': 'new test attribute',
                'description': '',
                'tags': ['']
            })
        }
        
        # IAM request events
        self.event_iam_post_valid = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'requestContext': {
                'identity': {
                    'userArn': 'arn:aws:iam::123456789012:user/test-user'
                }
            },
            'body': json.dumps({
                'auth_info': {
                    'claims': {
                        'sub': 'user123',
                        'email': 'testuser@example.com',
                        'cognito:groups': 'admin,users',
                        'cognito:username': 'testuser'
                    }
                },
                'data': [
                    {'app_name': 'IAM App 1', 'description': 'Test app 1'},
                    {'app_name': 'IAM App 2', 'description': 'Test app 2'}
                ]
            })
        }
        
        self.event_cognito_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123',
                        'email': 'testuser@example.com',
                        'cognito:groups': 'admin,users',
                        'cognito:username': 'testuser'
                    }
                }
            },
            'body': json.dumps({
                'app_name': 'Cognito App',
                'description': 'Test cognito app'
            })
        }

    def assert_put_success(self, lambda_items, event, len_history=2):
        response = lambda_items.lambda_handler(event, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        self.assertTrue('errors' not in response)
        new_item_response = json.loads(response['body'])['newItems'][0]
        updated_item_db = self.apps_table.get_item(Key={'app_id': new_item_response["app_id"]})['Item']
        self.assertEqual(new_item_response, updated_item_db)
        self.assertEqual('App Number 3', updated_item_db['app_name'])
        self.assertEqual(123, updated_item_db['new_attr'])
        self.assertEqual('', updated_item_db['description'])
        self.assertEqual([''], updated_item_db['tags'])
        self.assertEqual(len_history, len(updated_item_db['_history'].keys()))
        return response

    def assert_no_new_items_added(self):
        self.assertEqual(2, len(self.apps_table.scan(Limit=5)['Items']))

    def test_lambda_handler_schema_no_exist(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_schema_no_exist, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Invalid schema provided :NO_EXIST', response["body"])
        self.assert_no_new_items_added()

    def test_lambda_handler_no_schema_provided(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_no_schema_provided, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('No schema provided to function.', response['body'])
        self.assert_no_new_items_added()

    def test_lambda_handler_get_success(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_get, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        items = json.loads(response['body'])
        self.assertEqual(2, len(items))
        self.assertEqual(['OFBiz', 'Wordpress'], [item['app_name'] for item in items])
        self.assert_no_new_items_added()

    @mock.patch('shared.items.common.get_auth_response_for_creation',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_post_not_authorized(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_id, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual({'errors': [{'action': 'deny', 'cause': 'Request is not Authenticated'}]},
                         json.loads(response['body']))
        self.assert_no_new_items_added()

    @mock.patch('shared.items.common.get_auth_response_for_creation',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_invalid_body(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_invalid_body, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('{"errors": ["malformed json input"]}', response['body'])
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_items.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('shared.items.common.get_auth_response_for_creation',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_success(self):
        import lambda_items
        self.assert_put_success(lambda_items, self.event_post_id, 2)

    @mock.patch('shared.items.common.get_auth_response_for_creation',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_no_app_name(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_no_app_name, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('attribute app_name is required', response['body'])
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_items.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('shared.items.common.get_auth_response_for_creation',
                new=mock_get_mf_auth_policy_allow_no_user)
    def test_lambda_handler_put_app_name_exists(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_app_name_exists, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        body = json.loads(response['body'])
        self.assertEqual([], body['newItems'])
        self.assertEqual({"existing_name": ["Wordpress"]}, body['errors'])
        self.assert_no_new_items_added()

    # IAM Request Tests
    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_items.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.item_validation.does_item_with_name_exist', return_value=False)
    def test_lambda_handler_iam_post_success(self, mock_name_exists, mock_mfauth):
        mock_mfauth.return_value.get_user_resource_creation_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_items
        response = lambda_items.lambda_handler(self.event_iam_post_valid, None)
        
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        
        body = json.loads(response['body'])
        self.assertIn('newItems', body)
        self.assertEqual(2, len(body['newItems']))
        
        # Verify items were created with correct user attribution
        for item in body['newItems']:
            self.assertEqual('testuser@example.com', item['_history']['createdBy'])
            self.assertIn(item['app_name'], ['IAM App 1', 'IAM App 2'])

    def test_lambda_handler_iam_post_missing_auth_info(self):
        """Test IAM POST request when auth_info is missing from body"""
        import lambda_items
        
        event_missing_auth = {
            'httpMethod': 'POST',
            'pathParameters': {'schema': 'app'},
            'requestContext': {
                'identity': {
                    'userArn': 'arn:aws:iam::123456789012:user/test-user'
                }
            },
            'body': json.dumps({
                'data': [{'app_name': 'IAM App 1'}]
            })
        }
        
        response = lambda_items.lambda_handler(event_missing_auth, None)
        
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        
        body = json.loads(response['body'])
        self.assertIn('errors', body)

    @mock.patch('shared.items.common.MFAuth')
    @mock.patch('shared.items.common.get_auth_response_for_creation',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_items.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    def test_lambda_handler_cognito_vs_iam_detection(self, mock_mfauth):
        mock_mfauth.return_value.get_user_resource_creation_policy.return_value = {'action': 'allow', 'user': 'testuser@example.com'}
        import lambda_items
        
        # Test Cognito request (has authorizer)
        cognito_response = lambda_items.lambda_handler(self.event_cognito_post, None)
        self.assertEqual(lambda_items.default_http_headers, cognito_response['headers'])
        print(cognito_response)
        self.assertTrue('statusCode' not in cognito_response)  # Success response
        
        cognito_body = json.loads(cognito_response['body'])
        self.assertIn('newItems', cognito_body)  # Standard Cognito response format
        
        # Test IAM request (no authorizer)
        iam_response = lambda_items.lambda_handler(self.event_iam_post_valid, None)
        self.assertEqual(lambda_items.default_http_headers, iam_response['headers'])
        self.assertTrue('statusCode' not in iam_response)
        
        iam_body = json.loads(iam_response['body'])
        self.assertIn('newItems', iam_body)  # IAM response format

    # Test lambda_items specific functions
    @mock.patch('lambda_items.generate_next_numeric_id', return_value=5)
    def test_set_system_attributes_for_new_item_number_key(self, mock_get_id):
        import lambda_items
        item = {'app_name': 'TestApp'}
        schema = {'attributes': [{'name': 'status', 'default': 'active'}]}
        new_audit = {'createdBy': 'user1'}
        
        lambda_items.set_system_attributes_for_new_item(
            self.apps_table, item, schema, 'app', 'number', new_audit
        )
        
        self.assertEqual('5', item['app_id'])
        self.assertEqual('active', item['status'])
        self.assertEqual(new_audit, item['_history'])

    def test_set_system_attributes_for_new_item_server_app_id_only(self):
        import lambda_items
        item = {'server_name': 'TestServer', 'app_ids': ['app1']}
        schema = {}
        new_audit = {}
        
        with mock.patch('lambda_items.generate_next_numeric_id', return_value=1):
            lambda_items.set_system_attributes_for_new_item(
                self.servers_table, item, schema, 'server', 'number', new_audit
            )
        
        self.assertEqual(['app1'], item['app_ids'])

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_items.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.item_validation.does_item_with_name_exist', return_value=False)
    def test_sequential_numeric_id_batch_processing(self, mock_name_exists):
        import lambda_items
        
        # Mock the database to return existing items with IDs 1, 2, 3
        # So the next available ID should be 4
        with mock.patch('lambda_items.generate_next_numeric_id', return_value=4) as mock_gen_id:
            
            # Create test data - 3 items that should get IDs 4, 5, 6
            test_items = [
                {'app_name': 'BatchApp1', 'description': 'First app in batch'},
                {'app_name': 'BatchApp2', 'description': 'Second app in batch'},
                {'app_name': 'BatchApp3', 'description': 'Third app in batch'}
            ]
            
            schema = {'schema_type': 'user', 'key_type': 'number'}
            new_audit = {'createdBy': 'test-user', 'createdTimestamp': '2024-01-01T00:00:00Z'}
            
            # Process the batch
            name_list, duplicates, existing, validation_errors, validated_items = \
                lambda_items.process_and_validate_item_batch(
                    test_items, 'app', schema, 'number', self.apps_table, new_audit
                )
            
            # Verify generate_next_numeric_id was called only once
            mock_gen_id.assert_called_once_with(self.apps_table, 'app')
            
            # Verify no validation errors occurred
            self.assertEqual([], duplicates, "Should have no duplicate names")
            self.assertEqual([], existing, "Should have no existing names")
            self.assertEqual([], validation_errors, "Should have no validation errors")
            
            # Verify all items were validated successfully
            self.assertEqual(3, len(validated_items), "All 3 items should be validated")
            
            # Verify each item got a unique sequential ID
            expected_ids = ['4', '5', '6']
            actual_ids = [item['app_id'] for item in validated_items]
            
            self.assertEqual(expected_ids, actual_ids, 
                           f"Items should get sequential IDs {expected_ids}, but got {actual_ids}")
            
            # Verify each item has the correct attributes
            for i, item in enumerate(validated_items):
                expected_name = f'BatchApp{i+1}'
                self.assertEqual(expected_name, item['app_name'])
                self.assertEqual(expected_ids[i], item['app_id'], 
                               f'app_id should be {expected_ids[i]} but got {item["app_id"]}')
                self.assertEqual(new_audit, item['_history'])

    def test_numeric_id_single_item_processing(self):
        import lambda_items
        
        with mock.patch('lambda_items.generate_next_numeric_id', return_value=10) as mock_gen_id:
            item = {'app_name': 'SingleApp', 'description': 'Single app'}
            schema = {'schema_type': 'user'}
            new_audit = {'createdBy': 'test-user'}
            
            # Set system attributes for single item
            next_id = lambda_items.set_system_attributes_for_new_item(
                self.apps_table, item, schema, 'app', 'number', new_audit
            )
            
            # Verify the item got the correct ID
            self.assertEqual('10', item['app_id'])
            self.assertEqual(new_audit, item['_history'])
            
            # For single item, next_id should be None since we didn't pass one in
            self.assertIsNone(next_id)
