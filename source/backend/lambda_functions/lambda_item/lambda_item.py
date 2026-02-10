#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import item_validation
import item_custom_assets
from typing import Any, List, Dict

from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers, convert_floats_to_decimal
from shared.items.common import (
    get_schema_info, get_data_table, is_iam_request, create_error_response,
    parse_json_body, validate_s3_format, get_auth_response, get_auth_response_for_deletion,
    create_auth_error_response, JsonEncoder, PREFIX_INVOCATION, update_audit_trail,
)

SUFFIX_DOESNT_EXIST = 'does not exist'

def route_request(event, data_table, schema, schema_name, logging_context):
    """
    Route Cognito-authenticated requests to appropriate handlers.
    
    Supports:
    - GET: Retrieve single item by ID
    - PUT: Update single item
    - DELETE: Delete single item
    
    Args:
        event: API Gateway event
        data_table: DynamoDB table resource
        schema: Schema configuration
        schema_name: Name of the schema
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response
    """
    method = event['httpMethod']
    if method == 'GET':
        return handle_get_single_item_request(event, data_table, schema_name, schema['schema_type'], logging_context)
    elif method == 'PUT':
        return handle_put_item_request(event, data_table, schema_name, schema, logging_context)
    elif method == 'DELETE':
        return handle_delete_item_request(event, data_table, schema_name, schema['schema_type'], logging_context)
    else:
        return create_error_response(405, 'Method not allowed')

def determine_dynamodb_key_structure(schema_name: str, schema_type: str):
    """
    Get partition key and sort key names for schemas.
    
    Args:
        schema_name: The schema name (e.g., 'rule', 'app', 'server', 'storage', etc.)
        
    Returns:
        tuple: (partition_key_name, sort_key_name) where sort_key_name is None for single-key schemas
    """
    if schema_name == 'rule':
        return ('rule_type', 'rule_id')
    elif schema_type == 'custom':  # Add other composite key schemas here
        return ('asset_type#shard', 'asset_id')
    else:
        # For standard single-key schemas
        return (schema_name + '_id', None)

class MissingTypeParameterError(Exception):
    """Raised when composite key schema is missing required type parameter"""
    pass

def construct_dynamodb_key_from_event(event: Any, schema_name: str, schema_type: str):
    """
    Build DynamoDB key for item operations with validation.
    
    Args:
        event: Lambda event object
        schema_name: Schema name
        schema_type: Schema type
        
    Returns:
        dict: DynamoDB key
        
    Raises:
        MissingTypeParameterError: When composite key schema is missing type parameter
    """
    partition_key, sort_key = determine_dynamodb_key_structure(schema_name, schema_type)
    query_params = event.get('queryStringParameters')
    item_id = event['pathParameters']['id']
    
    # Handle different key structures based on schema type
    if sort_key is not None and schema_type == 'custom':
        # For custom assets, calculate the shard number from the ID
        shard_number = item_custom_assets.get_shard_number(item_id)
        return {partition_key: f"{schema_name}#{shard_number}", sort_key: item_id}
    elif sort_key is not None and query_params and 'type' in query_params:
        # Composite key schema with type parameter, e.g. rule
        return {partition_key: query_params['type'], sort_key: event['pathParameters']['id']}
    elif sort_key is not None:
        # Composite key schema missing required type parameter
        raise MissingTypeParameterError(f'Missing required type parameter for {schema_name} schema')
    else:
        # Single key schema
        return {partition_key: event['pathParameters']['id']}

def lambda_handler(event, _):
    """
    Main Lambda handler for single item operations (GET/PUT/DELETE) on various schemas.
    
    Handles both Cognito-authenticated and IAM-authenticated requests:
    - Cognito: Standard API requests from frontend
    - IAM: S3 import requests for bulk updates
    
    Example API requests:
    GET /prod/{schema}/{id} - Get single item by ID
    PUT /prod/{schema}/{id} - Update single item
    DELETE /prod/{schema}/{id} - Delete single item
    
    Args:
        event: Lambda event containing HTTP method, path parameters, and body
        _: Lambda context (unused)
        
    Returns:
        dict: HTTP response with headers, statusCode, and body
    """
    log_event_received(event)
    
    schema_name, schema, logging_context = get_schema_info(event)
    if isinstance(schema, dict) and 'statusCode' in schema:
        return schema  # Error response
    
    data_table = get_data_table(schema_name, schema['schema_type'])
    
    if is_iam_request(event) and event['httpMethod'] == 'PUT':
        return handle_s3_bulk_import_request(event, data_table, schema_name, schema, logging_context)
    
    return route_request(event, data_table, schema, schema_name, logging_context)

