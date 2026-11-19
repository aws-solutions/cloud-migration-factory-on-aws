"""
S3 Operations Module

This module handles all S3-related operations for the import data processor,
including metadata retrieval, file content operations, and results storage.

Author: AWS Migration Factory Team
"""

import json
from typing import Optional, Tuple
from cmf_logger import logger
import cmf_boto
from s3_import_exceptions import S3OperationError
from results import ProcessingResults

# Initialize S3 client for reuse
s3_client = cmf_boto.client('s3')

def get_upload_metadata(bucket_name: str, object_key: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieve upload metadata from S3 object metadata.
    """
    try:
        head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        metadata = head_response.get('Metadata', {})
        
        upload_id = metadata.get('upload-id')
        uploaded_by = metadata.get('uploaded-by')
        
        if not upload_id:
            logger.error(f"Critical: No upload-id found in metadata for {object_key}. Available metadata keys: {list(metadata.keys())}")
            return None, None
            
        logger.info(f"Retrieved metadata for {object_key}: upload_id={upload_id}, uploaded_by={uploaded_by}")
        return upload_id, uploaded_by
    except Exception as e:
        logger.error(f"Failed to get S3 metadata for {object_key}: {e}")
        raise

def get_s3_file_content(bucket_name: str, object_key: str) -> str:
    """
    Download and decode file content from S3.
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        _validate_file_size(object_key, response)
        
        file_content = response['Body'].read().decode('utf-8')
        _validate_file_content(object_key, file_content)
        
        logger.info(f"Retrieved file content: {len(file_content)} bytes from {object_key}")
        return file_content
    except UnicodeDecodeError as e:
        logger.error(f"File {object_key} is not valid UTF-8: {e}")
        raise S3OperationError(f"File {object_key} is not valid UTF-8: {e}") from e
    except S3OperationError:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve file content from {object_key}: {e}")
        raise S3OperationError(f"Failed to retrieve file content from {object_key}: {e}") from e

def _validate_file_size(object_key: str, response: dict) -> None:
    """Validate S3 object file size."""
    content_length = response.get('ContentLength', 0)
    
    if content_length == 0:
        raise S3OperationError(f"File {object_key} is empty")
    if content_length > 100 * 1024 * 1024:  # 100MB limit
        raise S3OperationError(f"File {object_key} is too large ({content_length} bytes)")

def _validate_file_content(object_key: str, file_content: str) -> None:
    """Validate file content is not empty."""
    if not file_content.strip():
        raise S3OperationError(f"File {object_key} contains no valid content")

def save_results_to_s3(bucket_name: str, upload_id: str, results: any, object_key: str) -> str:
    """
    Save processing results to S3.
    """
    try:
        results_filename = object_key.replace('uploads/', 'results/', 1)
        
        if not results:
            raise S3OperationError(f"Cannot save empty results for upload {upload_id}")
        
        results_content = _serialize_results(results, upload_id)
        _upload_results_to_s3(bucket_name, results_filename, results_content, upload_id)
        
        logger.info(f"Results saved to {results_filename} ({len(results_content)} bytes)")
        return f's3://{bucket_name}/{results_filename}'
    except S3OperationError:
        raise
    except Exception as e:
        logger.error(f"Failed to save results for upload {upload_id}: {e}")
        raise S3OperationError(f"Failed to save results for upload {upload_id}: {e}") from e

def _serialize_results(results: any, upload_id: str) -> str:
    """Serialize results object to JSON string."""
    results_content = json.dumps(
        results.__dict__, 
        indent=2, 
        default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o)
    )
    
    if not results_content or results_content == '{}':
        raise S3OperationError(f"Results serialization produced empty content for upload {upload_id}")
    
    return results_content

def _upload_results_to_s3(bucket_name: str, results_filename: str, 
                         results_content: str, upload_id: str) -> None:
    """Upload results content to S3."""
    s3_client.put_object(
        Bucket=bucket_name,
        Key=results_filename,
        Body=results_content,
        ContentType='application/json',
        Metadata={
            'upload-id': upload_id,
            'file-type': 'results'
        }
    )