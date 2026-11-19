"""
DynamoDB Operations Module

This module handles all DynamoDB operations for upload status tracking
and metadata management.

Author: AWS Migration Factory Team
"""

import os
from typing import Union, Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
from cmf_logger import logger
import cmf_boto
from boto3.dynamodb.conditions import Key
from s3_import_exceptions import DynamoDBError

class UploadStatus(Enum):
    """Upload job status values"""
    PENDING = 'pending'
    IN_PROGRESS = 'in-progress'
    COMPLETE = 'complete'
    FAILED = 'failed'

# Initialize DynamoDB resources
dynamodb = cmf_boto.resource('dynamodb')
application = os.environ['application']
environment = os.environ['environment']
upload_table_name = f'{application}-{environment}-upload-entities-metadata'
upload_table = dynamodb.Table(upload_table_name)

def check_and_update_upload_status(upload_id: str, new_status: str) -> Union[Dict[str, Any], bool]:
    """
    Check current upload processing status and update if processing should continue.
    """
    try:
        upload_item = _get_upload_record(upload_id)
        current_status = _validate_current_status(upload_id, upload_item)
        
        if _is_already_processed(upload_id, current_status):
            return False
            
        _update_status_to_in_progress(upload_id, new_status)
        logger.info(f"Updated upload {upload_id} status from {current_status} to {new_status}")
        return upload_item
        
    except DynamoDBError:
        raise
    except Exception as e:
        logger.error(f"Failed to check/update upload status for {upload_id}: {e}")
        raise DynamoDBError(f"Failed to check/update upload status for {upload_id}: {e}") from e

def _get_upload_record(upload_id: str) -> Dict[str, Any]:
    """Get upload record from DynamoDB."""
    response = upload_table.get_item(Key={'upload_id': upload_id})
    
    if 'Item' not in response:
        error_msg = f"Upload record not found for upload_id: {upload_id}"
        logger.error(error_msg)
        raise DynamoDBError(error_msg)
        
    return response['Item']

def _validate_current_status(upload_id: str, upload_item: Dict[str, Any]) -> str:
    """Validate and return current status."""
    current_status = upload_item.get('status')
    
    if not current_status:
        logger.warning(f"Upload {upload_id} has no status field, treating as pending")
        current_status = 'pending'
    
    return current_status

def _is_already_processed(upload_id: str, current_status: str) -> bool:
    """Check if upload is already processed or in progress."""
    if current_status in [UploadStatus.IN_PROGRESS.value, UploadStatus.FAILED.value, 
                          UploadStatus.COMPLETE.value]:
        logger.info(f"Upload {upload_id} already processed with status: {current_status}")
        return True
    return False

def _update_status_to_in_progress(upload_id: str, new_status: str) -> None:
    """Update upload status to in-progress and remove record_ttl to prevent deletion."""
    current_timestamp = datetime.now(timezone.utc).isoformat()
    
    upload_table.update_item(
        Key={'upload_id': upload_id},
        ConditionExpression='attribute_exists(upload_id)',
        UpdateExpression='SET #status = :status, #history.#lastModifiedTimestamp = :lastModifiedTimestamp REMOVE record_ttl',
        ExpressionAttributeNames={
            '#status': 'status',
            '#history': '_history',
            '#lastModifiedTimestamp': 'lastModifiedTimestamp'
        },
        ExpressionAttributeValues={
            ':status': new_status,
            ':lastModifiedTimestamp': current_timestamp
        }
    )

def fetch_all_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Fetch filtered entity schemas from DynamoDB schema table.
    Only keeps 'app'/'application', 'database', 'server', and 'custom' schemas.
    
    Returns:
        dict: Dictionary mapping schema names to schema objects
    """
    try:
        schema_table_name = f"{application}-{environment}-schema"
        schema_table = dynamodb.Table(schema_table_name)
        response = schema_table.scan()
        
        schema_cache = {}
        for item in response.get('Items', []):
            schema_name = item.get('schema_name')
            if schema_name and _should_include_schema(schema_name, item):
                schema_cache[schema_name] = item
        
        logger.info(f"Fetched {len(schema_cache)} filtered schemas")
        return schema_cache
        
    except Exception as e:
        logger.error(f"Failed to fetch all schemas: {e}")
        return {}

def _should_include_schema(schema_name: str, schema: Dict[str, Any]) -> bool:
    """Check if schema should be included in import processing."""
    return (schema_name in ['application', 'app', 'database', 'server'] or is_custom_asset_schema(schema))

def fetch_all_entities_for_import(schema_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Pre-load all entities from all schemas into name-to-ID mappings.
    
    Args:
        schema_cache: Dictionary of all schemas
        
    Returns:
        dict: {entity_type: {entity_name: entity_id}}
    """
    name_to_id_map = {}
    
    # Handle standard entities
    for schema_name, schema in schema_cache.items():
        if is_custom_asset_schema(schema):
            continue  # Skip custom assets, handle separately
            
        try:
            entity_type_name = "app" if schema_name == "application" else schema_name
            table_name = f"{application}-{environment}-{entity_type_name}s"
            table = dynamodb.Table(table_name)
            items = scan_dynamodb_table(table)
            
            name_field = f"{entity_type_name}_name"
            id_field = f"{entity_type_name}_id"
            
            name_to_id_map[schema_name] = {
                item[name_field]: item[id_field] 
                for item in items 
                if name_field in item and id_field in item
            }
            
            logger.info(f"Pre-loaded {len(name_to_id_map[schema_name])} {schema_name} entities")
            
        except Exception as e:
            logger.warning(f"Failed to pre-load {schema_name} entities: {e}")
            name_to_id_map[schema_name] = {}
    
    # Handle custom assets
    custom_asset_mappings = fetch_custom_assets_for_import(schema_cache)
    name_to_id_map.update(custom_asset_mappings)
    
    return name_to_id_map

