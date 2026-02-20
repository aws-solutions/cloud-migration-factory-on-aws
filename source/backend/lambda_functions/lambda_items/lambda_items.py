#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from time import sleep
from boto3.dynamodb.types import TypeSerializer
from ulid import ULID
import uuid
import item_validation
import item_custom_assets
from typing import Any

import cmf_boto
from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers
from shared.items.common import (
    get_schema_info, get_data_table, is_iam_request, create_error_response,
    parse_json_body, validate_s3_format, get_auth_response_for_creation as get_auth_response,
    create_auth_error_response, JsonEncoder, PREFIX_INVOCATION, create_audit_info, normalize_to_list
)
from cmf_utils import convert_floats_to_decimal

client_ddb = cmf_boto.client('dynamodb')

def lambda_handler(event, _):
    """
    Main Lambda handler for items operations (GET/POST) on various schemas.
    
    Handles both Cognito-authenticated and IAM-authenticated requests:
    - Cognito: Standard API requests from frontend
    - IAM: S3 import requests from other Lambda functions
    
    Example API requests:
    GET /prod/{schema} - List all items in schema
    POST /prod/{schema} - Create new items in schema
    
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
    
    if is_iam_request(event):
        return process_s3_post(event, data_table, data_table.name, schema, schema_name, logging_context)
    
    return route_request(event, data_table, schema, schema_name, logging_context)

def route_request(event, data_table, schema, schema_name, logging_context):
    """
    Route Cognito-authenticated requests to appropriate handlers.
    
    Supports:
    - GET: Retrieve all items in schema
    - POST: Create new items in schema
    
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
        return process_get(data_table, schema, schema_name, logging_context)
    elif method == 'POST':
        return process_post(event, data_table, data_table.name, schema, schema_name, logging_context)
    else:
        return create_error_response(405, 'Method not allowed')
def slice_items_for_batch(items: list, start_indx: int, num_items: int):
    """
    Get a slice of items from list for batch processing.
    
    Args:
        items: List of items to slice
        start_indx: Starting index
        num_items: Number of items to retrieve
        
    Returns:
        list: Sliced list of items
    """
    # Calculate end index, ensuring we don't exceed list bounds
    end_indx = min(start_indx + num_items, len(items))
    return items[start_indx:end_indx]
def generate_next_numeric_id(data_table, schema_name):
    """
    Get next available incrementing ID for number-based schemas.
    
    Scans existing items to find the highest numeric ID and returns
    the next available ID. Used for schemas with key_type='number'.
    
    Args:
        data_table: DynamoDB table resource
        schema_name: Name of the schema (e.g., 'app', 'server')
        
    Returns:
        int: Next available ID (highest existing ID + 1)
    """
    existing_items = item_validation.scan_dynamodb_data_table(data_table)
    schema_id = f'{schema_name}_id'
    
    # Extract only valid numeric IDs from existing items
    # Filter out non-numeric values that might exist in the table
    ids = [int(item[schema_id]) for item in existing_items 
           if item.get(schema_id) and str(item[schema_id]).isdigit()]
    
    # Return next available ID (max + 1, or 1 if no IDs exist)
    return max(ids, default=0) + 1

def process_get(data_table: Any, schema: Any, schema_name: str, logging_context: str):
    """
    Handle GET requests to retrieve all items from a schema.
    
    Example API request:
    GET /prod/app
    Authorization: Bearer <cognito-token>
    
    Response:
    [
        {"app_id": "1", "app_name": "MyApp", "description": "..."},
        {"app_id": "2", "app_name": "OtherApp", "description": "..."}
    ]
    
    Args:
        data_table: DynamoDB table resource
        schema: Schema configuration dict
        schema_name: Name of the schema (e.g., 'app', 'server')
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with sorted list of items
    """
    logger.info(f'{PREFIX_INVOCATION} {logging_context} Received event is: GET')
    
    if schema['schema_type'] == 'custom':
        items = get_custom_schema_items(data_table, schema_name, schema['schema_type'])
    else:
        items = get_standard_schema_items(data_table, schema_name)
    
    return {'headers': {**default_http_headers}, 'body': json.dumps(items, cls=JsonEncoder)}