def handle_get_single_item_request(event: Any, data_table: Any, schema_name: str, schema_type: str, logging_context: str):
    if 'id' in event['pathParameters']:
        return get_item_by_id(event, data_table, schema_name, schema_type, logging_context)

def get_item_by_id(event: Any, data_table: Any, schema_name: str, schema_type: str, logging_context: str):
    """Get a single item by its ID."""
    try:
        # Build the appropriate DynamoDB key for this schema
        key = construct_dynamodb_key_from_event(event, schema_name, schema_type)
    except MissingTypeParameterError as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {str(e)}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [str(e)]})}
    
    resp = data_table.get_item(Key=key)
    
    if 'Item' in resp:
        return {'headers': {**default_http_headers},
                'body': json.dumps(resp['Item'], cls=JsonEncoder)}
    else:
        msg = f'{schema_name} Id {event["pathParameters"]["id"]} {SUFFIX_DOESNT_EXIST}'
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

def handle_s3_bulk_import_request(event: Any, data_table: Any, schema_name: str, schema: Any, logging_context: str):
    """
    Handle IAM-authenticated PUT requests for S3 bulk import operations with bulk authorization.
    
    Uses all-or-nothing authorization by concatenating all attributes from all items
    and checking permissions once upfront for efficiency.
    
    Example API request:
    PUT /prod/app/123
    Authorization: AWS4-HMAC-SHA256 <iam-signature>
    {
        "user": "import-service",
        "data": [
            {"app_id": "123", "app_name": "UpdatedApp1", "description": "..."},
            {"app_id": "124", "app_name": "UpdatedApp2", "description": "..."}
        ]
    }
    
    Args:
        event: API Gateway event with IAM authentication
        data_table: DynamoDB table resource
        schema_name: Name of the schema
        schema: Schema configuration
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with update results and any errors
    """
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Processing IAM-authenticated S3 import PUT request')
    
    body = parse_json_body(event, logging_context)
    event['requestContext']['authorizer'] = body.get("auth_info", {})

    if isinstance(body, dict) and 'statusCode' in body:
        return body
    
    if not validate_s3_format(body):
        return create_error_response(400, json.dumps({'errors': ['Invalid S3 import format']}))
    
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Processing {len(body["data"])} items')
    
    # Perform bulk authorization check
    bulk_auth_event = create_bulk_auth_event(body['data'], schema_name, body.get("auth_info", {}))
    auth_response = get_auth_response(bulk_auth_event, schema_name)
    if auth_response['action'] != 'allow':
        return create_auth_error_response(auth_response, logging_context)
    
    # Process all items with pre-approved authorization
    results = []
    for item in body['data']:
        try:
            item_event = {
                'pathParameters': {'id': item[f'{schema_name}_id']},
                'body': json.dumps(item),
                'requestContext': {
                    'authorizer': body.get("auth_info", {})
                }
            }
            result = update_item_with_validation(item_event, data_table, schema_name, schema, auth_response, logging_context)
            results.append({'id': item[f'{schema_name}_id'], 'success': result.get('statusCode', 200) != 400})
        except Exception as e:
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, Error processing item {item.get(f"{schema_name}_id", "unknown")}: {str(e)}')
            results.append({'id': item.get(f'{schema_name}_id', 'unknown'), 'success': False, 'error': str(e)})
    
    return {'headers': {**default_http_headers},
            'statusCode': 200,
            'body': json.dumps({'results': results})}

def handle_put_item_request(event: Any, data_table: Any, schema_name: str, schema: Any, logging_context: str):
    """
    Handle Cognito-authenticated PUT requests to update single items.
    
    Example API request:
    PUT /prod/app/123
    Authorization: Bearer <cognito-token>
    {
        "app_name": "UpdatedAppName",
        "description": "Updated description",
        "tags": ["updated", "production"]
    }
    
    Response:
    {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "Attributes": {...}
    }
    
    Args:
        event: API Gateway event with Cognito authentication
        data_table: DynamoDB table resource
        schema_name: Name of the schema
        schema: Schema configuration
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with update result
    """
    auth_response = get_auth_response(event, schema_name)
    if auth_response['action'] != 'allow':
        return create_auth_error_response(auth_response, logging_context)
    
    return update_item_with_validation(event, data_table, schema_name, schema, auth_response, logging_context)

