#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
import boto3
import base64
import binascii
import re
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple
from botocore.exceptions import ClientError
from policy import MFAuth
from ulid import ULID
from aws_lambda_powertools.utilities.validation import SchemaValidationError, validate
from lambda_upload_data_entities_schemas import *
from helpers import convert_repoitem_to_job, DEFAULT_EXPIRATION_SECONDS

from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers
from repository import create_repository

class BadRequest(Exception):
    pass

class NotFound(Exception):
    pass

class Unauthorized(Exception):
    pass

class Forbidden(Exception):
    pass
class InternalError(Exception):
    pass

application = os.environ['application']
environment = os.environ['environment']

# Validate environment variables at module load
def validate_environment() -> None:
    required_vars = ["UPLOAD_ENTITIES_METADATA_TABLE_NAME", "UPLOAD_ENTITIES_BUCKET_NAME"]
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

# Call at module load
validate_environment()

# S3 bucket names from environment variables
s3_bucket_name = os.environ["UPLOAD_ENTITIES_BUCKET_NAME"]

# Initialize S3 client
s3_client = boto3.client('s3')

# Initialize repository
repository = create_repository()

def get_validator_and_handler(event: Any) -> tuple[callable, dict, dict, str]:
    """
    Determine the appropriate handler function & validator.

    Args:
        event: The Lambda event object

    Returns:
        tuple: (handler_function, input_schema, output_schema, envelope)

    Raises:
        BadRequest: If the HTTP method/path combination is not supported
    """
    http_method = event['httpMethod']
    path_parameters = event.get('pathParameters', {})

    if http_method == 'POST':
        return (
            post_upload,
            POST_ENTITIES_INPUT,
            POST_ENTITIES_OUTPUT,
            "powertools_json(body)"
        )
    elif http_method == 'GET' and path_parameters and 'id' in path_parameters:
        return (
            get_upload,
            GET_ENTITY_INPUT,
            GET_ENTITY_OUTPUT,
            None
        )
    elif http_method == 'GET' and not path_parameters:
        return (
            list_user_uploads,
            LIST_ENTITIES_INPUT,
            LIST_ENTITIES_OUTPUT,
            None
        )
    else:
        raise BadRequest("Method not allowed")

# 
POST_ENTITIES_INPUT_VALIDATION_ERROR_PATTERNS = {
    re.compile(r"data\.filename must match pattern"): 
        "File name must start with a letter or number and can only contain letters, numbers, spaces, and these symbols: . - _ , ( )",
    
    re.compile(r"data\.filename must be shorter than or equal to (\d+) characters"): 
        "File name cannot be longer than {value} characters",
        
    re.compile(r"data\.file_size must be smaller than or equal to (\d+)"): 
        "File size cannot be more than {value} bytes",
        
    re.compile(r"data\.file_size must be greater than or equal to (\d+)"): 
        "File cannot be empty",
    
    re.compile(r"data\.total_entities must be smaller than or equal to (\d+)"): 
        "Total entities to be imported cannot be more than {value}",
        
    re.compile(r"data\.total_entities must be bigger than or equal to (\d+)"): 
        "File should contain at least {value} entity",
}

def extract_threshold_value(validation_message: str, pattern: re.Pattern) -> Tuple[Optional[str], bool]:
    """Extract threshold value from validation message."""
    match = pattern.search(validation_message)
    if match:
        # Return the captured group if it exists, otherwise None, and True for match found
        return (match.group(1) if pattern.groups > 0 else None, True)
    return (None, False)

def get_friendly_validation_error(validation_message: str) -> str:
    """Map validation errors to friendly messages while preserving threshold values."""
    
    for pattern, message_template in POST_ENTITIES_INPUT_VALIDATION_ERROR_PATTERNS.items():
        threshold_value, pattern_matched = extract_threshold_value(validation_message, pattern)
        
        if pattern_matched:
            if "{value}" in message_template and threshold_value:
                return message_template.format(value=threshold_value)
            return message_template
            
    return validation_message