def get_custom_schema_items(data_table, schema_name, schema_type):
    """
    Retrieve and process items from custom schema tables.
    
    Custom schemas use a shared table with sharding. Items are queried
    across all shards and converted from DB format to API format.
    
    Args:
        data_table: DynamoDB custom-assets table
        schema_name: Name of the custom schema
        schema_type: Should be 'custom'
        
    Returns:
        list: Sorted list of items in API format
    """
    items = item_custom_assets.query_custom_assets(data_table, schema_name)
    converted_items = [item_custom_assets.adapt_item_to_schema(item, schema_name, schema_type) for item in items]
    return sorted(converted_items, key=lambda i: i.get(f"{schema_name}_name", ''))

def get_standard_schema_items(data_table, schema_name):
    """
    Retrieve and process items from standard schema tables.
    
    Standard schemas have dedicated tables. Items are scanned and
    returned in their native format.
    
    Args:
        data_table: DynamoDB table for the schema
        schema_name: Name of the schema
        
    Returns:
        list: Sorted list of items by schema_name_name field
    """
    items = item_validation.scan_dynamodb_data_table(data_table)
    return sorted(items, key=lambda i: i.get(f"{schema_name}_name", ''))

def process_s3_post(event: dict, data_table: Any, data_table_name: str, schema, schema_name: str, logging_context: str):
    """
    Handle IAM-authenticated POST requests for S3 bulk import operations.
    
    This is called when other Lambda functions (triggered by S3 events) need to
    create items in bulk. The request format is different from regular API calls.
    
    Example API request:
    POST /prod/app
    Authorization: AWS4-HMAC-SHA256 <iam-signature>
    {
        "user": "import-service",
        "data": [
            {"app_name": "ImportedApp1", "description": "..."},
            {"app_name": "ImportedApp2", "description": "..."}
        ]
    }
    
    Args:
        event: API Gateway event with IAM authentication
        data_table: DynamoDB table resource
        data_table_name: Name of the DynamoDB table
        schema: Schema configuration
        schema_name: Name of the schema
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with created items and any errors
    """
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Processing IAM-authenticated S3 import request')
    
    body = parse_json_body(event, logging_context)
    event['requestContext']['authorizer'] = body.get("auth_info", {})

    auth_response = get_auth_response(event, schema_name)
    if auth_response['action'] != 'allow':
        return create_auth_error_response(auth_response, logging_context)

    if isinstance(body, dict) and 'statusCode' in body:
        return body
    
    if not validate_s3_format(body):
        return create_error_response(400, json.dumps({'errors': ['Invalid S3 import format']}))
    
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Processing {len(body["data"])} items for user: {auth_response["user"]}')
    
    try:
        return process_authorized_post(body['data'], data_table, data_table_name, schema_name, schema, auth_response, logging_context)
    except Exception as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Error processing data: {str(e)}', exc_info=True)
        return create_error_response(500, json.dumps({'errors': [f'Error processing data: {str(e)}']}))