def update_item_with_validation(event: Any, data_table: Any, schema_name: str, schema: Any, auth_response: dict, logging_context: str):
    """Update an existing item with full validation and audit trail."""
    # Parse and validate the request body
    try:
        body = json.loads(event['body'])
        # Check if ID field is being modified and validate it matches path parameter
        id_field = schema_name + "_id"
        if id_field in body:
            path_id = event['pathParameters']['id']
            body_id = str(body[id_field])  # Convert to string for comparison
            if body_id != path_id:
                msg = f'The {id_field} in the request body ({body_id}) does not match the ID in the path parameter ({path_id})'
                logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
    except Exception as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {str(e)}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': ['malformed json input']})}

    # Get the existing item from DynamoDB
    try:
        key = construct_dynamodb_key_from_event(event, schema_name, schema['schema_type'])
    except MissingTypeParameterError as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {str(e)}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [str(e)]})}
    
    existing_item = data_table.get_item(Key=key)
    
    # Adapt custom asset items to schema format for processing
    schema_type = schema['schema_type']
    if 'Item' in existing_item:
        schema_adapted_existing_item = item_custom_assets.adapt_item_to_schema(
            existing_item['Item'], schema_name, schema_type
        )
        existing_item['Item'] = schema_adapted_existing_item
    
    # Validate item exists and check for naming conflicts
    validation_response = validate_item_exists_and_naming(existing_item, data_table, event, schema_name, schema_type, body, logging_context)
    if validation_response is not None:
        return validation_response

    # Merge new data with existing item
    updated_item = merge_item_updates(body, existing_item)
    
    # Validate the updated item against schema rules
    item_validation_result = item_validation.check_valid_item_create(updated_item['Item'], schema)
    if item_validation_result is not None:
        logger.error(f'Invocation: {logging_context}, Item validation failed: {json.dumps(item_validation_result)}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [item_validation_result]})}

    # Update audit trail
    update_audit_trail(updated_item, auth_response)
    
    # Ensure the item has the correct DynamoDB keys
    try:
        key = construct_dynamodb_key_from_event(event, schema_name, schema['schema_type'])
        updated_item['Item'].update(key)
    except MissingTypeParameterError as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {str(e)}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [str(e)]})}
    
    # Convert back to DynamoDB format and save
    updated_item['Item'] = item_custom_assets.revert_item_from_schema(
        updated_item['Item'], schema_name, schema['schema_type']
    )
    
    # Convert floats to Decimal for DynamoDB compatibility
    updated_item['Item'] = convert_floats_to_decimal(updated_item['Item'])
    
    resp = data_table.put_item(Item=updated_item['Item'])
    return {'headers': {**default_http_headers}, 'body': json.dumps(resp)}

def validate_item_exists_and_naming(existing_item: Any, data_table: Any, event: Any, schema_name: str, schema_type: str, body: Any, logging_context: str):
    """Validate that the item exists and check for naming conflicts."""
    # Check if the item exists
    if 'Item' not in existing_item:
        msg = f'{schema_name} Id: {event["pathParameters"]["id"]} {SUFFIX_DOESNT_EXIST}'
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

    # Check for name conflicts if name is being updated
    schema_name_key = schema_name + '_name'
    if schema_name_key in body:
        return check_name_uniqueness(data_table, body, event, schema_name, schema_type, logging_context)
    
    return None

def check_name_uniqueness(data_table: Any, body: Any, event: Any, schema_name: str, schema_type: str, logging_context: str):
    """Check if the new name conflicts with existing items."""
    name_value = str(body[schema_name + '_name'])
    current_id = str(event['pathParameters']['id'])
    
    # Determine the correct field names based on schema type
    schema_name_key = schema_name + '_name'
    schema_id_key = schema_name + '_id'
    if schema_type == 'custom':
        schema_name_key = 'asset_name'
        schema_id_key = 'asset_id'
    
    try:
        # Try to use NameIndex GSI for efficient lookup
        response = data_table.query(
            IndexName='NameIndex',
            KeyConditionExpression=Key(schema_name_key).eq(name_value)
        )
        
        # Check if any item with this name exists with a different ID
        for item in response.get('Items', []):
            if item.get(schema_id_key) != current_id:
                msg = f'{schema_name_key}: {name_value} already exist'
                logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
                        
    except Exception as e:
        # Fall back to table scan if GSI query fails
        logger.warning(f'{PREFIX_INVOCATION} {logging_context}, NameIndex GSI query failed, falling back to scan: {str(e)}')
        return check_name_uniqueness_with_scan(data_table, name_value, current_id, schema_name_key, schema_id_key, logging_context)
    
    return None