def is_custom_asset_schema(schema: Dict[str, Any]) -> bool:
    """Check if schema represents a custom asset type."""
    # Custom assets are identified by schema_type = 'custom'
    return schema.get('schema_type') == 'custom'

def fetch_custom_assets_for_import(schema_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Fetch all custom assets and build name-to-ID mappings."""
    try:
        custom_assets_table_name = f"{application}-{environment}-custom-assets"
        custom_assets_table = dynamodb.Table(custom_assets_table_name)
        
        # Scan entire custom assets table
        all_custom_assets = scan_dynamodb_table(custom_assets_table)
        
        # Group assets by type and build mappings
        return group_custom_assets_by_type(all_custom_assets, schema_cache)
        
    except Exception as e:
        logger.warning(f"Failed to pre-load custom assets: {e}")
        return {}

def group_custom_assets_by_type(custom_assets: List[Dict[str, Any]], 
                               schema_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Group custom assets by type and build name-to-ID mappings."""
    mappings = {}
    
    # Get list of custom asset schema names
    custom_schema_names = {
        schema_name for schema_name, schema in schema_cache.items() 
        if is_custom_asset_schema(schema)
    }
    
    # Group assets by type
    for asset in custom_assets:
        # Extract asset_type from partition key (format: "asset_type#shard")
        partition_key = asset.get('asset_type#shard', '')
        if '#' not in partition_key:
            continue
            
        asset_type = partition_key.split('#')[0]
        
        # Only include assets for schemas we're importing
        if asset_type not in custom_schema_names:
            continue
            
        # Initialize mapping for this asset type
        if asset_type not in mappings:
            mappings[asset_type] = {}
            
        # Map from DB format to API format
        # DB: asset_name → asset_id
        # API: {schema_name}_name → {schema_name}_id (handled by conversion functions)
        asset_name = asset.get('asset_name')
        asset_id = asset.get('asset_id')
        
        if asset_name and asset_id:
            mappings[asset_type][asset_name] = asset_id
    
    # Log results
    for asset_type, mapping in mappings.items():
        logger.info(f"Pre-loaded {len(mapping)} {asset_type} custom assets")
    
    return mappings

def scan_dynamodb_table(table) -> List[Dict[str, Any]]:
    """
    Scan entire DynamoDB table with pagination.
    
    Args:
        table: DynamoDB table resource
        
    Returns:
        list: All items from the table
    """
    items = []
    response = table.scan()
    items.extend(response.get('Items', []))
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    return items

def update_upload_status(upload_id: str, status: str, results_location: Optional[str] = None) -> None:
    """
    Update upload status in DynamoDB.
    """
    try:
        update_expr, attr_values = _build_update_expression(status, results_location)
        
        response = upload_table.update_item(
            Key={'upload_id': upload_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={
                '#status': 'status',
                '#history': '_history',
                '#lastModifiedTimestamp': 'lastModifiedTimestamp'
            },
            ExpressionAttributeValues=attr_values,
            ConditionExpression='attribute_exists(upload_id)',
            ReturnValues='ALL_NEW'
        )
        
        if not response.get('Attributes'):
            raise DynamoDBError(f"Failed to update upload {upload_id} - no attributes returned")
            
        logger.info(f"Successfully updated upload {upload_id} status to {status}")
        if results_location:
            logger.info(f"Results location set to: {results_location}")
            
    except DynamoDBError:
        raise
    except Exception as e:
        logger.error(f"Critical: Failed to update upload status for {upload_id} to {status}: {e}")
        raise DynamoDBError(f"Failed to update upload status for {upload_id} to {status}: {e}") from e

def _build_update_expression(status: str, results_location: Optional[str]) -> tuple:
    """Build DynamoDB update expression and attribute values."""
    current_timestamp = datetime.now(timezone.utc).isoformat()
    
    update_expr = 'SET #status = :status, #history.#lastModifiedTimestamp = :lastModifiedTimestamp'
    attr_values = {
        ':status': status,
        ':lastModifiedTimestamp': current_timestamp
    }
    
    if results_location:
        update_expr += ', results_location = :location'
        attr_values[':location'] = results_location
    
    return update_expr, attr_values

def safe_update_upload_status_to_failed(upload_id: str) -> None:
    """
    Safely update upload status to failed without raising exceptions.
    Used in error handling scenarios where we don't want to mask the original error.
    
    Args:
        upload_id (str): Unique upload identifier
    """
    try:
        update_upload_status(upload_id, 'failed')
    except Exception as e:
        logger.error(f"Failed to update upload {upload_id} to failed status: {e}")
        # Don't raise - this is a cleanup operation