def process_post(event: dict, data_table: Any, data_table_name: str, schema, schema_name: str, logging_context: str):
    """
    Handle Cognito-authenticated POST requests to create new items.
    
    Example API request (single item):
    POST /prod/app
    Authorization: Bearer <cognito-token>
    {
        "app_name": "MyNewApp",
        "description": "Application description",
        "tags": ["web", "production"]
    }
    
    Example API request (multiple items):
    POST /prod/app
    Authorization: Bearer <cognito-token>
    [
        {"app_name": "App1", "description": "First app"},
        {"app_name": "App2", "description": "Second app"}
    ]
    
    Response:
    {
        "newItems": [
            {"app_id": "3", "app_name": "MyNewApp", "_history": {...}}
        ],
        "errors": {"duplicate_name": ["ExistingApp"]}  // if any errors
    }
    
    Args:
        event: API Gateway event with Cognito authentication
        data_table: DynamoDB table resource
        data_table_name: Name of the DynamoDB table
        schema: Schema configuration
        schema_name: Name of the schema
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with created items and any errors
    """
    auth_response = get_auth_response(event, schema_name)
    if auth_response['action'] != 'allow':
        return create_auth_error_response(auth_response, logging_context)
    
    body = parse_json_body(event, logging_context)
    if isinstance(body, dict) and 'statusCode' in body:
        return body
    
    body = normalize_to_list(body, logging_context)
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Starting PUT of {len(body)} items.')
    
    try:
        return process_authorized_post(body, data_table, data_table_name, schema_name, schema, auth_response, logging_context)
    except Exception as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Unhandled exception: {str(e)}', exc_info=True)
        return create_error_response(500, json.dumps({'errors': ['Unhandled API Exception: check logs for detailed error message.']}))
    
def process_authorized_post(body: dict, data_table: Any, data_table_name: str, schema_name: str, schema: dict, auth_response: dict, logging_context: str):
    """
    Process authorized POST request to create items after validation.
    
    This function handles the core logic for creating items:
    1. Validates payload structure and required fields
    2. Checks for duplicates and existing items
    3. Applies schema validation rules
    4. Sets system attributes (IDs, audit info, defaults)
    5. Saves items to DynamoDB in batches
    6. Returns results with any errors
    
    Args:
        body: List of items to create
        data_table: DynamoDB table resource
        data_table_name: Name of the DynamoDB table
        schema_name: Name of the schema
        schema: Schema configuration with validation rules
        auth_response: Authorization info with user details
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with newItems and errors
    """
    key_type = schema.get("key_type", "number")
    
    validation_response = validate_payload_structure(body, schema_name, key_type, logging_context)
    if validation_response:
        return validation_response
    
    new_audit = create_audit_info(auth_response)
    validated_items, errors = validate_items_and_collect_errors(body, schema_name, schema, key_type, data_table, new_audit)
    
    responses = save_items_to_db(validated_items, schema_name, schema['schema_type'], data_table_name, logging_context)
    
    has_errors, error_messages = check_all_errors(errors, responses, logging_context)
    return create_final_response(validated_items, error_messages, has_errors, logging_context)

def validate_payload_structure(body, schema_name, key_type, logging_context):
    """
    Validate basic structure and requirements of payload records.
    
    Checks that each record has the required name field and validates
    any provided ID fields based on the schema's key type.
    
    Args:
        body: List of items to validate
        schema_name: Name of the schema
        key_type: Type of primary key ('number' or 'ulid')
        logging_context: Context string for logging
        
    Returns:
        dict: Error response if validation fails, None if valid
    """
    for record in body:
        name_field = f'{schema_name}_name'
        if name_field not in record:
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, attribute {name_field} is required')
            return create_error_response(400, f'attribute {name_field} is required')
        
        id_error = validate_id_field(record, schema_name, key_type, logging_context)
        if id_error:
            return id_error
    return None

def validate_id_field(record, schema_name, key_type, logging_context):
    """
    Validate ID field in record if present.
    
    For 'number' key types, IDs are system-managed and cannot be provided.
    For 'ulid' key types, provided IDs must be valid ULID format.
    For 'uuid' key types, provided IDs must be valid UUID format.
    
    Args:
        record: Item record to validate
        schema_name: Name of the schema
        key_type: Type of primary key ('number', 'ulid', or 'uuid')
        logging_context: Context string for logging
        
    Returns:
        dict: Error response if validation fails, None if valid
    """
    id_field = f'{schema_name}_id'
    if id_field not in record:
        return None
    
    if key_type not in ["ulid", "uuid"]:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Cannot create {id_field}, managed by system')
        return create_error_response(400, f"You cannot create {id_field}, this is managed by the system")
    
    try:
        if key_type == "ulid":
            ULID.parse(record[id_field])
        else:  # uuid
            uuid.UUID(record[id_field])
        return None
    except (ValueError, TypeError):
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {id_field} must be a valid {key_type.upper()}')
        return create_error_response(400, f"{id_field} must be a valid {key_type.upper()}")
    