def lambda_handler(event: Any, context: Any):
    """
    Lambda handler for S3 upload operations.

    Supports:
    - POST /upload/data/entities: Generate pre-signed URL for JSON blob upload
    - GET /upload/data/entities/{id}: Get upload status and metadata
    - GET /upload/data/entities: List jobs submitted by the calling user
    """
    log_event_received(event)

    try:
        # Validate request and get appropriate handler
        handler_func, input_schema, output_schema, envelope = get_validator_and_handler(event)

        # Validate input
        if input_schema:
            validate(event=event, schema=input_schema, envelope=envelope)

        # Execute handler
        resp = handler_func(event, context)

        # Validate output
        if output_schema:
            try:
                validate(event=resp, schema=output_schema, envelope="powertools_json(body)")
            except SchemaValidationError as e:
                logger.error(f'output_schema validation failure in lambda_handler: {str(e.validation_message)}')
                raise InternalError("output_schema validation failure in lambda_handler")

        return resp

    except BadRequest as e:
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': json.dumps({'errors': [str(e)]})
        }
    except SchemaValidationError as e:
        logger.info(f'Validation error: {str(e)}')
        friendly_message = get_friendly_validation_error(e.validation_message)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': json.dumps({'errors': [friendly_message]})
        }
    except json.JSONDecodeError as e:
        logger.info(f'JSON decode error: {str(e)}')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': json.dumps({'errors': ['Invalid JSON in request body']})
        }
    except Unauthorized as e:
        return {
            'headers': {**default_http_headers},
            'statusCode': 401,
            'body': json.dumps({'errors': ['Access denied']})
            }
    except Forbidden as e:
        return {
            'headers': {**default_http_headers},
            'statusCode': 403,
            'body': json.dumps({'errors': ['Access denied']})
            }
    except NotFound as e:
        return {
            'headers': {**default_http_headers},
            'statusCode': 404,
            'body': json.dumps({'errors': ['Not found']})
            }
    except Exception as e:
        logger.error(f'Unexpected error in lambda_handler: {str(e)}')
        return {
            'headers': {**default_http_headers},
            'statusCode': 500,
            'body': json.dumps({'errors': ['Internal server error']})
        }


