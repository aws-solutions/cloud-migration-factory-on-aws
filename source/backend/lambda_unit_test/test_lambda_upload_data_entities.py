#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import uuid
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch, MagicMock, ANY
import unittest

import botocore
from moto import mock_aws
import test_common_utils
from test_common_utils import logger, default_mock_os_environ as mock_os_environ


# Mock environment variables for upload data entities
mock_upload_entities_environ = {
    **mock_os_environ,
    'UPLOAD_ENTITIES_METADATA_TABLE_NAME': 'test-upload-entities-table',
    'UPLOAD_ENTITIES_BUCKET_NAME': 'test-upload-entities-bucket'
}


def mock_get_mf_auth_policy_allow():
    """Mock successful authentication response"""
    return {
        'action': 'allow',
        'user': {
            'userRef': 'arn:aws:iam::123456789012:user/test-user'
        }
    }


def mock_get_mf_auth_policy_deny():
    """Mock denied authentication response"""
    return {
        'action': 'deny'
    }


def mock_get_user_policy_success():
    """Mock successful user policy response"""
    return (
        ['policy1', 'policy2'],
        {
            'userRef': 'arn:aws:iam::123456789012:user/test-user',
            'email': 'test-user@example.com'
        }
    )


def mock_get_user_policy_no_user():
    """Mock user policy response without userRef"""
    return (
        ['policy1', 'policy2'],
        {'email': 'test-user@example.com'}
    )

def mock_audit_history():
    """Mock audit history"""
    return {
        "createdBy": {"email": "serviceaccount@yourdomain.com", "userRef": "e9bec4f8-3061-708f-87a7-5d231c6eda1a"},
        "createdTimestamp": "2025-08-18T00:56:59.817819+00:00",
        "lastModifiedBy": {"email": "serviceaccount@yourdomain.com", "userRef": "e9bec4f8-3061-708f-87a7-5d231c6eda1a"},
        "lastModifiedTimestamp": "2025-08-18T00:57:05.451673+00:00",
    }