def validate_items_and_collect_errors(body, schema_name, schema, key_type, data_table, new_audit):
    """
    Validate items against schema rules and check for conflicts.
    
    Performs comprehensive validation including:
    - Schema attribute validation
    - Duplicate name checking within the batch
    - Existing name checking in the database
    - ID conflict checking for ULID schemas
    
    Args:
        body: List of items to validate
        schema_name: Name of the schema
        schema: Schema configuration with validation rules
        key_type: Type of primary key ('number' or 'ulid')
        data_table: DynamoDB table resource
        new_audit: Audit information to add to items
        
    Returns:
        tuple: (validated_items, errors_dict)
    """
    # Process the batch and get validation results
    _, duplicates, existing, validation_errors, validated = process_and_validate_item_batch(
        body, schema_name, schema, key_type, data_table, new_audit
    )
    
    # Organize errors by type for consistent response format
    errors = {
        'validation': validation_errors,  # Schema rule violations
        'duplicates': duplicates,         # Duplicate names in batch
        'existing': existing             # Names already in database
    }
    
    return validated, errors

def save_items_to_db(items, schema_name, schema_type, table_name, logging_context):
    """
    Save validated items to DynamoDB database.
    
    Converts items from API format to database format and saves them
    in batches using DynamoDB batch_write_item operations.
    
    Args:
        items: List of validated items in API format
        schema_name: Name of the schema
        schema_type: Type of schema ('custom' or 'user')
        table_name: Name of the DynamoDB table
        logging_context: Context string for logging
        
    Returns:
        list: List of batch operation responses
    """
    responses = []
    if items:
        db_items = [item_custom_assets.revert_item_from_schema(item, schema_name, schema_type) for item in items]
        save_items_in_batches_to_dynamodb(db_items, table_name, responses, logging_context)
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Processed {len(items)} items')
    return responses

def check_all_errors(errors, responses, logging_context):
    """
    Aggregate all error types from validation and database operations.
    
    Args:
        errors: Dict containing validation, duplicates, and existing errors
        responses: List of database operation responses
        logging_context: Context string for logging
        
    Returns:
        tuple: (has_errors, error_messages)
    """
    return aggregate_all_error_types(errors['validation'], errors['duplicates'], errors['existing'], responses, logging_context)

def create_final_response(items, error_messages, has_errors, logging_context):
    """
    Create final HTTP response for items operation.
    
    Returns a consistent response format with created items and any errors
    that occurred during processing. Successful items are always returned
    even if some items failed validation.
    
    Args:
        items: List of successfully created items
        error_messages: Dict of error types and messages
        has_errors: Boolean indicating if any errors occurred
        logging_context: Context string for logging
        
    Returns:
        dict: HTTP response with newItems and optional errors
    """
    response_body = {'newItems': items}
    if has_errors:
        response_body['errors'] = error_messages
        logger.warning(f'{PREFIX_INVOCATION} {logging_context}, {json.dumps(response_body)}')
    else:
        logger.info(f'{PREFIX_INVOCATION} {logging_context}, All items successfully processed.')
    
    return {'headers': {**default_http_headers}, 'body': json.dumps(response_body)}

