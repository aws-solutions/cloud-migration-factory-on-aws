#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from test_common_utils import default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    'TOOLS_API_ID': 'test_api_id',
    'region': 'us-east-1'
}

@mock.patch.dict('os.environ', mock_os_environ)
class LambdaImportDataFromS3Test(unittest.TestCase):

    def setUp(self):
        self.valid_s3_event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'uploads/test-file.json'}
                }
            }]
        }
        
        self.invalid_event = {'Records': []}
        
        self.mock_context = MagicMock()
        self.mock_context.function_name = 'test-function'
        
        self.sample_import_data = {
            'entities_to_create': [{
                'entityName': 'app',
                'schema': {
                    'schema_name': 'app',
                    'attributes': [{'name': 'app_name', 'type': 'string'}]
                },
                'data': {
                    'app1': {'app_name': 'TestApp1'}
                }
            }],
            'entities_to_update': [],
            'issues': {
                'deduplicationErrors': [],
                'validationErrors': []
            }
        }

    @patch('lambda_import_data_from_s3.process_s3_record')
    @patch('lambda_import_data_from_s3.fetch_all_schemas')
    def test_lambda_handler_success(self, mock_fetch_schemas, mock_process_record):
        import lambda_import_data_from_s3
        
        mock_fetch_schemas.return_value = {'app': {'schema_name': 'app'}}
        mock_process_record.return_value = None
        
        result = lambda_import_data_from_s3.lambda_handler(self.valid_s3_event, self.mock_context)
        
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('Successfully processed 1 files', result['body'])
        mock_fetch_schemas.assert_called_once()
        mock_process_record.assert_called_once()

    def test_lambda_handler_no_records(self):
        import lambda_import_data_from_s3
        
        with self.assertRaises(Exception):
            lambda_import_data_from_s3.lambda_handler(self.invalid_event, self.mock_context)

    @patch('lambda_import_data_from_s3.process_s3_record')
    @patch('lambda_import_data_from_s3.fetch_all_schemas')
    def test_lambda_handler_processing_failure(self, mock_fetch_schemas, mock_process_record):
        import lambda_import_data_from_s3
        
        mock_fetch_schemas.return_value = {}
        mock_process_record.side_effect = Exception('Processing failed')
        
        with self.assertRaises(Exception):
            lambda_import_data_from_s3.lambda_handler(self.valid_s3_event, self.mock_context)

    @patch('lambda_import_data_from_s3.save_results_and_complete')
    @patch('lambda_import_data_from_s3.update_entities')
    @patch('lambda_import_data_from_s3.create_entities')
    @patch('lambda_import_data_from_s3.process_entities')
    @patch('lambda_import_data_from_s3.read_data_from_s3')
    @patch('lambda_import_data_from_s3.create_processing_results')
    def test_process_s3_record_success(self, mock_create_results, mock_read_data, 
                                     mock_process_entities, mock_create_entities, 
                                     mock_update_entities, mock_save_results):
        import lambda_import_data_from_s3
        
        # Mock workflow data
        mock_workflow_data = MagicMock()
        mock_workflow_data.upload_id = 'test-upload-id'
        mock_workflow_data.object_key = 'uploads/test.json'
        mock_workflow_data.uploaded_by = 'test-user'
        mock_workflow_data.import_data = MagicMock()
        
        mock_results = MagicMock()
        
        mock_read_data.return_value = mock_workflow_data
        mock_create_results.return_value = mock_results
        mock_process_entities.return_value = mock_workflow_data
        mock_create_entities.return_value = mock_workflow_data
        mock_update_entities.return_value = mock_workflow_data
        
        lambda_import_data_from_s3.process_s3_record(self.valid_s3_event['Records'][0], {})
        
        mock_read_data.assert_called_once()
        mock_create_results.assert_called_once()
        mock_process_entities.assert_called_once()
        mock_create_entities.assert_called_once()
        mock_update_entities.assert_called_once()

    @patch('lambda_import_data_from_s3.get_s3_file_content')
    @patch('lambda_import_data_from_s3.get_upload_metadata')
    @patch('lambda_import_data_from_s3.check_and_update_upload_status')
    @patch('lambda_import_data_from_s3.parse_import_request')
    def test_read_data_from_s3_success(self, mock_parse_request, mock_check_status,
                                     mock_get_metadata, mock_get_content):
        import lambda_import_data_from_s3
        
        mock_get_metadata.return_value = ('upload-123', 'test-user')
        mock_check_status.return_value = {'auth_info': {'user': 'test-user'}}
        mock_get_content.return_value = json.dumps(self.sample_import_data)
        mock_parse_request.return_value = MagicMock()
        
        result = lambda_import_data_from_s3.read_data_from_s3(self.valid_s3_event['Records'][0])
        
        self.assertEqual(result.upload_id, 'upload-123')
        self.assertEqual(result.uploaded_by, 'test-user')
        mock_get_metadata.assert_called_once()
        mock_check_status.assert_called_once()
        mock_get_content.assert_called_once()
        mock_parse_request.assert_called_once()

    @patch('lambda_import_data_from_s3.get_upload_metadata')
    def test_read_data_from_s3_no_upload_id(self, mock_get_metadata):
        import lambda_import_data_from_s3
        
        mock_get_metadata.return_value = (None, None)
        
        with self.assertRaises(Exception):
            lambda_import_data_from_s3.read_data_from_s3(self.valid_s3_event['Records'][0])

    @patch('lambda_import_data_from_s3.process_entities_for_import')
    def test_process_entities_success(self, mock_process_entities_for_import):
        import lambda_import_data_from_s3
        
        mock_workflow_data = MagicMock()
        mock_workflow_data.import_data.entities_to_create = []
        mock_workflow_data.import_data.entities_to_update = []
        mock_workflow_data.schema_cache = {}
        
        mock_results = MagicMock()
        
        mock_process_entities_for_import.return_value = {
            'entities_to_create': {},
            'entities_to_update': {},
            'name_to_id_map': {}
        }
        
        result = lambda_import_data_from_s3.process_entities(mock_workflow_data, mock_results)
        
        self.assertEqual(result.processed_creates, {})
        self.assertEqual(result.processed_updates, {})
        mock_process_entities_for_import.assert_called_once()

    @patch('s3_import_batch_processor.execute_create_phase')
    @patch('lambda_import_data_from_s3.remove_failed_entities_from_updates')
    def test_create_entities_success(self, mock_remove_failed, mock_execute_create):
        import lambda_import_data_from_s3
        
        mock_workflow_data = MagicMock()
        mock_workflow_data.processed_creates = {'app': []}
        mock_workflow_data.processed_updates = {'app': []}
        mock_workflow_data.auth_info = {}
        mock_workflow_data.schema_cache = {}
        
        mock_results = MagicMock()
        
        mock_execute_create.return_value = {}
        
        result = lambda_import_data_from_s3.create_entities(mock_workflow_data, mock_results)
        
        mock_execute_create.assert_called_once()
        mock_remove_failed.assert_not_called()

    @patch('s3_import_batch_processor.execute_update_phase')
    def test_update_entities_success(self, mock_execute_update):
        import lambda_import_data_from_s3
        
        mock_workflow_data = MagicMock()
        mock_workflow_data.processed_updates = {'app': []}
        mock_workflow_data.auth_info = {}
        
        mock_results = MagicMock()
        
        result = lambda_import_data_from_s3.update_entities(mock_workflow_data, mock_results)
        
        mock_execute_update.assert_called_once()

    @patch('lambda_import_data_from_s3.save_results_to_s3')
    @patch('lambda_import_data_from_s3.update_upload_status')
    def test_save_results_and_complete_success(self, mock_update_status, mock_save_results):
        import lambda_import_data_from_s3
        
        mock_workflow_data = MagicMock()
        mock_workflow_data.upload_id = 'upload-123'
        mock_workflow_data.object_key = 'uploads/test.json'
        mock_workflow_data.s3_bucket = 'test-bucket'
        
        mock_results = MagicMock()
        mock_results.has_failures.return_value = False
        
        mock_save_results.return_value = 's3://test-bucket/results/test.json'
        
        lambda_import_data_from_s3.save_results_and_complete(mock_workflow_data, mock_results)
        
        mock_save_results.assert_called_once()
        mock_update_status.assert_called_once_with('upload-123', 'complete', 's3://test-bucket/results/test.json')

    @patch('lambda_import_data_from_s3.save_results_to_s3')
    @patch('lambda_import_data_from_s3.update_upload_status')
    def test_save_results_and_complete_with_failures(self, mock_update_status, mock_save_results):
        import lambda_import_data_from_s3
        
        mock_workflow_data = MagicMock()
        mock_workflow_data.upload_id = 'upload-123'
        mock_workflow_data.object_key = 'uploads/test.json'
        mock_workflow_data.s3_bucket = 'test-bucket'
        
        mock_results = MagicMock()
        mock_results.has_failures.return_value = True
        
        mock_save_results.return_value = 's3://test-bucket/results/test.json'
        
        lambda_import_data_from_s3.save_results_and_complete(mock_workflow_data, mock_results)
        
        mock_update_status.assert_called_once_with('upload-123', 'failed', 's3://test-bucket/results/test.json')

    @patch('lambda_import_data_from_s3.save_results_to_s3')
    @patch('lambda_import_data_from_s3.update_upload_status')
    def test_handle_processing_error(self, mock_update_status, mock_save_results):
        import lambda_import_data_from_s3
        
        mock_workflow_data = MagicMock()
        mock_workflow_data.upload_id = 'upload-123'
        mock_workflow_data.object_key = 'uploads/test.json'
        mock_workflow_data.s3_bucket = 'test-bucket'
        mock_workflow_data.import_data = MagicMock()
        mock_workflow_data.import_data.entities_to_create = []
        mock_workflow_data.import_data.entities_to_update = []
        
        mock_results = MagicMock()
        mock_save_results.return_value = 's3://test-bucket/results/test.json'
        
        error = Exception('Test error')
        
        lambda_import_data_from_s3.handle_processing_error(mock_workflow_data, mock_results, error)
        
        mock_save_results.assert_called_once()
        mock_update_status.assert_called_once_with('upload-123', 'failed', 's3://test-bucket/results/test.json')

    def test_remove_failed_entities_from_updates(self):
        import lambda_import_data_from_s3
        
        processed_updates = {
            'app': [
                {'app_id': 'failed-id-1', 'app_name': 'FailedApp1'},
                {'app_id': 'success-id-1', 'app_name': 'SuccessApp1'}
            ]
        }
        
        failed_entity_ids = {
            'app': ['failed-id-1']
        }
        
        mock_results = MagicMock()
        schema_cache = {
            'app': {
                'attributes': [
                    {'name': 'server_ids', 'type': 'multivalue-relationship', 'rel_entity': 'server'}
                ]
            }
        }
        
        lambda_import_data_from_s3.remove_failed_entities_from_updates(
            processed_updates, failed_entity_ids, mock_results, schema_cache
        )
        
        # Should remove the failed entity
        self.assertEqual(len(processed_updates['app']), 1)
        self.assertEqual(processed_updates['app'][0]['app_id'], 'success-id-1')

    def test_invalid_s3_record_structure(self):
        import lambda_import_data_from_s3
        
        invalid_record = {'invalid': 'structure'}
        
        with self.assertRaises(Exception):
            lambda_import_data_from_s3.read_data_from_s3(invalid_record)

if __name__ == '__main__':
    unittest.main()