@mock.patch.dict('os.environ', mock_upload_entities_environ)
@mock_aws
class LambdaUploadDataEntitiesTest(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.init_mocks()
        self.init_event_objects()
        
    def init_mocks(self):
        """Initialize mock objects"""
        # Mock S3 client
        self.mock_s3_client = MagicMock()
        self.mock_s3_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/test-key?signature=test'
        
        # Mock repository
        self.mock_repository = MagicMock()
        self.mock_repository.create_upload_record.return_value = {
            'upload_id': 'test-upload-id',
            'filename': 'test-data.json',
            'status': 'pending',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
        }
        self.mock_repository.get_upload_record.return_value = {
            'upload_id': 'test-upload-id',
            'filename': 'test.json',
            'status': 'pending',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
        }
        self.mock_repository.list_uploads.return_value = {
            'items': [
                {
                    'upload_id': 'test-upload-1',
                    'filename': 'test1.json',
                    'status': 'complete',
                    'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
                    'file_size': 1024,
                    'total_entities': 100,
                    'data_source_id': 'test-source',
                    '_history': mock_audit_history(),
                },
                {
                    'upload_id': 'test-upload-2',
                    'filename': 'test2.json',
                    'status': 'pending',
                    'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
                    'file_size': 2048,
                    'total_entities': 200,
                    'data_source_id': 'test-source-2',
                    '_history': mock_audit_history(),
                }
            ],
            'count': 2
        }

    def init_event_objects(self):
        """Initialize test event objects"""
        # POST request event
        self.post_event = {
            'httpMethod': 'POST',
            'pathParameters': None,
            'body': json.dumps({
                'filename': 'cmf-5 singlesheet, v(2).xlsx',
                'updated_schemas': ['application', 'server'],
                'file_size': 1024,
                'total_entities': 100,
                'data_source_id': 'test-source'
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'arn:aws:iam::123456789012:user/test-user',
                        'cognito:groups': ['admin'],
                        'email': 'test-user@example.com'
                    }
                }
            }
        }
        
        # GET request event for specific upload
        self.get_upload_event = {
            'httpMethod': 'GET',
            'pathParameters': {'id': 'test-upload-id'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'arn:aws:iam::123456789012:user/test-user',
                        'cognito:groups': ['admin'],
                        'email': 'test-user@example.com'
                    }
                }
            }
        }
        
        # GET request event for listing uploads
        self.list_uploads_event = {
            'httpMethod': 'GET',
            'pathParameters': None,
            'queryStringParameters': {'limit': '10'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'arn:aws:iam::123456789012:user/test-user',
                        'cognito:groups': ['admin'],
                        'email': 'test-user@example.com'
                    }
                }
            }
        }
        
        # Lambda context
        self.context = test_common_utils.LambdaContextLogStream('test-log-stream')

        # Define POST validation test cases
        self.post_validation_test_cases = [
            {
                "name": "invalid filename characters",
                "body": {
                    'filename': "test[2].json",
                    'updated_schemas': ['application', 'server'],
                    'file_size': 1000,
                    'total_entities': 100,
                    'data_source_id': 'test-source'
                },
                "expected_error": "File name must start with a letter or number and can only contain letters, numbers, spaces, and these symbols: . - _ , ( )"
            },
            {
                "name": "filename not starting with alphanumeric",
                "body": {
                    'filename': "-test.json",
                    'updated_schemas': ['application', 'server'],
                    'file_size': 1000,
                    'total_entities': 100,
                    'data_source_id': 'test-source'
                },
                "expected_error": "File name must start with a letter or number and can only contain letters, numbers, spaces, and these symbols: . - _ , ( )"
            },
            {
                "name": "filename too long",
                "body": {
                    'filename': "a" + "very" * 30 + " long file name.json",
                    'updated_schemas': ['application', 'server'],
                    'file_size': 1000,
                    'total_entities': 100,
                    'data_source_id': 'test-source'
                },
                "expected_error": "File name cannot be longer than 100 characters"
            },
            {
                "name": "file size too large",
                "body": {
                    'filename': "test.json",
                    'updated_schemas': ['application', 'server'],
                    'file_size': 50*1000*1000+1,
                    'total_entities': 100,
                    'data_source_id': 'test-source'
                },
                "expected_error": "File size cannot be more than 50000000 bytes"
            },
            {
                "name": "too many entities",
                "body": {
                    'filename': "test.json",
                    'updated_schemas': ['application', 'server'],
                    'file_size': 1000,
                    'total_entities': 100*1000+1,
                    'data_source_id': 'test-source'
                },
                "expected_error": "Total entities to be imported cannot be more than 100000"
            },
            {
                "name": "zero entity",
                "body": {
                    'filename': "test.json",
                    'updated_schemas': ['application', 'server'],
                    'file_size': 1000,
                    'total_entities': 0,
                    'data_source_id': 'test-source'
                },
                "expected_error": "File should contain at least 1 entity"
            },
        ]

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.s3_client')
    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_success(self, mock_auth_class, mock_s3_client, mock_repository):
        """Test successful POST upload request"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
        mock_repository.create_upload_record.return_value = {
            'upload_id': 'test-upload-id',
            'filename': 'test-data.json',
            'status': 'pending',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        lambda_upload_data_entities.s3_client = mock_s3_client
        
        result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertIn('id', response_body)
        self.assertIn('presigned_url', response_body)
        self.assertIn('s3_object_metadata', response_body)
        self.assertIn('expires_at', response_body)
        
        # Verify mocks were called
        # Should be called twice (once for each schema: 'application', 'server')
        self.assertEqual(mock_auth.get_user_resource_creation_policy.call_count, 2)
        mock_s3_client.generate_presigned_url.assert_called_once()
        mock_repository.create_upload_record.assert_called_once()

    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_validation_error(self, mock_auth_class):
        """Test POST upload validation error scenario 1"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
                
        # Import and test
        import lambda_upload_data_entities

        # Test each case
        for test_case in self.post_validation_test_cases:
            with self.subTest(name=test_case["name"]):
                # Prepare event
                self.post_event["body"] = json.dumps(test_case["body"])
                
                # Execute
                result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
                
                # Assert
                self.assertEqual(result['statusCode'], 400, f"Failed on: {test_case['name']}")
                response_body = json.loads(result['body'])
                self.assertEqual(
                    response_body['errors'], 
                    [test_case["expected_error"]], 
                    f"Failed on: {test_case['name']}"
                )

    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_access_denied(self, mock_auth_class):
        """Test POST upload with access denied"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_deny()
        mock_auth_class.return_value = mock_auth
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 403)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Access denied'])
        
        # Should be called once (fails on first schema)
        mock_auth.get_user_resource_creation_policy.assert_called_once()

    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_invalid_json(self, mock_auth_class):
        """Test POST upload with invalid JSON body"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        # Create event with invalid JSON
        invalid_event = self.post_event.copy()
        invalid_event['body'] = 'invalid json'
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(invalid_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 400)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Invalid JSON in request body'])

    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_missing_schemas(self, mock_auth_class):
        """Test POST upload with missing updated_schemas"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        # Create event without updated_schemas
        missing_schemas_event = {
            'httpMethod': 'POST',
            'pathParameters': None,
            'body': json.dumps({
                'filename': 'test-data.json',
                'updated_schemas': [],
                'file_size': 1024,
                'total_entities': 100,
                'data_source_id': 'test-source'
            }),
            'requestContext': self.post_event['requestContext']
        }
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(missing_schemas_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 400)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['data.updated_schemas must contain at least 1 items'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.s3_client')
    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_s3_error(self, mock_auth_class, mock_s3_client, mock_repository):
        """Test POST upload with S3 error"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        mock_s3_client.generate_presigned_url.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GeneratePresignedUrl'
        )
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        lambda_upload_data_entities.s3_client = mock_s3_client
        
        result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_get_upload_success(self, mock_auth_class, mock_repository):
        """Test successful GET upload status request"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.get_upload_record.return_value = {
            'upload_id': 'test-upload-id',
            'filename': 'test.json',
            'status': 'complete',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.get_upload_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertEqual(response_body['id'], 'test-upload-id')
        self.assertEqual(response_body['status'], 'complete')
        
        # Verify mocks were called
        mock_auth.get_user_policy.assert_called_once()
        mock_repository.get_upload_record.assert_called_once_with('test-upload-id')

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    @patch('helpers.s3_client')
    def test_get_upload_success_with_results_location(self, mock_s3_client, mock_auth_class, mock_repository):
        """Test successful GET upload status request with results_location pre-signed URL"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.get_upload_record.return_value = {
            'upload_id': 'test-upload-id',
            'filename': 'test.json',
            'status': 'complete',
            'created_at': '2024-01-15T10:00:00Z',
            'updated_at': '2024-01-15T10:00:00Z',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
            'results_location': 's3://test-bucket/results/batch1/data.json'
        }
        
        mock_s3_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/results/batch1/data.json?signature=test'
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.get_upload_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertEqual(response_body['id'], 'test-upload-id')
        self.assertEqual(response_body['status'], 'complete')
        self.assertEqual(response_body['results_url'], 'https://test-bucket.s3.amazonaws.com/results/batch1/data.json?signature=test')
        
        # Verify mocks were called
        mock_auth.get_user_policy.assert_called_once()
        mock_repository.get_upload_record.assert_called_once_with('test-upload-id')
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "results/batch1/data.json"
            },
            ExpiresIn=60
        )

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_get_upload_not_found(self, mock_auth_class, mock_repository):
        """Test GET upload status for non-existent upload"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.get_upload_record.return_value = None
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.get_upload_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 404)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Not found'])

    def test_unsupported_http_method(self):
        """Test unsupported HTTP method"""
        # Create event with unsupported method
        unsupported_event = {
            'httpMethod': 'DELETE',
            'pathParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'cognito:username': 'arn:aws:iam::123456789012:user/test-user',
                        'cognito:groups': ['admin'],
                        'email': 'test-user@example.com'
                    }
                }
            }
        }
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(unsupported_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 400)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Method not allowed'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.s3_client')
    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_repository_failure(self, mock_auth_class, mock_s3_client, mock_repository):
        """Test POST upload with repository failure"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
        mock_repository.create_upload_record.side_effect = Exception('Database error')
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        lambda_upload_data_entities.s3_client = mock_s3_client
        
        result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])

    @patch('lambda_upload_data_entities.ULID')
    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.s3_client')
    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_s3_key_generation(self, mock_auth_class, mock_s3_client, mock_repository, mock_ulid):
        """Test S3 key generation with date partitioning"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
        mock_repository.create_upload_record.return_value = {
            'upload_id': 'test-ulid-1234',
            'status': 'pending',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'filename': 'test-data.json',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
        }
        
        test_ulid = 'test-ulid-1234'
        mock_ulid.return_value = test_ulid
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        lambda_upload_data_entities.s3_client = mock_s3_client
        
        with patch('lambda_upload_data_entities.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 30, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        # The S3 key should be in the format uploads/YYYY/MM/DD/ULID
        self.assertTrue(response_body['id'].startswith('test-ulid'))

    @patch('lambda_upload_data_entities.MFAuth')
    def test_post_upload_missing_user_context(self, mock_auth_class):
        """Test POST upload with missing user context in auth response"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = {
            'action': 'allow'
            # Missing 'user' key
        }
        mock_auth_class.return_value = mock_auth
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])
        
        # Should be called twice (once for each schema) before failing
        self.assertEqual(mock_auth.get_user_resource_creation_policy.call_count, 2)

    # ===== LIST UPLOADS VALIDATION TESTS =====

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_success(self, mock_auth_class, mock_repository):
        """Test successful list uploads request"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.list_uploads.return_value = {
            'items': [
                {
                    'upload_id': 'test-upload-1',
                    'status': 'complete',
                    'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
                    'filename': 'test.json',
                    'file_size': 1024,
                    'total_entities': 100,
                    'data_source_id': 'test-source',
                    '_history': mock_audit_history(),
                }
            ],
            'count': 1
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertIn('items', response_body)
        self.assertIn('count', response_body)
        self.assertEqual(response_body['count'], 1)

    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_missing_user_context(self, mock_auth_class):
        """Test list uploads with missing user context"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_no_user()
        mock_auth_class.return_value = mock_auth
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 401)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Access denied'])

    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_invalid_user_ref(self, mock_auth_class):
        """Test list uploads with invalid user reference"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = (
            ['policy1'],
            {'email': 'test@example.com'}  # Missing userRef
        )
        mock_auth_class.return_value = mock_auth
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 401)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Access denied'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_invalid_pagination_token(self, mock_auth_class, mock_repository):
        """Test list uploads with invalid pagination token"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        # Create event with invalid pagination token
        invalid_event = {
            'httpMethod': 'GET',
            'pathParameters': None,
            'queryStringParameters': {'limit': '10', 'next_token': 'invalid-token'},
            'requestContext': self.list_uploads_event['requestContext']
        }
        
        # Import and test
        import lambda_upload_data_entities
        
        result = lambda_upload_data_entities.lambda_handler(invalid_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 400)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Invalid pagination token'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_repository_error(self, mock_auth_class, mock_repository):
        """Test list uploads with repository error"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.list_uploads.side_effect = Exception('Database error')
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_invalid_repository_response(self, mock_auth_class, mock_repository):
        """Test list uploads with invalid repository response"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        # Return invalid response (not a dict)
        mock_repository.list_uploads.return_value = "invalid response"
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_missing_required_fields(self, mock_auth_class, mock_repository):
        """Test list uploads with missing required fields in repository response"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        # Return response missing required fields
        mock_repository.list_uploads.return_value = {
            'items': [],
            # Missing 'count'
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_with_limit(self, mock_auth_class, mock_repository):
        """Test list uploads with custom limit"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.list_uploads.return_value = {
            'items': [
                {
                    'upload_id': 'test-upload-1',
                    'status': 'complete',
                    'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
                    'filename': 'test.json',
                    'file_size': 1024,
                    'total_entities': 100,
                    'data_source_id': 'test-source',
                    '_history': mock_audit_history(),
                }
            ],
            'count': 1
        }
        
        # Create event with custom limit
        valid_event = {
            'httpMethod': 'GET',
            'pathParameters': None,
            'queryStringParameters': {
                'limit': '25'
            },
            'requestContext': self.list_uploads_event['requestContext']
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(valid_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertIn('items', response_body)
        self.assertEqual(response_body['count'], 1)
        
        # Verify repository was called with correct limit
        mock_repository.list_uploads.assert_called_once()
        call_args = mock_repository.list_uploads.call_args
        self.assertEqual(call_args.kwargs['limit'], 25)

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_with_pagination_token(self, mock_auth_class, mock_repository):
        """Test list uploads with valid pagination token"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.list_uploads.return_value = {
            'items': [
                {
                    'upload_id': 'test-upload-1',
                    'status': 'complete',
                    'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
                    'filename': 'test.json',
                    'file_size': 1024,
                    'total_entities': 100,
                    'data_source_id': 'test-source',
                    '_history': mock_audit_history(),
                }
            ],
            'count': 1,
            'last_evaluated_key': {'upload_id': 'test-upload-1'}
        }
        
        # Create valid pagination token
        import base64
        import json
        token_data = json.dumps({'upload_id': 'previous-upload'})
        valid_token = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')
        
        # Create event with valid pagination token
        valid_event = {
            'httpMethod': 'GET',
            'pathParameters': None,
            'queryStringParameters': {'limit': '10', 'next_token': valid_token},
            'requestContext': self.list_uploads_event['requestContext']
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(valid_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertIn('items', response_body)
        self.assertIn('next_token', response_body)  # Should have next token since last_evaluated_key exists

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_invalid_uploads_type(self, mock_auth_class, mock_repository):
        """Test list uploads with invalid uploads type in repository response"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        # Return response with invalid items type
        mock_repository.list_uploads.return_value = {
            'items': 'not a list',  # Should be a list
            'count': 0
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 500)
        response_body = json.loads(result['body'])
        self.assertIn('errors', response_body)
        self.assertEqual(response_body['errors'], ['Internal server error'])

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.MFAuth')
    def test_list_uploads_basic_functionality(self, mock_auth_class, mock_repository):
        """Test basic list uploads functionality"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_policy.return_value = mock_get_user_policy_success()
        mock_auth_class.return_value = mock_auth
        
        mock_repository.list_uploads.return_value = {
            'items': [],
            'count': 0
        }
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        
        result = lambda_upload_data_entities.lambda_handler(self.list_uploads_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        response_body = json.loads(result['body'])
        self.assertIn('items', response_body)
        self.assertIn('count', response_body)
        self.assertEqual(response_body['count'], 0)

    @patch('lambda_upload_data_entities.repository', new_callable=lambda: MagicMock())
    @patch('lambda_upload_data_entities.s3_client')
    @patch('lambda_upload_data_entities.MFAuth')
    @patch('lambda_upload_data_entities.datetime')
    def test_post_upload_record_ttl_is_unix_timestamp(self, mock_datetime, mock_auth_class, mock_s3_client, mock_repository):
        """Test that record_ttl is stored as Unix timestamp for DynamoDB TTL compatibility"""
        # Setup mocks
        mock_auth = MagicMock()
        mock_auth.get_user_resource_creation_policy.return_value = mock_get_mf_auth_policy_allow()
        mock_auth_class.return_value = mock_auth
        
        mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
        mock_repository.create_upload_record.return_value = {
            'upload_id': 'test-upload-id',
            'filename': 'test-data.json',
            'status': 'pending',
            'uploaded_by': 'arn:aws:iam::123456789012:user/test-user',
            'file_size': 1024,
            'total_entities': 100,
            'data_source_id': 'test-source',
            '_history': mock_audit_history(),
        }
        
        # Mock datetime to return a specific time
        mock_now = datetime(2024, 1, 15, 10, 30, 0)
        mock_datetime.utcnow.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Calculate expected TTL timestamp (5 hours from now)
        expected_ttl_datetime = mock_now + timedelta(seconds=60*60*5)
        expected_ttl_timestamp = int(expected_ttl_datetime.timestamp())
        
        # Import and test
        import lambda_upload_data_entities
        lambda_upload_data_entities.repository = mock_repository
        lambda_upload_data_entities.s3_client = mock_s3_client
        
        result = lambda_upload_data_entities.lambda_handler(self.post_event, self.context)
        
        # Assertions
        self.assertEqual(result['statusCode'], 200)
        
        # Verify that create_upload_record was called with the correct record_ttl
        mock_repository.create_upload_record.assert_called_once()
        call_args = mock_repository.create_upload_record.call_args
        upload_metadata = call_args[0][0]  # First argument is upload_metadata
        
        # Verify record_ttl is present and is an integer (Unix timestamp)
        self.assertIn('record_ttl', upload_metadata)
        self.assertIsInstance(upload_metadata['record_ttl'], int)
        
        # Verify the timestamp is approximately correct (within 1 second tolerance)
        actual_ttl = upload_metadata['record_ttl']
        self.assertAlmostEqual(actual_ttl, expected_ttl_timestamp, delta=1)
        
        # Verify it's a future timestamp (greater than current time)
        current_timestamp = int(mock_now.timestamp())
        self.assertGreater(actual_ttl, current_timestamp)
        
        # Verify it's approximately 5 hours in the future
        time_diff = actual_ttl - current_timestamp
        expected_diff = 5 * 60 * 60  # 5 hours in seconds
        self.assertAlmostEqual(time_diff, expected_diff, delta=1)

