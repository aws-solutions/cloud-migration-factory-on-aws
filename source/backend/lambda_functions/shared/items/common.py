#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
from datetime import datetime, timezone
from policy import MFAuth
from typing import Any
from decimal import Decimal

from cmf_logger import logger
import cmf_boto
from cmf_utils import default_http_headers, convert_floats_to_decimal

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)
schema_table = cmf_boto.resource('dynamodb').Table(schema_table_name)

# Upload tracking table. The authoritative, server-verified Cognito authorizer
# context for an S3 import is persisted here by the Cognito-authenticated upload
# Lambda (lambda_upload_data_entities). It is the only trusted source of identity
# for the IAM/S3 bulk-import path.
upload_table_name = '{}-{}-upload-entities-metadata'.format(application, environment)
upload_table = cmf_boto.resource('dynamodb').Table(upload_table_name)

PREFIX_INVOCATION = 'Invocation:'


def get_schema_info(event):
    """
    Extract and validate schema information from API Gateway event.
    
    Validates that the schema exists in the schema table and returns
    the schema configuration along with logging context.
    
    Args:
        event: API Gateway event with pathParameters containing 'schema'
        
    Returns:
        tuple: (schema_name, schema_config, logging_context)
               If error, schema_config contains error response dict
    """
    if 'schema' not in event['pathParameters']:
        return None, create_error_response(400, 'No schema provided to function.'), ''
    
    schema_name = event['pathParameters']['schema']
    logging_context = f"{schema_name}:{event['httpMethod']}"
    logger.debug(f'{PREFIX_INVOCATION} {logging_context}')
    
    schema = find_schema(schema_name)
    if not schema:
        msg = f'Invalid schema provided :{schema_name}'
        logger.error(msg)
        return schema_name, create_error_response(400, msg), logging_context
    
    return schema_name, schema, logging_context


def find_schema(schema_name):
    """
    Find schema configuration by name in the schema DynamoDB table.
    
    Queries the schema table using schema_name as the hash key and returns
    the complete schema configuration including attributes, validation rules,
    and schema type (user/custom).
    
    Args:
        schema_name: Name of the schema to find (e.g., 'app', 'server', 'wave')
        
    Returns:
        dict: Schema configuration if found, None otherwise
    """
    try:
        response = schema_table.get_item(Key={'schema_name': schema_name})
        return response.get('Item')
    except Exception as e:
        logger.error(f'Error querying schema table for {schema_name}: {str(e)}')
        return None


def get_data_table(schema_name, schema_type):
    """
    Get the appropriate DynamoDB table resource for the schema.
    
    Custom schemas use a shared 'custom-assets' table with sharding,
    while standard schemas use dedicated tables named after the schema.
    
    Args:
        schema_name: Name of the schema (e.g., 'app', 'server')
        schema_type: Type of schema ('custom' or 'user')
        
    Returns:
        boto3.resource.Table: DynamoDB table resource
    """
    if schema_type == 'custom':
        table_name = f'{application}-{environment}-custom-assets'
    else:
        table_name = f'{application}-{environment}-{schema_name}s'
    return cmf_boto.resource('dynamodb').Table(table_name)


def is_iam_request(event):
    """
    Determine if the request is IAM-authenticated vs Cognito-authenticated.
    
    IAM requests come from other AWS services (like S3-triggered Lambda functions)
    and set the userArn in the identity context. These requests use a different
    payload format for bulk operations.
    
    Args:
        event: API Gateway event
        
    Returns:
        bool: True if IAM request, False if Cognito request
    """
    return (event.get('requestContext', {}).get('identity', {}).get('userArn') is not None)


def create_error_response(status_code, message):
    """
    Create standardized HTTP error response with CORS headers.
    
    Args:
        status_code: HTTP status code (400, 401, 500, etc.)
        message: Error message string or object
        
    Returns:
        dict: HTTP response with headers, statusCode, and body
    """
    return {
        'headers': {**default_http_headers},
        'statusCode': status_code,
        'body': message if isinstance(message, str) else json.dumps({'errors': [message]})
    }


def parse_json_body(event, logging_context):
    """
    Parse and validate JSON body from API Gateway event.
    
    Args:
        event: API Gateway event with 'body' field
        logging_context: Context string for logging
        
    Returns:
        dict: Parsed JSON object, or error response dict if invalid
    """
    try:
        return json.loads(event['body'])
    except Exception as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context} {str(e)}')
        return create_error_response(400, json.dumps({'errors': ['malformed json input']}))


def validate_s3_format(body):
    """
    Validate that the request body has the expected S3 import format.
    
    S3 import requests must have 'upload_id' and 'data' fields where 'data'
    contains the array of items to create/update. The caller-supplied body must
    NOT carry identity/claims (auth_info) - those are resolved server-side from
    the trusted upload tracking record via resolve_verified_auth_info().

    Args:
        body: Parsed JSON body

    Returns:
        bool: True if valid S3 format, False otherwise
    """
    return (isinstance(body, dict)
            and isinstance(body.get('upload_id'), str) and body['upload_id']
            and 'data' in body)