def save_items_in_batches_to_dynamodb(items: list, table_name: str, responses: list, logging_context: str):
    """
    Save validated items to DynamoDB using batch write operations.
    
    Splits items into batches of 25 (DynamoDB limit) and uses
    batch_write_item for efficient bulk operations. Handles
    unprocessed items with retry logic.
    
    Args:
        items: List of items to save (in DynamoDB format)
        table_name: Name of the DynamoDB table
        responses: List to collect batch operation responses
        logging_context: Context string for logging
    """
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Saving {len(items)} items')
    
    # DynamoDB TypeSerializer converts Python objects to DynamoDB format
    ts = TypeSerializer()
    batch_size = 25  # DynamoDB batch_write_item limit
    
    # Process items in batches to stay within DynamoDB limits
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # Convert floats to Decimal and then to DynamoDB PutRequest format
        batch_requests = [{'PutRequest': {'Item': ts.serialize(convert_floats_to_decimal(item))['M']}} for item in batch]
        
        # Execute batch write operation
        response = client_ddb.batch_write_item(RequestItems={table_name: batch_requests})
        
        # Handle any unprocessed items with retry logic
        response = retry_unprocessed_items_with_backoff(response, batch, logging_context)
        responses.append(response)

def retry_unprocessed_items_with_backoff(response: dict, items: list, logging_context: str):
    """
    Retry unprocessed items from batch operations with exponential backoff.
    
    DynamoDB batch operations may not process all items due to throttling
    or capacity limits. This function retries unprocessed items with
    exponential backoff up to a maximum number of retries.
    
    Args:
        response: Initial batch_write_item response
        items: Original items that were attempted
        logging_context: Context string for logging
        
    Returns:
        dict: Final response after retries
    """
    # If all items were processed successfully, no retry needed
    if not response['UnprocessedItems']:
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Successfully wrote {len(items)} items')
        return response
    
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Retrying unprocessed items')
    
    max_retries = 3
    base_sleep_time = 5  # seconds
    unprocessed = response['UnprocessedItems']
    
    # Retry with exponential backoff
    for retry_count in range(max_retries):
        if not unprocessed:
            break
            
        # Calculate sleep time: 5s, 10s, 20s (capped at 60s)
        sleep_time = min(base_sleep_time * (2 ** retry_count), 60)
        sleep(sleep_time)
        
        # Retry the unprocessed items
        response = client_ddb.batch_write_item(RequestItems=unprocessed)
        unprocessed = response['UnprocessedItems']
        
        if unprocessed:
            logger.warning(f'{PREFIX_INVOCATION} {logging_context}, {len(unprocessed)} items still unprocessed after retry {retry_count + 1}')
    
    # Log final failure if items still unprocessed after all retries
    if unprocessed:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Failed to process all items after {max_retries} retries')
        response['UnprocessedItems'] = unprocessed
    
    return response

def validate_single_item_with_error_tracking(schema, schema_name, data_table, item, item_name_exists_errors, items_validation_errors, item_name_duplicates_errors, item_name_list):
    """
    Validate a single item against schema rules and duplicate checks.
    
    Performs three types of validation:
    1. Checks if item name already exists in database
    2. Validates item structure against schema rules
    3. Checks for duplicate names within the current batch
    
    Args:
        schema: Schema configuration with validation rules
        schema_name: Name of the schema
        data_table: DynamoDB table resource
        item: Item to validate
        item_name_exists_errors: List to collect existing name errors
        items_validation_errors: List to collect validation errors
        item_name_duplicates_errors: List to collect duplicate errors
        item_name_list: List of names already processed in batch
        
    Returns:
        bool: True if item is valid, False otherwise
    """
    # Determine the correct name field based on schema type
    schema_name_key = f'{schema_name}_name'
    name_value = item[schema_name_key]
    
    # Custom schemas use 'asset_name' instead of '{schema}_name'
    if schema['schema_type'] == 'custom':
        schema_name_key = 'asset_name'
    
    is_valid = True
    
    # Check 1: Does this name already exist in the database?
    # Skip if schema allows duplicates
    if not schema.get('allow_duplicates', False) and item_validation.does_item_with_name_exist(schema_name_key, name_value, data_table):
        item_name_exists_errors.append(name_value)
        is_valid = False
    
    # Check 2: Does the item structure comply with schema rules?
    validation_result = item_validation.check_valid_item_create(item, schema)
    if validation_result:
        items_validation_errors.append({name_value: validation_result})
        is_valid = False
    
    # Check 3: Is this name duplicated within the current batch?
    if name_value in item_name_list:
        item_name_duplicates_errors.append(name_value)
        is_valid = False
    else:
        # Track this name to catch future duplicates in the batch
        item_name_list.append(name_value)
    
    return is_valid