def check_name_uniqueness_with_scan(data_table: Any, name_value: str, current_id: str, schema_name_key: str, schema_id_key: str, logging_context: str):
    """Fallback method to check name uniqueness using table scan."""
    existing_data = item_validation.scan_dynamodb_data_table(data_table)
    for existing_item in existing_data:
        if schema_name_key in existing_item:
            if existing_item[schema_name_key] == name_value and existing_item[schema_id_key] != current_id:
                msg = f'{schema_name_key}: {name_value} already exist'
                logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
    return None

def merge_item_updates(body: Any, existing_item: Any):
    """Merge new attributes with existing item and clean up empty values."""
    # Merge new attributes with existing item
    for key in body.keys():
        existing_item['Item'][key] = body[key]
    
    updated_item = existing_item
    keys = list(updated_item['Item'].keys())

    # Remove empty string values and empty single-element lists
    for key in keys:
        value = updated_item['Item'][key]
        
        # Remove empty strings
        if value == '':
            del updated_item['Item'][key]
            continue
            
        # Remove lists that contain only an empty string
        if isinstance(value, list) and len(value) == 1 and value[0] == '':
            del updated_item['Item'][key]

    return updated_item

def format_delete_response(logging_context: str, delete_response: dict):
    """Format the response from a DynamoDB delete operation."""
    if delete_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info(f'{PREFIX_INVOCATION} {logging_context}, Item successfully deleted.')
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': "Item was successfully deleted."}
    else:
        logger.error(f'{PREFIX_INVOCATION}: {logging_context}, {json.dumps(delete_response)}')
        return {'headers': {**default_http_headers},
                'statusCode': delete_response['ResponseMetadata']['HTTPStatusCode'],
                'body': json.dumps({'errors': [delete_response]})}

def handle_delete_item_request(event: Any, data_table: Any, schema_name: str, schema_type: str, logging_context: str):
    """
    Handle DELETE requests to remove single items.
    
    Example API request:
    DELETE /prod/app/123
    Authorization: Bearer <cognito-token>
    
    Response (success):
    "Item was successfully deleted."
    
    Response (error):
    {"errors": ["Record has deletion protection flag enabled, and cannot be deleted."]}
    
    Args:
        event: API Gateway event with Cognito authentication
        data_table: DynamoDB table resource
        schema_name: Name of the schema
        schema_type: Type of schema ('custom' or 'user')
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with deletion result
    """
    auth_response = get_auth_response_for_deletion(event, schema_name)
    if auth_response['action'] != 'allow':
        return create_auth_error_response(auth_response, logging_context)
    
    # Build the DynamoDB key for the item to delete
    try:
        key = construct_dynamodb_key_from_event(event, schema_name, schema_type)
    except MissingTypeParameterError as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {str(e)}')
        return create_error_response(400, json.dumps({'errors': [str(e)]}))
    
    # Check if item exists before attempting deletion
    resp = data_table.get_item(Key=key)
    if 'Item' not in resp:
        msg = f'{schema_name} Id: {event["pathParameters"]["id"]} {SUFFIX_DOESNT_EXIST}'
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
        return create_error_response(400, json.dumps({'errors': [msg]}))
    
    # Attempt to delete the item (with deletion protection check)
    try:
        delete_response = data_table.delete_item(
            Key=key,
            ConditionExpression=Attr('deletion_protection').ne(True),
        )
        return format_delete_response(logging_context, delete_response)
        
    except ClientError as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {e}')
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            msg = 'Record has deletion protection flag enabled, and cannot be deleted.'
            return create_error_response(400, json.dumps({'errors': [msg]}))
        raise

def create_bulk_auth_event(items: List[Dict[str, Any]], schema_name: str, auth_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a mock event containing all attributes from all items for bulk authorization.
    
    Args:
        items: List of items being updated
        schema_name: Name of the schema
        auth_info: Authentication info
        
    Returns:
        dict: Mock event with concatenated attributes for authorization check
    """
    # Collect all unique attributes across all items
    all_attributes = set()
    for item in items:
        all_attributes.update(item.keys())
    
    # Create mock item with all possible attributes for authorization check
    mock_item = {attr: "bulk_check_value" for attr in all_attributes}
    
    return {
        'pathParameters': {'id': 'bulk_auth_check'},
        'body': json.dumps(mock_item),
        'requestContext': {
            'authorizer': auth_info
        }
    }

