#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from test_common_utils import default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    'application': 'migration-factory',
    'environment': 'test',
    'region': 'us-east-1'
}

@mock.patch.dict('os.environ', mock_os_environ)
class S3ImportLambdaClientTest(unittest.TestCase):

    def setUp(self):
        self.sample_data = [{'app_id': 'test-id', 'app_name': 'TestApp'}]
        self.auth_info = {'user': 'test-user'}

    @patch('s3_import_lambda_client.lambda_client')
    def test_invoke_lambda_function_post_success(self, mock_lambda_client):
        import s3_import_lambda_client
        
        mock_response = {
            'StatusCode': 200,
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({
                'newItems': [{'app_id': 'new-id', 'app_name': 'NewApp'}],
                'errors': {}
            })
        }).encode('utf-8')
        mock_lambda_client.invoke.return_value = mock_response
        
        result = s3_import_lambda_client.invoke_lambda_function('POST', 'app', self.sample_data, self.auth_info)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(len(result['new_items']), 1)

    @patch('s3_import_lambda_client.lambda_client')
    def test_invoke_lambda_function_put_success(self, mock_lambda_client):
        import s3_import_lambda_client
        
        mock_response = {
            'StatusCode': 200,
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({
                'newItems': [],
                'errors': {}
            })
        }).encode('utf-8')
        mock_lambda_client.invoke.return_value = mock_response
        
        result = s3_import_lambda_client.invoke_lambda_function('PUT', 'app', self.sample_data, self.auth_info)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['status_code'], 200)

    @patch('s3_import_lambda_client.lambda_client')
    def test_invoke_lambda_function_server_error(self, mock_lambda_client):
        import s3_import_lambda_client
        
        mock_response = {
            'StatusCode': 200,
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'statusCode': 500,
            'body': 'Internal Server Error'
        }).encode('utf-8')
        mock_lambda_client.invoke.return_value = mock_response
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.invoke_lambda_function('POST', 'app', self.sample_data, self.auth_info)

    @patch('s3_import_lambda_client.lambda_client')
    def test_invoke_lambda_function_client_error(self, mock_lambda_client):
        import s3_import_lambda_client
        
        mock_response = {
            'StatusCode': 200,
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'statusCode': 400,
            'body': 'Bad Request'
        }).encode('utf-8')
        mock_lambda_client.invoke.return_value = mock_response
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.invoke_lambda_function('POST', 'app', self.sample_data, self.auth_info)

    @patch('s3_import_lambda_client.lambda_client')
    def test_invoke_lambda_function_error(self, mock_lambda_client):
        import s3_import_lambda_client
        
        mock_response = {
            'StatusCode': 200,
            'FunctionError': 'Unhandled',
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'errorMessage': 'Function failed'
        }).encode('utf-8')
        mock_lambda_client.invoke.return_value = mock_response
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.invoke_lambda_function('POST', 'app', self.sample_data, self.auth_info)

    def test_validate_lambda_request_inputs_invalid_method(self):
        import s3_import_lambda_client
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.validate_lambda_request_inputs('INVALID', 'app', self.sample_data, self.auth_info)

    def test_validate_lambda_request_inputs_invalid_entity_name(self):
        import s3_import_lambda_client
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.validate_lambda_request_inputs('POST', '', self.sample_data, self.auth_info)

    def test_validate_lambda_request_inputs_invalid_data(self):
        import s3_import_lambda_client
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.validate_lambda_request_inputs('POST', 'app', [], self.auth_info)

    def test_get_function_name_post(self):
        import s3_import_lambda_client
        
        function_name = s3_import_lambda_client.get_function_name('POST')
        self.assertTrue(function_name.endswith('-items'))

    def test_get_function_name_put(self):
        import s3_import_lambda_client
        
        function_name = s3_import_lambda_client.get_function_name('PUT')
        self.assertTrue(function_name.endswith('-item'))

    def test_get_function_name_invalid_method(self):
        import s3_import_lambda_client
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.get_function_name('INVALID')

    def test_create_lambda_payload(self):
        import s3_import_lambda_client
        
        payload = s3_import_lambda_client.create_lambda_payload('POST', 'app', self.sample_data, self.auth_info)
        
        self.assertEqual(payload['httpMethod'], 'POST')
        self.assertEqual(payload['pathParameters']['schema'], 'app')
        self.assertIn('data', json.loads(payload['body']))
        self.assertIn('auth_info', json.loads(payload['body']))

    def test_validate_lambda_response_success(self):
        import s3_import_lambda_client
        
        response_payload = {
            'statusCode': 200,
            'body': json.dumps({'newItems': [], 'errors': {}})
        }
        
        result = s3_import_lambda_client.validate_lambda_response(response_payload, 'POST', 'app')
        self.assertEqual(result, response_payload['body'])

    def test_validate_lambda_response_server_error(self):
        import s3_import_lambda_client
        
        response_payload = {
            'statusCode': 500,
            'body': 'Internal Server Error'
        }
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.validate_lambda_response(response_payload, 'POST', 'app')

    def test_validate_lambda_response_body_with_errors(self):
        import s3_import_lambda_client
        
        response_data = json.dumps({
            'errors': ['Test error message']
        })
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.validate_lambda_response_body(response_data, 'POST', 'app')

    def test_validate_lambda_response_body_invalid_json(self):
        import s3_import_lambda_client
        
        response_data = 'invalid json'
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.validate_lambda_response_body(response_data, 'POST', 'app')

    def test_check_lambda_response_errors_list(self):
        import s3_import_lambda_client
        
        api_json = {'errors': ['Error 1', 'Error 2']}
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.check_lambda_response_errors(api_json, 'POST', 'app')

    def test_check_lambda_response_errors_dict(self):
        import s3_import_lambda_client
        
        api_json = {'errors': {'validation': ['Invalid field']}}
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.check_lambda_response_errors(api_json, 'POST', 'app')

    def test_build_lambda_error_details(self):
        import s3_import_lambda_client
        
        errors = {
            'validation': ['Field required'],
            'processing': 'Processing failed'
        }
        
        result = s3_import_lambda_client.build_lambda_error_details(errors)
        
        self.assertEqual(len(result), 2)
        self.assertIn('validation: Field required', result)
        self.assertIn('processing: Processing failed', result)

    def test_create_lambda_response_success(self):
        import s3_import_lambda_client
        
        response_payload = {'statusCode': 200}
        response_data = json.dumps({
            'newItems': [{'app_id': 'new-id'}],
            'errors': {}
        })
        
        result = s3_import_lambda_client.create_lambda_response('app', self.sample_data, response_payload, response_data)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(len(result['new_items']), 1)

    def test_create_lambda_response_with_errors(self):
        import s3_import_lambda_client
        
        response_payload = {'statusCode': 200}
        response_data = json.dumps({
            'newItems': [],
            'errors': {'validation': ['Error']}
        })
        
        with self.assertRaises(Exception):
            s3_import_lambda_client.create_lambda_response('app', self.sample_data, response_payload, response_data)

if __name__ == '__main__':
    unittest.main()