def batch_check_ids_exist_in_db(items_with_ids, schema_name, data_table):
    """
    Check for existing items in DynamoDB using batch operations.
    
    Splits large lists of IDs into chunks of 100 (DynamoDB batch limit)
    and checks which IDs already exist in the database.
    
    Args:
        items_with_ids: List of items that have ID fields
        schema_name: Name of the schema
        data_table: DynamoDB table resource
        
    Returns:
        set: Set of existing IDs found in database
    """
    existing_ids = set()
    # Extract just the ID values from the items
    keys = [item[f'{schema_name}_id'] for item in items_with_ids]
    
    # Process in chunks of 100 (DynamoDB batch_get_item limit)
    for i in range(0, len(keys), 100):
        chunk_keys = keys[i:i+100]
        # Check this chunk and add any existing IDs to our set
        existing_ids.update(check_id_chunk_with_retry(chunk_keys, schema_name, data_table, i))
    
    return existing_ids

def check_id_chunk_with_retry(chunk_keys, schema_name, data_table, chunk_index):
    """
    Check a chunk of keys with exponential backoff retry logic.
    
    Handles DynamoDB throttling by retrying failed requests with
    exponential backoff. Used by batch_check_ids_exist_in_db.
    
    Args:
        chunk_keys: List of keys to check (max 100)
        schema_name: Name of the schema
        data_table: DynamoDB table resource
        chunk_index: Index of chunk for logging
        
    Returns:
        set: Set of existing IDs from this chunk
    """
    max_retries = 3
    base_sleep_time = 1
    
    # Retry with exponential backoff
    for retry_count in range(max_retries + 1):
        try:
            # Build DynamoDB batch_get_item request
            # Each key needs to be in DynamoDB format: {'field_name': {'S': 'value'}}
            response = client_ddb.batch_get_item(
                RequestItems={data_table.name: {'Keys': [{f'{schema_name}_id': {'S': key}} for key in chunk_keys]}}
            )
            
            # Extract the ID values from the response items
            return {item[f'{schema_name}_id']['S'] for item in response.get('Responses', {}).get(data_table.name, [])}
            
        except Exception as e:
            if retry_count == max_retries:
                # Log failure after all retries exhausted
                logger.warning(f'{PREFIX_INVOCATION} batch_check_ids_exist_in_db, Failed chunk {chunk_index//100 + 1} after {max_retries} retries: {str(e)}')
                return set()
            
            # Wait before retrying (exponential backoff)
            sleep(base_sleep_time * (2 ** retry_count))
    
    return set()

def separate_items_by_id_conflicts(body, schema_name, existing_ids):
    """
    Filter out items that have IDs already existing in database.
    
    Used for ULID schemas where users can provide their own IDs.
    Items with existing IDs are rejected with validation errors.
    
    Args:
        body: List of items to filter
        schema_name: Name of the schema
        existing_ids: Set of IDs that already exist in database
        
    Returns:
        tuple: (items_to_validate, validation_errors)
    """
    items_to_validate = []
    validation_errors = []
    
    # Separate items into valid and conflicting groups
    for item in body:
        item_id = item.get(f'{schema_name}_id', None)
        
        if item_id is not None and item_id in existing_ids:            # This ID already exists - create validation error
            item_name = item[f'{schema_name}_name']
            validation_errors.append({item_name: [f'ID already exists: {item_id}']})
        else:
            # This item does not have an ID or
            # the ID it has is available - item can proceed to validation
            items_to_validate.append(item)
    
    return items_to_validate, validation_errors

