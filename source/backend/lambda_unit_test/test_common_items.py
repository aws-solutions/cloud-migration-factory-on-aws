#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda_functions'))

import json
from unittest import mock
from moto import mock_aws
from test_lambda_item_common import LambdaItemCommonTest
from test_common_utils import default_mock_os_environ as mock_os_environ


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class CommonItemsTest(LambdaItemCommonTest):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        super().setUp()

    def test_get_schema_info_no_schema_provided(self):
        from shared.items.common import get_schema_info
        event = {'pathParameters': {}}
        
        schema_name, schema, logging_context = get_schema_info(event)
        
        self.assertIsNone(schema_name)
        self.assertEqual(400, schema['statusCode'])
        self.assertEqual('No schema provided to function.', schema['body'])
        self.assertEqual('', logging_context)

    def test_get_schema_info_invalid_schema(self):
        from shared.items.common import get_schema_info
        event = {'pathParameters': {'schema': 'INVALID'}, 'httpMethod': 'GET'}
        
        schema_name, schema, logging_context = get_schema_info(event)
        
        self.assertEqual('INVALID', schema_name)
        self.assertEqual(400, schema['statusCode'])
        self.assertEqual('Invalid schema provided :INVALID', schema['body'])
        self.assertEqual('INVALID:GET', logging_context)

    def test_get_schema_info_valid_schema(self):
        from shared.items.common import get_schema_info
        event = {'pathParameters': {'schema': 'app'}, 'httpMethod': 'GET'}
        
        schema_name, schema, logging_context = get_schema_info(event)
        
        self.assertEqual('app', schema_name)
        self.assertIsNotNone(schema)
        self.assertEqual('app:GET', logging_context)

    def test_find_schema_exists(self):
        from shared.items.common import find_schema
        result = find_schema('app')
        self.assertIsNotNone(result)
        self.assertEqual('app', result['schema_name'])

    def test_find_schema_not_exists(self):
        from shared.items.common import find_schema
        result = find_schema('nonexistent')
        self.assertIsNone(result)

    def test_get_data_table_standard_schema(self):
        from shared.items.common import get_data_table
        table = get_data_table('app', 'user')
        self.assertTrue(table.name.endswith('-apps'))

    def test_get_data_table_custom_schema(self):
        from shared.items.common import get_data_table
        table = get_data_table('custom_asset', 'custom')
        self.assertTrue(table.name.endswith('-custom-assets'))

    def test_is_iam_request_true(self):
        from shared.items.common import is_iam_request
        event = {'requestContext': {'identity': {'userArn': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'}}}
        self.assertTrue(is_iam_request(event))

    def test_is_iam_request_false(self):
        from shared.items.common import is_iam_request
        event = {'requestContext': {'authorizer': {'claims': {'sub': 'user123'}}}}
        self.assertFalse(is_iam_request(event))

    def test_create_error_response_with_string(self):
        from shared.items.common import create_error_response
        response = create_error_response(400, 'Test error message')
        
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Test error message', response['body'])
        self.assertIn('headers', response)

    def test_create_error_response_with_object(self):
        from shared.items.common import create_error_response
        response = create_error_response(500, {'error': 'Internal error'})
        
        self.assertEqual(500, response['statusCode'])
        self.assertEqual('{"errors": [{"error": "Internal error"}]}', response['body'])

    def test_parse_json_body_valid(self):
        from shared.items.common import parse_json_body
        event = {'body': '{"test": "value"}'}
        
        result = parse_json_body(event, 'test_context')
        
        self.assertEqual({'test': 'value'}, result)

    def test_parse_json_body_invalid(self):
        from shared.items.common import parse_json_body
        event = {'body': 'invalid json'}
        
        result = parse_json_body(event, 'test_context')
        
        self.assertEqual(400, result['statusCode'])
        self.assertIn('malformed json input', result['body'])

    def test_validate_s3_format_valid(self):
        from shared.items.common import validate_s3_format
        body = {'auth_info': 'anything', 'data': [{'item': 'value'}]}
        
        self.assertTrue(validate_s3_format(body))

    def test_validate_s3_format_invalid_missing_user(self):
        from shared.items.common import validate_s3_format
        body = {'data': [{'item': 'value'}]}
        
        self.assertFalse(validate_s3_format(body))

    def test_validate_s3_format_invalid_missing_data(self):
        from shared.items.common import validate_s3_format
        body = {'user': 'test-user'}
        
        self.assertFalse(validate_s3_format(body))

    def test_validate_s3_format_invalid_not_dict(self):
        from shared.items.common import validate_s3_format
        body = "not a dict"
        
        self.assertFalse(validate_s3_format(body))

    def test_json_encoder_decimal(self):
        from shared.items.common import JsonEncoder
        from decimal import Decimal
        
        encoder = JsonEncoder()
        result = encoder.default(Decimal('123.45'))
        
        self.assertEqual(123.45, result)
        self.assertIsInstance(result, float)

    def test_json_encoder_bytes(self):
        from shared.items.common import JsonEncoder
        
        encoder = JsonEncoder()
        result = encoder.default(b'test bytes')
        
        self.assertEqual('test bytes', result)

    @mock.patch('shared.items.common.MFAuth')
    def test_get_auth_response(self, mock_mfauth):
        from shared.items.common import get_auth_response
        
        mock_auth_instance = mock_mfauth.return_value
        mock_auth_instance.get_user_attribute_policy.return_value = {'action': 'allow', 'user': 'test-user'}
        
        event = {'requestContext': {'authorizer': {'claims': {'sub': 'user123'}}}}
        result = get_auth_response(event, 'app')
        
        self.assertEqual({'action': 'allow', 'user': 'test-user'}, result)
        mock_auth_instance.get_user_attribute_policy.assert_called_once_with(event, 'app')

    @mock.patch('shared.items.common.MFAuth')
    def test_get_auth_response_for_creation(self, mock_mfauth):
        from shared.items.common import get_auth_response_for_creation
        
        mock_auth_instance = mock_mfauth.return_value
        mock_auth_instance.get_user_resource_creation_policy.return_value = {'action': 'allow', 'user': 'test-user'}
        
        event = {'requestContext': {'authorizer': {'claims': {'sub': 'user123'}}}}
        result = get_auth_response_for_creation(event, 'app')
        
        self.assertEqual({'action': 'allow', 'user': 'test-user'}, result)
        mock_auth_instance.get_user_resource_creation_policy.assert_called_once_with(event, 'app')

    @mock.patch('shared.items.common.MFAuth')
    def test_get_auth_response_for_deletion(self, mock_mfauth):
        from shared.items.common import get_auth_response_for_deletion
        
        mock_auth_instance = mock_mfauth.return_value
        mock_auth_instance.get_user_resource_creation_policy.return_value = {'action': 'allow', 'user': 'test-user'}
        
        event = {'requestContext': {'authorizer': {'claims': {'sub': 'user123'}}}}
        result = get_auth_response_for_deletion(event, 'app')
        
        self.assertEqual({'action': 'allow', 'user': 'test-user'}, result)
        mock_auth_instance.get_user_resource_creation_policy.assert_called_once_with(event, 'app')

    def test_create_auth_error_response(self):
        from shared.items.common import create_auth_error_response
        
        auth_response = {'action': 'deny', 'cause': 'Insufficient permissions'}
        result = create_auth_error_response(auth_response, 'test_context')
        
        self.assertEqual(401, result['statusCode'])
        expected_body = json.dumps({'errors': [auth_response]})
        self.assertEqual(expected_body, result['body'])

    def test_update_audit_trail_with_user(self):
        from shared.items.common import update_audit_trail
        from datetime import datetime, timezone
        
        updated_item = {'Item': {'_history': {'createdBy': 'original-user', 'createdTimestamp': '2023-01-01T00:00:00Z'}}}
        auth_response = {'user': 'test-user'}
        
        update_audit_trail(updated_item, auth_response)
        
        history = updated_item['Item']['_history']
        self.assertEqual('test-user', history['lastModifiedBy'])
        self.assertIn('lastModifiedTimestamp', history)
        self.assertEqual('original-user', history['createdBy'])
        self.assertEqual('2023-01-01T00:00:00Z', history['createdTimestamp'])

    def test_update_audit_trail_no_user(self):
        from shared.items.common import update_audit_trail
        
        updated_item = {'Item': {}}
        auth_response = {}
        
        update_audit_trail(updated_item, auth_response)
        
        history = updated_item['Item']['_history']
        self.assertNotIn('lastModifiedBy', history)
        self.assertNotIn('lastModifiedTimestamp', history)

    def test_create_audit_info_with_user(self):
        from shared.items.common import create_audit_info
        
        auth_response = {'user': 'test-user'}
        result = create_audit_info(auth_response)
        
        self.assertEqual('test-user', result['createdBy'])
        self.assertIn('createdTimestamp', result)

    def test_create_audit_info_no_user(self):
        from shared.items.common import create_audit_info
        
        auth_response = {}
        result = create_audit_info(auth_response)
        
        self.assertEqual({}, result)

    def test_normalize_to_list_dict_input(self):
        from shared.items.common import normalize_to_list
        
        body = {'item': 'value'}
        result = normalize_to_list(body, 'test_context')
        
        self.assertEqual([{'item': 'value'}], result)

    def test_normalize_to_list_list_input(self):
        from shared.items.common import normalize_to_list
        
        body = [{'item1': 'value1'}, {'item2': 'value2'}]
        result = normalize_to_list(body, 'test_context')
        
        self.assertEqual([{'item1': 'value1'}, {'item2': 'value2'}], result)

    def test_convert_floats_to_decimal_float(self):
        from cmf_utils import convert_floats_to_decimal
        from decimal import Decimal
        
        result = convert_floats_to_decimal(4354.12)
        
        self.assertIsInstance(result, Decimal)
        self.assertEqual(Decimal('4354.12'), result)

    def test_convert_floats_to_decimal_dict(self):
        from cmf_utils import convert_floats_to_decimal
        from decimal import Decimal
        
        data = {'price': 99.99, 'name': 'test', 'count': 5}
        result = convert_floats_to_decimal(data)
        
        self.assertEqual(Decimal('99.99'), result['price'])
        self.assertEqual('test', result['name'])
        self.assertEqual(5, result['count'])

    def test_convert_floats_to_decimal_list(self):
        from cmf_utils import convert_floats_to_decimal
        from decimal import Decimal
        
        data = [1.5, 'text', {'nested': 2.7}]
        result = convert_floats_to_decimal(data)
        
        self.assertEqual(Decimal('1.5'), result[0])
        self.assertEqual('text', result[1])
        self.assertEqual(Decimal('2.7'), result[2]['nested'])

    def test_convert_floats_to_decimal_non_float(self):
        from cmf_utils import convert_floats_to_decimal
        
        # Test various non-float types remain unchanged
        self.assertEqual('string', convert_floats_to_decimal('string'))
        self.assertEqual(42, convert_floats_to_decimal(42))
        self.assertEqual(True, convert_floats_to_decimal(True))
        self.assertEqual(None, convert_floats_to_decimal(None))