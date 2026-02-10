#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from test_common_utils import default_mock_os_environ

@mock.patch.dict('os.environ', default_mock_os_environ)
class S3ImportBatchProcessorTest(unittest.TestCase):

    def setUp(self):
        self.processed_creates = {
            'app': [
                {'app_id': 'app-1', 'app_name': 'TestApp1'},
                {'app_id': 'app-2', 'app_name': 'TestApp2'}
            ]
        }
        
        self.processed_updates = {
            'app': [
                {'app_id': 'app-1', 'server_ids': ['server-1']},
                {'app_id': 'app-2', 'server_ids': ['server-2']}
            ]
        }
        
        self.auth_info = {'user': 'test-user'}
        self.mock_results = MagicMock()
        self.mock_results.created_items = {}
        self.mock_results.updated_items = {}
        self.mock_results.create_failures = {}
        self.mock_results.update_failures = {}
        self.mock_results.get_successful_creates_count.return_value = 0
        self.mock_results.get_successful_updates_count.return_value = 0
        self.mock_results.get_failed_creates_count.return_value = 0
        self.mock_results.get_failed_updates_count.return_value = 0

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_create_phase_success(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        mock_lambda_invoke.return_value = {
            'success': True,
            'new_items': [
                {'app_id': 'app-1', 'app_name': 'TestApp1'},
                {'app_id': 'app-2', 'app_name': 'TestApp2'}
            ],
            'api_errors': {}
        }
        
        result = s3_import_batch_processor.execute_create_phase(
            self.processed_creates, self.auth_info, self.mock_results
        )
        
        self.assertEqual(result, {})  # No failed entities
        mock_lambda_invoke.assert_called_once_with('POST', 'app', self.processed_creates['app'], self.auth_info)

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_create_phase_failure(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        mock_lambda_invoke.return_value = {
            'success': False,
            'api_errors': {'error': 'Test error'}
        }
        
        result = s3_import_batch_processor.execute_create_phase(
            self.processed_creates, self.auth_info, self.mock_results
        )
        
        self.assertIn('app', result)  # Should have failed entities

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_create_phase_exception(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        mock_lambda_invoke.side_effect = Exception('Lambda Error')
        
        result = s3_import_batch_processor.execute_create_phase(
            self.processed_creates, self.auth_info, self.mock_results
        )
        
        self.assertIn('app', result)  # Should have failed entities

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_update_phase_success(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        mock_lambda_invoke.return_value = {
            'success': True,
            'api_errors': {}
        }
        
        s3_import_batch_processor.execute_update_phase(
            self.processed_updates, self.auth_info, self.mock_results
        )
        
        mock_lambda_invoke.assert_called_once_with('PUT', 'app', self.processed_updates['app'], self.auth_info)

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_update_phase_failure(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        mock_lambda_invoke.return_value = {
            'success': False,
            'api_errors': {'error': 'Test error'}
        }
        
        s3_import_batch_processor.execute_update_phase(
            self.processed_updates, self.auth_info, self.mock_results
        )

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_update_phase_exception(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        mock_lambda_invoke.side_effect = Exception('Lambda Error')
        
        s3_import_batch_processor.execute_update_phase(
            self.processed_updates, self.auth_info, self.mock_results
        )

    def test_handle_create_batch_failure(self):
        import s3_import_batch_processor
        from results import FailureDetails
        
        batch = [{'app_id': 'app-1', 'app_name': 'TestApp1'}]
        response = {'success': False, 'api_errors': {'error': 'Test error'}}
        entity_failed_ids = []
        
        s3_import_batch_processor.handle_create_batch_failure(
            'app', batch, response, self.mock_results, entity_failed_ids
        )
        
        self.assertEqual(len(entity_failed_ids), 1)
        self.assertEqual(entity_failed_ids[0], 'app-1')

    def test_handle_update_batch_failure(self):
        import s3_import_batch_processor
        from results import FailureDetails
        
        batch = [{'app_id': 'app-1', 'app_name': 'TestApp1'}]
        response = {'success': False, 'api_errors': {'error': 'Test error'}}
        
        s3_import_batch_processor.handle_update_batch_failure(
            'app', batch, response, self.mock_results
        )

    @patch('s3_import_batch_processor.invoke_lambda_function')
    def test_execute_create_phase_large_batch(self, mock_lambda_invoke):
        import s3_import_batch_processor
        
        # Create a large dataset to test batching
        large_creates = {
            'app': [{'app_id': f'app-{i}', 'app_name': f'TestApp{i}'} for i in range(400)]
        }
        
        mock_lambda_invoke.return_value = {
            'success': True,
            'new_items': [{'app_id': f'app-{i}', 'app_name': f'TestApp{i}'} for i in range(200)],
            'api_errors': {}
        }
        
        result = s3_import_batch_processor.execute_create_phase(
            large_creates, self.auth_info, self.mock_results
        )
        
        # Should be called twice (2 batches of 200 each)
        self.assertEqual(mock_lambda_invoke.call_count, 2)

    def test_handle_create_entity_type_failure(self):
        import s3_import_batch_processor
        
        entity_data = [{'app_id': 'app-1', 'app_name': 'TestApp1'}]
        error = Exception('Entity type error')
        failed_entity_ids = {}
        
        s3_import_batch_processor.handle_create_entity_type_failure(
            'app', entity_data, error, self.mock_results, failed_entity_ids
        )
        
        self.assertIn('app', failed_entity_ids)
        self.assertEqual(len(failed_entity_ids['app']), 1)

    def test_handle_update_entity_type_failure(self):
        import s3_import_batch_processor
        
        entity_data = [{'app_id': 'app-1', 'app_name': 'TestApp1'}]
        error = Exception('Entity type error')
        
        s3_import_batch_processor.handle_update_entity_type_failure(
            'app', entity_data, error, self.mock_results
        )

if __name__ == '__main__':
    unittest.main()