def post_upload(event: Any, context: Any) -> dict:
    """
    Create a new upload job. Returns a pre-signed URL for uploading a JSON blob to S3.

    Expected request body:
    {
        "updated_schemas": ["app", "server"],
        "file_size": 123;
        "total_entities": 5;
        "filename": "test-upload.csv";
        "data_source_id": "source-01";
    }

    Returns:
    {
        "id": "unique-upload-id",
        "status": "completed",
        "uploaded_by": "user12345",
        "filename": "data.csv",
        "file_size": 1024000,
        "total_entities": 10,
        "data_source_id": "123",
        "presigned_url": "https://s3.amazonaws.com/...",
        "expires_at": "2024-01-15T10:30:00Z",
        "s3_object_metadata": { ... },
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
    try:
        # Parse request body
        body_str = event.get('body', '{}')
        body = json.loads(body_str)

        # Get schemas which will be updated by this request
        updated_schemas = body.get('updated_schemas')
        if not updated_schemas or not isinstance(updated_schemas, list):
            raise BadRequest('updated_schemas must be a non-empty list')

        # Authenticate the request
        auth = MFAuth()
        auth_response = None

        # Check authorization for all schemas
        for schema in updated_schemas:
            auth_response = auth.get_user_resource_creation_policy(event, schema)
            if auth_response['action'] != 'allow':
                logger.warning(f'Access denied for user: {auth_response} for schema {schema}')
                raise Forbidden()

        # Ensure we passed auth
        if 'user' not in auth_response or 'userRef' not in auth_response['user']:
            raise InternalError("User context not found")

        # Generate unique upload ID
        upload_id = str(ULID())

        # Extract parameters with defaults and ensure they're integers
        file_size = int(body.get('file_size', 0))
        total_entities = int(body.get('total_entities', 0))
        filename = body.get('filename', "-")
        data_source_id = body.get('data_source_id', "-")

        # Generate S3 key with date-based partitioning
        now = datetime.utcnow()
        s3_key = f"uploads/{now.year:04d}/{now.month:02d}/{now.day:02d}/{upload_id}"

        # Prepare S3 metadata for presigned URL
        s3_object_metadata = {
            'upload-id': upload_id,
            'uploaded-by': auth_response['user']['userRef'],
            'upload-timestamp': now.isoformat(),
            'file-size': str(file_size),
            'filename': filename,
        }

        logger.info(f'Generating pre-signed URL for bucket: {s3_bucket_name}, key: {s3_key}')

        # Prepare parameters for presigned URL including metadata
        presigned_params = {
            "Bucket": s3_bucket_name,
            "Key": s3_key,
            "ContentType": 'application/json',
            "Metadata": s3_object_metadata
        }

        # Generate pre-signed URL for PUT operation with metadata
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params=presigned_params,
            ExpiresIn=DEFAULT_EXPIRATION_SECONDS
        )

        # Calculate expiration time
        expires_at = now + timedelta(seconds=DEFAULT_EXPIRATION_SECONDS)

        # Calculate time to live (ttl) to cleanup pending jobs which don't have a linked S3 file
        # Currently 5 hours - DynamoDB TTL requires Unix timestamp (seconds since epoch)
        record_ttl = int((now + timedelta(seconds=60*60*5)).timestamp())

        # Store upload metadata in DynamoDB for tracking
        upload_metadata = {
            'upload_id': upload_id,
            's3_bucket': s3_bucket_name,
            's3_key': s3_key,
            'status': 'pending',
            'uploaded_by': auth_response['user']['userRef'],
            'auth_info': event['requestContext']['authorizer'],
            'file_size': file_size,
            'total_entities': total_entities,
            'filename': filename,
            'data_source_id': data_source_id,
            'record_ttl': record_ttl
        }

        # Store in DynamoDB using repository
        repo_item = repository.create_upload_record(upload_metadata, auth_response)

        logger.info(f'Generated pre-signed URL for id: {upload_id}')

        resp = {
            'presigned_url': presigned_url,
            's3_object_metadata': s3_object_metadata,
            'expires_at': expires_at.isoformat(),
            **convert_repoitem_to_job(repo_item)
        }

        return {
            'headers': {**default_http_headers},
            'statusCode': 200,
            'body': json.dumps(resp)
        }

    except json.JSONDecodeError:
        raise BadRequest('Invalid JSON in request body')
    except ClientError as e:
        logger.error(f'Error generating pre-signed URL: {str(e)}')
        raise InternalError('Failed to generate pre-signed URL')


def get_upload(event: Any, context: Any) -> dict:
    """
    Get the status and metadata of an upload.

    Returns:
    {
        "id": "unique-upload-id",
        "status": "completed",
        "uploaded_by": "user12345",
        "filename": "data.csv",
        "file_size": 1024000,
        "total_entities": 10,
        "data_source_id": "123",
        "results_url": "pre-signed-url-containing-results",
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
    upload_id = event['pathParameters']['id']

    # Authenticate the request
    auth = MFAuth()
    user_policy_list, user = auth.get_user_policy(event)

    if 'userRef' not in user:
        raise Unauthorized("User context not found")

    # Get upload record from repository
    upload_data = repository.get_upload_record(upload_id)

    if not upload_data:
        raise NotFound('Upload not found')

    # Verify the authenticated user owns this upload
    if upload_data.get('uploaded_by') != user['userRef']:
        raise Forbidden('Access denied')

    logger.info(f'Retrieved upload status for id: {upload_id}')

    return {
        'headers': {**default_http_headers},
        'statusCode': 200,
        'body': json.dumps(convert_repoitem_to_job(upload_data), default=str)
    }


def list_user_uploads(event: Any, context: Any) -> dict:
    """
    List recent uploads for the authenticated user with pagination support.

    Query parameters:
    - limit: Number of uploads to return (default: 50, max: 100)
    - next_token: Pagination token for retrieving next page

    Returns:
    {
        "uploads": [
            {
                "id": "unique-upload-id",
                "status": "completed",
                "uploaded_by": "user12345",
                "filename": "data.csv",
                "file_size": 1024000,
                "total_entities": 10,
                "data_source_id": "123",
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
        ],
        "count": 25,
        "next_token": "eyJ1cGxvYWRfaWQiOiIuLi4ifQ=="
    }
    """
    # Authenticate the request
    auth = MFAuth()
    user_policy_list, user = auth.get_user_policy(event)

    if 'userRef' not in user:
        raise Unauthorized("User context not found")

    # Parse query parameters
    query_params = event.get('queryStringParameters') or {}
    limit = int(query_params.get('limit', 50))

    # Handle pagination token
    last_evaluated_key = None
    next_token = query_params.get('next_token')
    if next_token:
        try:
            decoded_token = base64.b64decode(next_token).decode('utf-8')
            last_evaluated_key = json.loads(decoded_token)
        except (ValueError, json.JSONDecodeError, base64.binascii.Error) as e:
            logger.info(f"Invalid pagination token: {str(e)}")
            raise BadRequest("Invalid pagination token")

    # Get uploads for the authenticated user only
    result = repository.list_uploads_by_user(
        user['userRef'],
        limit=limit,
        last_evaluated_key=last_evaluated_key
    )

    # Prepare response
    response_data = {
        'items': [convert_repoitem_to_job(item) for item in result['items']],
        'count': result['count'],
    }

    # Add next_token if there are more items
    if 'last_evaluated_key' in result:
        token_data = json.dumps(result['last_evaluated_key'], default=str)
        response_data['next_token'] = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')

    logger.info(f'Listed {result["count"]} uploads')

    return {
        'headers': {**default_http_headers},
        'statusCode': 200,
        'body': json.dumps(response_data, default=str)
    }