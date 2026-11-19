"""
Custom Exceptions for S3 Import Operations

This module defines specific exception types for different failure scenarios
in the S3 import workflow, providing better error handling and debugging.

Author: AWS Migration Factory Team
"""

class S3ImportError(Exception):
    """Base exception for S3 import operations"""
    pass

class ValidationError(S3ImportError):
    """Data validation failures during import processing"""
    pass

class APIError(S3ImportError):
    """API Gateway call failures"""
    def __init__(self, message, status_code=None, entity_type=None):
        super().__init__(message)
        self.status_code = status_code
        self.entity_type = entity_type

class DynamoDBError(S3ImportError):
    """DynamoDB operation failures"""
    pass

class S3OperationError(S3ImportError):
    """S3 read/write operation failures"""
    pass

class EntityProcessingError(S3ImportError):
    """Entity data processing and transformation failures"""
    pass