def process_and_validate_item_batch(body, schema_name, schema, key_type, data_table, new_audit):
    """
    Validate all items in batch and track different types of errors.
    
    Processes items through multiple validation stages:
    1. Filter out items with existing IDs (ULID schemas only)
    2. Validate each item against schema rules
    3. Check for duplicate names within batch
    4. Set system attributes for valid items
    
    Args:
        body: List of items to validate
        schema_name: Name of the schema
        schema: Schema configuration
        key_type: Type of primary key ('number' or 'ulid')
        data_table: DynamoDB table resource
        new_audit: Audit information to add to items
        
    Returns:
        tuple: (name_list, duplicates, existing, validation_errors, validated_items)
    """
    # Initialize tracking state for different types of validation errors
    validation_state = {
        'name_list': [],        # Track names processed to detect duplicates
        'duplicates': [],       # Names duplicated within this batch
        'existing': [],         # Names that already exist in database
        'validation_errors': [], # Schema validation failures
        'validated': []         # Successfully validated items
    }
    
    # For ULID schemas, filter out items with IDs that already exist
    items_to_validate = filter_items_by_existing_ids(body, schema_name, key_type, data_table, validation_state)
    
    # For numeric schemas, get the starting ID once and increment for each item
    next_numeric_id = None
    if key_type == "number":
        next_numeric_id = generate_next_numeric_id(data_table, schema_name)
    
    # Process each item through validation pipeline
    for item in items_to_validate:
        # Validate item and track errors in validation_state
        if validate_single_item_with_error_tracking(schema, schema_name, data_table, item, validation_state['existing'], 
                        validation_state['validation_errors'], validation_state['duplicates'], validation_state['name_list']):
            try:
                # Item passed validation - set system attributes (ID, defaults, audit)
                next_numeric_id = set_system_attributes_for_new_item(data_table, item, schema, schema_name, key_type, new_audit, next_numeric_id)
                validation_state['validated'].append(item)
            except ValueError:
                # System attribute setting failed - stop processing
                break
    
    return (validation_state['name_list'], validation_state['duplicates'], 
            validation_state['existing'], validation_state['validation_errors'], validation_state['validated'])

def filter_items_by_existing_ids(body, schema_name, key_type, data_table, validation_state):
    """
    Filter items by existing IDs for ULID schemas.
    
    For ULID schemas, users can provide their own IDs. This function
    checks if any provided IDs already exist and filters them out.
    
    Args:
        body: List of items to filter
        schema_name: Name of the schema
        key_type: Type of primary key ('number' or 'ulid')
        data_table: DynamoDB table resource
        validation_state: Dict to track validation errors
        
    Returns:
        list: Items to validate (filtered for ULID schemas)
    """
    # Only ULID schemas allow user-provided IDs that need conflict checking
    if key_type == "ulid":
        # Find items that have IDs provided by the user
        items_with_ids = [item for item in body if f'{schema_name}_id' in item]
        
        # Check which of these IDs already exist in the database
        existing_ids = batch_check_ids_exist_in_db(items_with_ids, schema_name, data_table)
        
        # Separate items into valid and conflicting groups
        items_to_validate, existing_errors = separate_items_by_id_conflicts(body, schema_name, existing_ids)
        
        # Add ID conflict errors to validation state
        validation_state['validation_errors'].extend(existing_errors)
        return items_to_validate
    
    # Number schemas generate IDs automatically, so no filtering needed
    return body

