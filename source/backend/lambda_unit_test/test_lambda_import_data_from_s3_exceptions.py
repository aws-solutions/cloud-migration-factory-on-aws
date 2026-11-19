#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from test_common_utils import default_mock_os_environ

@mock.patch.dict('os.environ', default_mock_os_environ)
class S3ImportExceptionsTest(unittest.TestCase):

    def test_s3_import_error_base_exception(self):
        from s3_import_exceptions import S3ImportError
        
        error = S3ImportError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)

    def test_validation_error(self):
        from s3_import_exceptions import ValidationError, S3ImportError
        
        error = ValidationError("Validation failed")
        self.assertEqual(str(error), "Validation failed")
        self.assertIsInstance(error, S3ImportError)
        self.assertIsInstance(error, Exception)

    def test_api_error_basic(self):
        from s3_import_exceptions import APIError, S3ImportError
        
        error = APIError("API call failed")
        self.assertEqual(str(error), "API call failed")
        self.assertIsInstance(error, S3ImportError)
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.entity_type)

    def test_api_error_with_status_code(self):
        from s3_import_exceptions import APIError
        
        error = APIError("API call failed", status_code=500)
        self.assertEqual(str(error), "API call failed")
        self.assertEqual(error.status_code, 500)
        self.assertIsNone(error.entity_type)

    def test_api_error_with_entity_type(self):
        from s3_import_exceptions import APIError
        
        error = APIError("API call failed", entity_type="app")
        self.assertEqual(str(error), "API call failed")
        self.assertIsNone(error.status_code)
        self.assertEqual(error.entity_type, "app")

    def test_api_error_with_all_parameters(self):
        from s3_import_exceptions import APIError
        
        error = APIError("API call failed", status_code=400, entity_type="server")
        self.assertEqual(str(error), "API call failed")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.entity_type, "server")

    def test_dynamodb_error(self):
        from s3_import_exceptions import DynamoDBError, S3ImportError
        
        error = DynamoDBError("DynamoDB operation failed")
        self.assertEqual(str(error), "DynamoDB operation failed")
        self.assertIsInstance(error, S3ImportError)

    def test_s3_operation_error(self):
        from s3_import_exceptions import S3OperationError, S3ImportError
        
        error = S3OperationError("S3 operation failed")
        self.assertEqual(str(error), "S3 operation failed")
        self.assertIsInstance(error, S3ImportError)

    def test_entity_processing_error(self):
        from s3_import_exceptions import EntityProcessingError, S3ImportError
        
        error = EntityProcessingError("Entity processing failed")
        self.assertEqual(str(error), "Entity processing failed")
        self.assertIsInstance(error, S3ImportError)

    def test_exception_inheritance_chain(self):
        from s3_import_exceptions import (
            S3ImportError, ValidationError, APIError, DynamoDBError, 
            S3OperationError, EntityProcessingError
        )
        
        # Test that all custom exceptions inherit from S3ImportError
        exceptions = [
            ValidationError("test"),
            APIError("test"),
            DynamoDBError("test"),
            S3OperationError("test"),
            EntityProcessingError("test")
        ]
        
        for exception in exceptions:
            self.assertIsInstance(exception, S3ImportError)
            self.assertIsInstance(exception, Exception)

    def test_exception_can_be_raised_and_caught(self):
        from s3_import_exceptions import ValidationError, APIError
        
        # Test ValidationError
        with self.assertRaises(ValidationError) as context:
            raise ValidationError("Test validation error")
        self.assertEqual(str(context.exception), "Test validation error")
        
        # Test APIError
        with self.assertRaises(APIError) as context:
            raise APIError("Test API error", status_code=404, entity_type="wave")
        self.assertEqual(str(context.exception), "Test API error")
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.entity_type, "wave")

    def test_exception_can_be_caught_as_base_class(self):
        from s3_import_exceptions import S3ImportError, ValidationError, APIError
        
        # Test that specific exceptions can be caught as S3ImportError
        with self.assertRaises(S3ImportError):
            raise ValidationError("Test error")
        
        with self.assertRaises(S3ImportError):
            raise APIError("Test error")

if __name__ == '__main__':
    unittest.main()