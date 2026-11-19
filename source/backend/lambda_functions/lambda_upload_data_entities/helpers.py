#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import boto3
import re
from botocore.exceptions import ClientError

try:
    from cmf_logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3')

# Default expiration time for pre-signed URLs (1 min)
DEFAULT_EXPIRATION_SECONDS = 60

def generate_presigned_url_from_s3_uri(s3_uri: str, expiration_seconds: int = DEFAULT_EXPIRATION_SECONDS) -> str:
    """
    Convert an S3 URI to a pre-signed URL for GET access.
    
    Args:
        s3_uri: S3 URI in format 's3://bucket/key'
        expiration_seconds: URL expiration time in seconds (default: 1 min)
        
    Returns:
        str: Pre-signed URL for accessing the S3 object
        
    Raises:
        ValueError: If S3 URI format is invalid
        ClientError: If S3 operation fails
    """
    # Parse S3 URI
    match = re.match(r'^s3://([^/]+)/(.+)$', s3_uri)
    if not match:
        raise ValueError(f"Invalid S3 URI format: {s3_uri}")
    
    bucket_name, object_key = match.groups()
    
    try:
        # Generate pre-signed URL for GET operation
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key
            },
            ExpiresIn=expiration_seconds
        )
        
        logger.info(f"Generated pre-signed URL for {s3_uri} (expires in {expiration_seconds}s)")
        return presigned_url
        
    except ClientError as e:
        logger.error(f"Failed to generate pre-signed URL for {s3_uri}: {str(e)}")
        raise

def convert_repoitem_to_job(record: dict) -> dict:
    """
    Convert a item from the repository into the expected item that the client is expecting
    
    Returns:
    {
        "id": "unique-upload-id",
        "status": "completed",
        "uploaded_by": "user12345",
        "filename": "data.csv",
        "file_size": 1024000,
        "total_entities": 10,
        "data_source_id": "123",
        "results_url": "https://pre-signed-url-to-results",
        "_history": 
        {
            "createdBy": 
            {
                "email": "serviceaccount@yourdomain.com",
                "userRef": "e9bec4f8-3061-708f-87a7-5d231c6eda1a"
            },
            "createdTimestamp": "2025-08-18T00:56:59.817819+00:00",
            "lastModifiedBy": 
            {
                "email": "serviceaccount@yourdomain.com",
                "userRef": "e9bec4f8-3061-708f-87a7-5d231c6eda1a"
            },
            "lastModifiedTimestamp": "2025-08-18T00:57:05.451673+00:00"
        }
    }
    """
    result = {
        "id": record.get("upload_id"),
        "status": record.get("status"),
        "uploaded_by": record.get("uploaded_by"),
        "filename": record.get("filename"),
        "file_size": int(record.get("file_size", 0)) if record.get("file_size") is not None else 0,
        "total_entities": int(record.get("total_entities", 0)) if record.get("total_entities") is not None else 0,
        "data_source_id": record.get("data_source_id"),
        "_history": record.get("_history"),
    }
    
    # Convert any results_location value into a pre-signed URL so the client can access
    if "results_location" in record:
        result["results_url"] = generate_presigned_url_from_s3_uri(record["results_location"])
    
    return result
