#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from test_common_utils import default_mock_os_environ

@mock.patch.dict('os.environ', default_mock_os_environ)
class S3ImportS3OperationsTest(unittest.TestCase):

    def setUp(self):
        self.bucket_name = 'test-bucket'
        self.object_key = 'uploads/test-file.json'
        self.upload_id = 'test-upload-123'
        self.uploaded_by = 'test-user'

    @patch('s3_import_s3_operations.s3_client')
    def test_get_upload_metadata_success(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_s3_client.head_object.return_value = {
            'Metadata': {
                'upload-id': self.upload_id,
                'uploaded-by': self.uploaded_by
            }
        }
        
        upload_id, uploaded_by = s3_import_s3_operations.get_upload_metadata(
            self.bucket_name, self.object_key
        )
        
        self.assertEqual(upload_id, self.upload_id)
        self.assertEqual(uploaded_by, self.uploaded_by)
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=self.bucket_name, Key=self.object_key
        )

    @patch('s3_import_s3_operations.s3_client')
    def test_get_upload_metadata_no_upload_id(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_s3_client.head_object.return_value = {
            'Metadata': {
                'uploaded-by': self.uploaded_by
            }
        }
        
        upload_id, uploaded_by = s3_import_s3_operations.get_upload_metadata(
            self.bucket_name, self.object_key
        )
        
        self.assertIsNone(upload_id)
        self.assertIsNone(uploaded_by)

    @patch('s3_import_s3_operations.s3_client')
    def test_get_upload_metadata_exception(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_s3_client.head_object.side_effect = Exception('S3 Error')
        
        with self.assertRaises(Exception):
            s3_import_s3_operations.get_upload_metadata(self.bucket_name, self.object_key)

    @patch('s3_import_s3_operations.s3_client')
    def test_get_s3_file_content_success(self, mock_s3_client):
        import s3_import_s3_operations
        
        test_content = json.dumps({'test': 'data'})
        mock_response = {
            'Body': MagicMock(),
            'ContentLength': len(test_content)
        }
        mock_response['Body'].read.return_value = test_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response
        
        content = s3_import_s3_operations.get_s3_file_content(self.bucket_name, self.object_key)
        
        self.assertEqual(content, test_content)
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=self.bucket_name, Key=self.object_key
        )

    @patch('s3_import_s3_operations.s3_client')
    def test_get_s3_file_content_empty_file(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_response = {
            'Body': MagicMock(),
            'ContentLength': 0
        }
        mock_s3_client.get_object.return_value = mock_response
        
        with self.assertRaises(Exception):
            s3_import_s3_operations.get_s3_file_content(self.bucket_name, self.object_key)

    @patch('s3_import_s3_operations.s3_client')
    def test_get_s3_file_content_too_large(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_response = {
            'Body': MagicMock(),
            'ContentLength': 200 * 1024 * 1024  # 200MB
        }
        mock_s3_client.get_object.return_value = mock_response
        
        with self.assertRaises(Exception):
            s3_import_s3_operations.get_s3_file_content(self.bucket_name, self.object_key)

    @patch('s3_import_s3_operations.s3_client')
    def test_get_s3_file_content_invalid_utf8(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_response = {
            'Body': MagicMock(),
            'ContentLength': 10
        }
        mock_response['Body'].read.return_value = b'\xff\xfe'  # Invalid UTF-8
        mock_s3_client.get_object.return_value = mock_response
        
        with self.assertRaises(Exception):
            s3_import_s3_operations.get_s3_file_content(self.bucket_name, self.object_key)

    @patch('s3_import_s3_operations.s3_client')
    def test_save_results_to_s3_success(self, mock_s3_client):
        import s3_import_s3_operations
        
        # Create a proper object with attributes including validation issues
        class MockValidationIssues:
            def __init__(self):
                self.deduplicationErrors = []
                self.validationErrors = [{'entityName': 'app', 'message': 'test error'}]
        
        class MockResults:
            def __init__(self):
                self.upload_id = 'test-upload-123'
                self.summary = {'successful_creates': 1, 'failed_creates': 0}
                self.validation_issues = MockValidationIssues()
        
        mock_results = MockResults()
        
        result_location = s3_import_s3_operations.save_results_to_s3(
            self.bucket_name, self.upload_id, mock_results, self.object_key
        )
        
        expected_key = 'results/test-file.json'
        expected_location = f's3://{self.bucket_name}/{expected_key}'
        
        self.assertEqual(result_location, expected_location)
        mock_s3_client.put_object.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_s3_client.put_object.call_args
        self.assertEqual(call_args[1]['Bucket'], self.bucket_name)
        self.assertEqual(call_args[1]['Key'], expected_key)
        self.assertEqual(call_args[1]['ContentType'], 'application/json')
        self.assertEqual(call_args[1]['Metadata']['upload-id'], self.upload_id)
        
        # Verify validation issues are correctly serialized in the JSON content
        uploaded_content = call_args[1]['Body']
        parsed_content = json.loads(uploaded_content)
        
        self.assertIn('validation_issues', parsed_content)
        validation_issues = parsed_content['validation_issues']
        self.assertEqual(validation_issues['deduplicationErrors'], [])
        self.assertEqual(validation_issues['validationErrors'], [{'entityName': 'app', 'message': 'test error'}])

    @patch('s3_import_s3_operations.s3_client')
    def test_save_results_to_s3_empty_results(self, mock_s3_client):
        import s3_import_s3_operations
        
        with self.assertRaises(Exception):
            s3_import_s3_operations.save_results_to_s3(
                self.bucket_name, self.upload_id, None, self.object_key
            )

    @patch('s3_import_s3_operations.s3_client')
    def test_save_results_to_s3_exception(self, mock_s3_client):
        import s3_import_s3_operations
        
        mock_s3_client.put_object.side_effect = Exception('S3 Put Error')
        mock_results = MagicMock()
        mock_results.__dict__ = {'test': 'data'}
        
        with self.assertRaises(Exception):
            s3_import_s3_operations.save_results_to_s3(
                self.bucket_name, self.upload_id, mock_results, self.object_key
            )

    def test_save_results_filename_transformation(self):
        import s3_import_s3_operations
        
        # Test that uploads/ prefix is correctly replaced with results/
        test_cases = [
            ('uploads/batch1/data.json', 'results/batch1/data.json'),
            ('uploads/test.json', 'results/test.json'),
            ('uploads/nested/folder/file.json', 'results/nested/folder/file.json')
        ]
        
        for input_key, expected_key in test_cases:
            with patch('s3_import_s3_operations.s3_client') as mock_s3_client:
                # Create a proper object with attributes including validation issues
                class MockValidationIssues:
                    def __init__(self):
                        self.deduplicationErrors = []
                        self.validationErrors = []
                
                class MockResults:
                    def __init__(self):
                        self.test = 'data'
                        self.upload_id = 'test-upload-123'
                        self.validation_issues = MockValidationIssues()
                
                mock_results = MockResults()
                
                s3_import_s3_operations.save_results_to_s3(
                    self.bucket_name, self.upload_id, mock_results, input_key
                )
                
                call_args = mock_s3_client.put_object.call_args
                self.assertEqual(call_args[1]['Key'], expected_key)

if __name__ == '__main__':
    unittest.main()