def set_system_attributes_for_new_item(data_table, item, schema, schema_name, key_type, new_audit, next_numeric_id=None):
    """
    Set system-managed attributes for new items.
    
    Adds required system attributes to items before saving:
    1. Sets primary key ID based on schema key type
    2. Applies default values from schema configuration
    3. Handles special relationships (e.g., server app_ids)
    4. Adds audit information
    
    Args:
        data_table: DynamoDB table resource
        item: Item to modify
        schema: Schema configuration
        schema_name: Name of the schema
        key_type: Type of primary key ('number' or 'ulid')
        new_audit: Audit information to add
        next_numeric_id: For numeric schemas, the next ID to use (optional)
        
    Returns:
        int: For numeric schemas, returns the next ID to use for subsequent items
    """
    # Step 1: Set primary key ID based on schema type
    id_field = f'{schema_name}_id'
    
    if key_type == "ulid" and id_field not in item:
        # Generate new ULID if not provided by user
        item[id_field] = str(ULID())
    elif key_type == "uuid" and id_field not in item:
        # Generate new UUID if not provided by user
        item[id_field] = str(uuid.uuid4())
    elif key_type == "number":
        # Use provided next_numeric_id or generate one if not provided
        if next_numeric_id is not None:
            item[id_field] = str(next_numeric_id)
            next_numeric_id += 1  # Increment for next item
        else:
            item[id_field] = str(generate_next_numeric_id(data_table, schema_name))
    
    # Step 2: Apply schema-defined default values for missing attributes
    apply_schema_default_values(item, schema)
    
    # Step 3: Add audit trail information
    item['_history'] = new_audit
    
    # Return the next numeric ID for batch processing
    return next_numeric_id

def apply_schema_default_values(item, schema):
    """
    Apply default values from schema configuration.
    
    Sets default values for attributes that are not provided in the item
    but have defaults defined in the schema.
    
    Args:
        item: Item to modify
        schema: Schema configuration with attribute defaults
    """
    if 'attributes' in schema:
        # Process each attribute definition in the schema
        for attribute in schema['attributes']:
            attr_name = attribute['name']
            
            # Only set default if attribute is missing and default is defined
            if 'default' in attribute and attr_name not in item:
                item[attr_name] = attribute['default']

def aggregate_all_error_types(validation_errors: list, duplicates: list, existing: list, responses: list, logging_context: str):
    """
    Aggregate and categorize all types of errors from item processing.
    
    Collects errors from multiple sources:
    - validation_errors: Schema validation failures
    - duplicates: Duplicate names within the batch
    - existing: Names that already exist in database
    - unprocessed_items: Items that failed to save to database
    
    Args:
        validation_errors: List of schema validation errors
        duplicates: List of duplicate names in batch
        existing: List of existing names in database
        responses: List of database operation responses
        logging_context: Context string for logging
        
    Returns:
        tuple: (has_errors, error_messages_dict)
    """
    error_messages = {}
    has_errors = False
    
    # Check each error type and add to response if present
    
    # Schema validation errors (required fields, data types, etc.)
    if validation_errors:
        logger.warning(f'{PREFIX_INVOCATION} {logging_context}, Validation errors: {json.dumps(validation_errors)}')
        error_messages['validation_errors'] = validation_errors
        has_errors = True
    
    # Duplicate names within the current batch
    if duplicates:
        error_messages['duplicate_name'] = duplicates
        has_errors = True
    
    # Names that already exist in the database
    if existing:
        error_messages['existing_name'] = existing
        has_errors = True
    
    # Items that failed to save to DynamoDB (throttling, etc.)
    unprocessed = extract_unprocessed_items_from_responses(responses)
    if unprocessed:
        error_messages['unprocessed_items'] = unprocessed
        has_errors = True
    
    return has_errors, error_messages

def extract_unprocessed_items_from_responses(responses):
    """
    Extract unprocessed items from batch operation responses.
    
    Scans through all batch operation responses to find items
    that failed to be processed due to errors or throttling.
    
    Args:
        responses: List of batch_write_item responses
        
    Returns:
        list: List of unprocessed items
    """
    unprocessed = []
    
    # Check each batch operation response for failures
    for response in responses:
        # Only process responses that indicate failure
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            # Extract any items that couldn't be processed
            if 'UnprocessedItems' in response and 'PutRequest' in response['UnprocessedItems']:
                unprocessed.append(response['UnprocessedItems']['PutRequest'])
    
    return unprocessed
