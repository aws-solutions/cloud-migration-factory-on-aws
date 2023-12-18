#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
from time import sleep
from unittest import mock

from moto import mock_dynamodb, mock_s3
from test_lambda_item_common import LambdaItemCommonTest, mock_item_check_valid_item_create_valid, \
    mock_item_check_valid_item_create_in_valid
from test_common_utils import logger, default_mock_os_environ as mock_os_environ, \
    mock_get_mf_auth_policy_allow, mock_get_mf_auth_policy_default_deny, mock_get_mf_auth_policy_allow_no_user


def mock_scan_dynamodb_data_table(table):
    return table.scan(Limit=5)['Items']


def mock_scan_dynamodb_data_table_error(table):
    raise Exception('Simulated Error')


def mock_get_relationship_data(attribute_names, attributes):
    logger.debug(f'mock_get_relationship_data({attribute_names}, {attributes})')
    return []


@mock.patch.dict('os.environ', mock_os_environ)
@mock_s3
@mock_dynamodb
class LambdaItemsTest(LambdaItemCommonTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        super().setUp()
        self.init_event_objects()

    def init_event_objects(self):

        self.event_no_schema_provided = {
            'pathParameters': {
            }
        }

        self.event_get = {
            'httpMethod': 'GET',
            'pathParameters': {
                'schema': 'app',
            }
        }
        self.event_post = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps({
                'app_name': 'App Number 3',
                'new_attr': 'new test attribute',
                'description': '',
                'tags': ['']
            })
        }
        self.event_post_list = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps([{
                'app_name': 'App Number 3',
                'new_attr': 'new test attribute',
                'description': '',
                'tags': ['']
            }, {
                'app_name': 'App Number 4',
                'description': '',
                'tags': ['tag4']
            }
            ])
        }
        self.event_post_list_dup = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps([{
                'app_name': 'App Number 3',
                'new_attr': 'new test attribute',
                'description': '',
                'tags': ['']
            }, {
                'app_name': 'App Number 3',
                'description': '',
                'tags': ['tag4']
            }
            ])
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
        self.event_post_with_app_id = {
            'httpMethod': 'POST',
            'pathParameters': {
                'schema': 'app'
            },
            'body': json.dumps({
                'app_id': '10',
                'app_name': 'App Number 3',
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

    def assert_put_success(self, lambda_items, event, len_history=2):
        response = lambda_items.lambda_handler(event, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        self.assertTrue('errors' not in response)
        new_item_response = json.loads(response['body'])['newItems'][0]
        updated_item_db = self.apps_table.get_item(Key={'app_id': '3'})['Item']
        self.assertEqual(new_item_response, updated_item_db)
        self.assertEqual('App Number 3', updated_item_db['app_name'])
        self.assertEqual('new test attribute', updated_item_db['new_attr'])
        self.assertEqual('', updated_item_db['description'])
        self.assertTrue([''], updated_item_db['tags'])
        self.assertEqual(len_history, len(updated_item_db['_history'].keys()))
        return response

    def assert_no_new_items_added(self):
        self.assertEqual(2, len(self.apps_table.scan(Limit=5)['Items']))

    def test_lambda_handler_schema_no_exist(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_schema_no_exist, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Invalid schema provided :NO_EXIST', response['body'])
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
        print(items)
        self.assertEqual(2, len(items))
        self.assertEqual(['OFBiz', 'Wordpress'], [item['app_name'] for item in items])
        self.assert_no_new_items_added()

    @mock.patch('lambda_item.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_default_deny)
    def test_lambda_handler_post_not_authorized(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual({'errors': [{'action': 'deny', 'cause': 'Request is not Authenticated'}]},
                         json.loads(response['body']))
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_invalid_body(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_invalid_body, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual({'errors': ['malformed json input']},
                         json.loads(response['body']))
        self.assert_no_new_items_added()


    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_success(self):
        import lambda_items
        self.assert_put_success(lambda_items, self.event_post, 2)

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow_no_user)
    def test_lambda_handler_put_policy_success_no_user(self):
        import lambda_items
        self.assert_put_success(lambda_items, self.event_post, 0)

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_list(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_list, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        new_items_response = sorted(json.loads(response['body'])['newItems'], key=lambda item: item['app_id'])
        updated_item1_db = self.apps_table.get_item(Key={'app_id': '3'})['Item']
        updated_item2_db = self.apps_table.get_item(Key={'app_id': '4'})['Item']
        self.assertEqual(new_items_response, [updated_item1_db, updated_item2_db])
        self.assertEqual('App Number 3', updated_item1_db['app_name'])
        self.assertEqual('App Number 4', updated_item2_db['app_name'])
        self.assertEqual('new test attribute', updated_item1_db['new_attr'])
        self.assertTrue('new_attr' not in updated_item2_db)
        self.assertEqual('', updated_item1_db['description'])
        self.assertEqual('', updated_item2_db['description'])
        self.assertTrue([''], updated_item1_db['tags'])
        self.assertTrue(['tag4'], updated_item2_db['tags'])
        self.assertEqual(2, len(updated_item1_db['_history'].keys()))
        self.assertEqual(2, len(updated_item2_db['_history'].keys()))

    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_no_app_name(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_no_app_name, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('attribute app_name is required', response['body'])
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_with_app_id(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_with_app_id, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('You cannot create app_id, this is managed by the system', response['body'])
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
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

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_in_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_invalid_item_validation(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_app_name_exists, None)
        print(response)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        body = json.loads(response['body'])
        self.assertEqual([], body['newItems'])
        self.assertEqual({"validation_errors": [{
            "Wordpress": ["Simulated error, attribute x is required"]}],
            "existing_name": ["Wordpress"]},
            body['errors'])
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    def test_lambda_handler_put_list_dup(self):
        import lambda_items
        # the first item is inserted with success, response comes with an extra error attribute
        response = self.assert_put_success(lambda_items, self.event_post_list_dup)
        self.assertEqual({"duplicate_name": ["App Number 3"]}, json.loads(response['body'])['errors'])

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_items.sleep',
                new=lambda x: sleep(0))
    @mock.patch('lambda_items.client_ddb.batch_write_item')
    def test_lambda_handler_put_batch_write_2errors_then_success(self, mock_batch_write_item):
        import lambda_items
        mock_batch_write_item.side_effect = [
            {
                'UnprocessedItems': [{'PutRequest': {'Item': {'id': 'item1'}}}],
                'ResponseMetadata': {'HTTPStatusCode': 200}
            },
            {
                'UnprocessedItems': [{'PutRequest': {'Item': {'id': 'item1'}}}],
                'ResponseMetadata': {'HTTPStatusCode': 200}
            },
            {
                'UnprocessedItems': [],
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
        ]
        response = lambda_items.lambda_handler(self.event_post, None)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        new_item_response = json.loads(response['body'])['newItems'][0]
        self.assertEqual(new_item_response, new_item_response)
        self.assertEqual('App Number 3', new_item_response['app_name'])
        self.assertEqual('new test attribute', new_item_response['new_attr'])
        self.assertEqual('', new_item_response['description'])
        self.assertTrue([''], new_item_response['tags'])
        self.assertEqual(2, len(new_item_response['_history'].keys()))
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow)
    @mock.patch('lambda_items.sleep',
                new=lambda x: sleep(0))
    @mock.patch('lambda_items.client_ddb.batch_write_item')
    def test_lambda_handler_put_batch_write_http_status_500(self, mock_batch_write_item):
        import lambda_items
        mock_batch_write_item.side_effect = [
            {
                'UnprocessedItems': [{'PutRequest': {'Item': {'id': 'item1'}}}],
                'ResponseMetadata': {'HTTPStatusCode': 500}
            },
            {
                'UnprocessedItems': [{'PutRequest': {'Item': {'id': 'item1'}}}],
                'ResponseMetadata': {'HTTPStatusCode': 500}
            },
            {
                'UnprocessedItems': [],
                'ResponseMetadata': {'HTTPStatusCode': 500}
            }
        ]
        # even if you return 500, the loop doesn't exit unless UnprocessedItems is empty, so the code for list of
        # unprocessed items is never executed
        response = lambda_items.lambda_handler(self.event_post, None)
        print(response)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertTrue('statusCode' not in response)
        new_item_response = json.loads(response['body'])['newItems'][0]
        self.assertEqual(new_item_response, new_item_response)
        self.assertEqual('App Number 3', new_item_response['app_name'])
        self.assertEqual('new test attribute', new_item_response['new_attr'])
        self.assertEqual('', new_item_response['description'])
        self.assertTrue([''], new_item_response['tags'])
        self.assertEqual(2, len(new_item_response['_history'].keys()))
        self.assert_no_new_items_added()

    @mock.patch('lambda_items.item_validation.check_valid_item_create',
                new=mock_item_check_valid_item_create_valid)
    @mock.patch('lambda_item.item_validation.get_relationship_data',
                new=mock_get_relationship_data)
    @mock.patch('lambda_item.item_validation.scan_dynamodb_data_table',
                new=mock_scan_dynamodb_data_table_error)
    @mock.patch('lambda_items.MFAuth.get_user_resource_creation_policy',
                new=mock_get_mf_auth_policy_allow_no_user)
    def test_lambda_handler_put_unhandled_exception(self):
        import lambda_items
        response = lambda_items.lambda_handler(self.event_post_app_name_exists, None)
        print(response)
        self.assertEqual(lambda_items.default_http_headers, response['headers'])
        self.assertEqual(500, response['statusCode'])
        self.assertEqual({'errors': ['Unhandled API Exception: check logs for detailed error message.']},
                         json.loads(response['body']))
        self.assert_no_new_items_added()