def resolve_verified_auth_info(upload_id, logging_context):
    """
    Resolve the server-verified Cognito authorizer context for an S3 import.

    The identity used to authorise a bulk import is read from the trusted upload
    tracking table (written only by the Cognito-authenticated upload Lambda),
    keyed by the upload_id reference supplied in the request body. This prevents
    callers of the IAM/S3 import path from supplying (spoofing) their own claims
    in the request body (CWE-290 / CWE-287 / CWE-639).

    Args:
        upload_id: The upload tracking id referenced by the import request
        logging_context: Context string for logging

    Returns:
        dict: The stored authorizer context ({'claims': {...}}) if found and
              well-formed, otherwise None.
    """
    if not upload_id or not isinstance(upload_id, str):
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Missing or invalid upload_id for S3 import')
        return None

    try:
        response = upload_table.get_item(Key={'upload_id': upload_id})
    except Exception as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Error reading upload record {upload_id}: {str(e)}')
        return None

    record = response.get('Item')
    if not record:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Upload record not found for upload_id: {upload_id}')
        return None

    auth_info = record.get('auth_info')
    if not isinstance(auth_info, dict) or not auth_info.get('claims'):
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Upload record {upload_id} has no verified auth_info')
        return None

    return auth_info


def get_auth_response(event, schema_name):
    """
    Get authorization response for the authenticated user for updates.
    
    Checks if the user has permission to update items in the specified schema
    based on their Cognito groups and assigned policies.
    
    Args:
        event: API Gateway event with Cognito authorizer context
        schema_name: Name of the schema to check permissions for
        
    Returns:
        dict: Authorization response with 'action' and 'user' fields
    """
    auth = MFAuth()
    return auth.get_user_attribute_policy(event, schema_name)


def get_auth_response_for_creation(event, schema_name):
    """
    Get authorization response for the authenticated user for creation.
    
    Checks if the user has permission to create items in the specified schema
    based on their Cognito groups and assigned policies.
    
    Args:
        event: API Gateway event with Cognito authorizer context
        schema_name: Name of the schema to check permissions for
        
    Returns:
        dict: Authorization response with 'action' and 'user' fields
    """
    auth = MFAuth()
    return auth.get_user_resource_creation_policy(event, schema_name)


def get_auth_response_for_deletion(event, schema_name):
    """
    Get authorization response for the authenticated user for deletions.
    
    Checks if the user has permission to delete items in the specified schema
    based on their Cognito groups and assigned policies.
    
    Args:
        event: API Gateway event with Cognito authorizer context
        schema_name: Name of the schema to check permissions for
        
    Returns:
        dict: Authorization response with 'action' and 'user' fields
    """
    auth = MFAuth()
    return auth.get_user_resource_creation_policy(event, schema_name)


def create_auth_error_response(auth_response, logging_context):
    """
    Create HTTP 401 response for authorization failures.
    
    Args:
        auth_response: Authorization response from MFAuth
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP 401 response with error details
    """
    logger.error(f'{PREFIX_INVOCATION} {logging_context}, Authorisation failed: {json.dumps(auth_response)}')
    return create_error_response(401, json.dumps({'errors': [auth_response]}))


def update_audit_trail(updated_item, auth_response):
    """Update the audit trail for the item with modification details."""
    new_audit = {}
    
    # Add modification details if user info is available
    if 'user' in auth_response:
        new_audit['lastModifiedBy'] = auth_response['user']
        new_audit['lastModifiedTimestamp'] = datetime.now(timezone.utc).isoformat()

    # Preserve original creation details if they exist
    if '_history' in updated_item['Item']:
        old_audit = updated_item['Item']['_history']
        if 'createdTimestamp' in old_audit:
            new_audit['createdTimestamp'] = old_audit['createdTimestamp']
        if 'createdBy' in old_audit:
            new_audit['createdBy'] = old_audit['createdBy']

    updated_item['Item']['_history'] = new_audit


def create_audit_info(auth_response):
    """Create audit information for new items."""
    audit = {}
    if 'user' in auth_response:
        audit['createdBy'] = auth_response['user']
        audit['createdTimestamp'] = datetime.now(timezone.utc).isoformat()
    return audit


def normalize_to_list(body, logging_context):
    """Convert single item dict to list format for consistent processing."""
    if isinstance(body, dict):
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, DICT provided, converting to single item list.')
        return [body]
    return body





class JsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for DynamoDB data types.
    
    Handles conversion of DynamoDB-specific types that are not
    natively JSON serializable:
    - Decimal numbers (converted to strings)
    - Bytes objects (converted to UTF-8 strings)
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)