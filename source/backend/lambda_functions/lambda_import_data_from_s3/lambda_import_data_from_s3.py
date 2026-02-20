"""
AWS Lambda Function: S3 Import Data Processor

This Lambda function is triggered by S3 object creation events in the uploads/ prefix.
It processes JSON files containing entity data validation results, creates entities via API calls,
resolves cross-references, and saves processing results back to S3.

Flow:
1. Triggered by S3 object creation in uploads/ prefix
2. Retrieves upload metadata and validates processing status
3. Parses JSON file as DataValidationResult
4. Generates ULIDs for entities and resolves cross-references
5. Makes POST API calls to create entities (without cross-references)
6. Updates entities with cross-references via direct DynamoDB operations
7. Saves processing results to S3 in results/ prefix
8. Updates upload status in DynamoDB

Author: AWS Migration Factory Team
"""

import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from request import parse_import_request, ImportRequestData, Entity, EntitySchema
from results import create_processing_results, ProcessingResults, FailureDetails
from cmf_logger import logger, log_event_received
from cmf_utils import send_anonymous_usage_data
from s3_import_s3_operations import get_upload_metadata, get_s3_file_content, save_results_to_s3
from s3_import_dynamodb_operations import check_and_update_upload_status, update_upload_status, fetch_all_schemas, safe_update_upload_status_to_failed
from s3_import_entity_processor import process_entities_for_import, get_name_field, get_id_field
from s3_import_exceptions import S3ImportError, ValidationError, S3OperationError, DynamoDBError

@dataclass
class LambdaContext:
    """AWS Lambda context object"""
    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    remaining_time_in_millis: int
    log_group_name: str
    log_stream_name: str
    aws_request_id: str

@dataclass
class WorkflowData:
    """Data passed between workflow steps"""
    import_data: ImportRequestData
    uploaded_by: Optional[str]
    auth_info: Dict[str, Any]
    upload_id: str
    object_key: str
    s3_bucket: str
    schema_cache: Optional[Dict[str, Dict[str, Any]]] = None
    processed_creates: Optional[Dict[str, List[Dict[str, Any]]]] = None
    processed_updates: Optional[Dict[str, List[Dict[str, Any]]]] = None
    name_to_id_map: Optional[Dict[str, Dict[str, str]]] = None

def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, str]:
    """
    Main Lambda handler function triggered by S3 object creation events.
    """
    log_event_received(event)
    
    if not event.get('Records'):
        logger.error("No Records found in event")
        raise ValidationError("Invalid event structure: missing Records")
    
    processed_count, failed_count = _process_all_records(event['Records'])
    
    if failed_count > 0:
        error_msg = f"Processing completed with {failed_count} failures out of {processed_count + failed_count} records"
        logger.error(error_msg)
        raise S3ImportError(error_msg)
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully processed {processed_count} files')
    }

def _process_all_records(records: List[Dict[str, Any]]) -> tuple:
    """Process all S3 records and return counts."""
    processed_count = 0
    failed_count = 0
    schema_cache = fetch_all_schemas()
    
    for record in records:
        try:
            process_s3_record(record, schema_cache)
            processed_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to process record {record}: {e}")
            _handle_record_failure(record)
    
    return processed_count, failed_count

def _handle_record_failure(record: Dict[str, Any]) -> None:
    """Handle failure of a single record by updating upload status."""
    try:
        bucket_name = record.get('s3', {}).get('bucket', {}).get('name')
        object_key = record.get('s3', {}).get('object', {}).get('key')
        if bucket_name and object_key:
            upload_id, _ = get_upload_metadata(bucket_name, object_key)
            if upload_id:
                safe_update_upload_status_to_failed(upload_id)
    except Exception as cleanup_error:
        logger.error(f"Failed to update status for failed record: {cleanup_error}")

def process_s3_record(record: Dict[str, Any], schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Process a single S3 record through the workflow steps.
    
    Args:
        record (dict): Single S3 record from Lambda event
        schema_cache (dict): Pre-fetched schema cache
        
    Raises:
        Exception: Any processing errors from workflow steps
    """
    data = None
    results = None
    
    try:
        # Execute simplified workflow steps
        data = read_data_from_s3(record)
        data.schema_cache = schema_cache
        
        results = create_processing_results(data.upload_id, data.object_key, data.uploaded_by, data.import_data)
        
        data = process_entities(data, results)
        data = create_entities(data, results)
        data = update_entities(data, results)
        
        # Save results and complete upload
        save_results_and_complete(data, results)
        
    except Exception as e:
        # Ensure upload status is marked as failed
        if data and data.upload_id:
            try:
                if not results:
                    results = create_processing_results(data.upload_id, data.object_key, data.uploaded_by, data.import_data)
                handle_processing_error(data, results, e)
            except Exception as cleanup_error:
                logger.error(f"Failed to handle processing error for {data.upload_id}: {cleanup_error}")
                # Fallback: just update status to failed
                safe_update_upload_status_to_failed(data.upload_id)
        raise

def read_data_from_s3(record: Dict[str, Any]) -> WorkflowData:
    """
    Read and parse data from S3 file, including upload metadata and status validation.
    """
    bucket_name, object_key = _extract_s3_info(record)
    logger.info(f"Step 1: Reading data from S3 - {bucket_name}/{object_key}")
    
    try:
        upload_id, uploaded_by, auth_info = _get_upload_info(bucket_name, object_key)
        import_data = _parse_file_content(bucket_name, object_key)
        
        logger.info(f"Successfully read data with {len(import_data.entities_to_create)} entities to create and {len(import_data.entities_to_update)} entities to update")
        
        return WorkflowData(
            import_data=import_data,
            uploaded_by=uploaded_by,
            auth_info=auth_info,
            upload_id=upload_id,
            object_key=object_key,
            s3_bucket=bucket_name
        )
        
    except Exception as e:
        logger.error(f"Failed to read data from S3: {e}")
        raise

def _extract_s3_info(record: Dict[str, Any]) -> tuple:
    """Extract bucket name and object key from S3 record."""
    if not record.get('s3', {}).get('bucket', {}).get('name'):
        raise ValidationError(f"Invalid S3 record structure: missing bucket name in {record}")
    if not record.get('s3', {}).get('object', {}).get('key'):
        raise ValidationError(f"Invalid S3 record structure: missing object key in {record}")
        
    return record['s3']['bucket']['name'], record['s3']['object']['key']

def _get_upload_info(bucket_name: str, object_key: str) -> tuple:
    """Get upload metadata and validate status."""
    upload_id, uploaded_by = get_upload_metadata(bucket_name, object_key)
    if not upload_id:
        raise S3OperationError(f"No upload_id found for {object_key} - file may not be properly uploaded")
    
    upload_record = check_and_update_upload_status(upload_id, 'in-progress')
    if not upload_record:
        raise DynamoDBError(f"Upload {upload_id} already processed or in progress")
    
    auth_info = upload_record.get('auth_info', {}) if isinstance(upload_record, dict) else {}
    return upload_id, uploaded_by, auth_info

def _parse_file_content(bucket_name: str, object_key: str) -> ImportRequestData:
    """Download and parse file content from S3."""
    file_content = get_s3_file_content(bucket_name, object_key)
    
    if not file_content or not file_content.strip():
        raise S3OperationError(f"File {object_key} is empty or contains no valid content")
    
    json_data = json.loads(file_content)
    import_data = parse_import_request(json_data)
    
    total_entities = len(import_data.entities_to_create) + len(import_data.entities_to_update)
    if total_entities == 0:
        logger.warning(f"No entities found in import data for {object_key}")
    
    return import_data

def process_entities(data: WorkflowData, results: ProcessingResults) -> WorkflowData:
    """
    Process entities: generate ULIDs, extract cross-references, build name-to-ID mappings.
    
    Args:
        data: WorkflowData containing entities to create and update
        results: Results tracking object
        
    Returns:
        WorkflowData: Data with processed entities ready for API calls
    """
    logger.info("Step 1: Processing entities - generating ULIDs and extracting cross-references")
    
    try:
        # Process all entities and extract cross-references
        processed_data = process_entities_for_import(
            data.import_data.entities_to_create,
            data.import_data.entities_to_update,
            data.schema_cache,
            results
        )
        
        # Store processed data in workflow
        data.processed_creates = processed_data['entities_to_create']
        data.processed_updates = processed_data['entities_to_update']
        data.name_to_id_map = processed_data['name_to_id_map']
        
        logger.info(f"Successfully processed entities with {len(data.processed_creates)} create types and {len(data.processed_updates)} update types")
        return data
        
    except Exception as e:
        logger.error(f"Failed to process entities: {e}")
        raise

def create_entities(data: WorkflowData, results: ProcessingResults) -> WorkflowData:
    """
    Create entities via POST operations (without cross-references).
    
    Args:
        data: WorkflowData containing processed entities
        results: Results tracking object
        
    Returns:
        WorkflowData: Data with CREATE phase completed
    """
    logger.info("Step 2: Creating entities via POST operations")
    
    from s3_import_batch_processor import execute_create_phase
    
    try:
        # Execute POST operations for all entity types
        failed_entity_ids = execute_create_phase(
            data.processed_creates or {},
            data.auth_info,
            results,
            data.schema_cache
        )
        
        # Remove failed entities from update lists
        if failed_entity_ids:
            remove_failed_entities_from_updates(data.processed_updates or {}, failed_entity_ids, results, data.schema_cache)
        
        logger.info(f"Step 2: CREATE phase completed - {results.get_successful_creates_count()} created, {results.get_failed_creates_count()} failed")
        return data
        
    except Exception as e:
        logger.error(f"Failed to create entities: {e}")
        raise

def update_entities(data: WorkflowData, results: ProcessingResults) -> WorkflowData:
    """
    Update entities via PUT operations (cross-references and file updates).
    
    Args:
        data: WorkflowData containing entities to update
        results: Results tracking object
        
    Returns:
        WorkflowData: Data with UPDATE phase completed
    """
    logger.info("Step 3: Updating entities via PUT operations")
    
    from s3_import_batch_processor import execute_update_phase
    
    try:
        # Execute PUT operations for all entity types
        execute_update_phase(
            data.processed_updates or {},
            data.auth_info,
            results,
            data.schema_cache
        )
        
        logger.info(f"Step 3: UPDATE phase completed - {results.get_successful_updates_count()} updated, {results.get_failed_updates_count()} failed")
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to update entities: {e}")
        raise

def save_results_and_complete(data: WorkflowData, results: ProcessingResults) -> None:
    """
    Save processing results to S3 and mark upload as complete.
    """
    upload_id = data.upload_id
    object_key = data.object_key
    bucket_name = data.s3_bucket
    
    results_location = save_results_to_s3(bucket_name, upload_id, results, object_key)
    
    if results.has_failures():
        status = 'failed'
        failed_creates = results.get_failed_creates_count()
        failed_updates = results.get_failed_updates_count()
        logger.warning(f"Upload {upload_id} completed with failures. {failed_creates} creates failed, {failed_updates} updates failed.")
    else:
        status = 'complete'
        send_anonymous_usage_data('UploadJobComplete')
        logger.info(f"Upload {upload_id} completed successfully. All entities processed without errors.")
    
    update_upload_status(upload_id, status, results_location)

def handle_processing_error(data: WorkflowData, results: ProcessingResults, error: Exception) -> None:
    """
    Handle processing errors and update status.
    """
    upload_id = data.upload_id
    if not upload_id:
        return
        
    try:
        # Mark all entities as failed - they will be counted via the failure dictionaries
        
        object_key = data.object_key
        bucket_name = data.s3_bucket
        if object_key and bucket_name:
            results_location = save_results_to_s3(bucket_name, upload_id, results, object_key)
        else:
            results_location = None
            
    except Exception as e:
        logger.error(f"Failed to generate error file for {upload_id}: {e}")
        results_location = None
    
    update_upload_status(upload_id, 'failed', results_location)
    failed_creates = results.get_failed_creates_count()
    failed_updates = results.get_failed_updates_count()
    logger.error(f"Error processing upload {upload_id}: {error}. {failed_creates} creates failed, {failed_updates} updates failed.")

def remove_failed_entities_from_updates(processed_updates: Dict[str, List[Dict[str, Any]]], 
                                       failed_entity_ids: Dict[str, List[str]], 
                                       results: ProcessingResults,
                                       schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Remove failed entities and their references from update lists.
    
    Args:
        processed_updates: Dictionary of entities to update
        failed_entity_ids: Dictionary of failed entity IDs by type
        results: Results tracking for additional failures
    """
    if not failed_entity_ids:
        return
        
    logger.info("Removing failed entities and their references from update lists")
    
    # Remove direct updates for failed entities
    for entity_type, failed_ids in failed_entity_ids.items():
        if entity_type in processed_updates:
            id_field = get_id_field(entity_type, schema_cache)
            original_count = len(processed_updates[entity_type])
            
            processed_updates[entity_type] = [
                entity for entity in processed_updates[entity_type]
                if entity.get(id_field) not in failed_ids
            ]
            
            removed_count = original_count - len(processed_updates[entity_type])
            if removed_count > 0:
                logger.info(f"Removed {removed_count} {entity_type} updates for failed creates")
    
    # Remove references TO failed entities from other updates
    remove_references_to_failed_entities(processed_updates, failed_entity_ids, results, schema_cache)

def remove_references_to_failed_entities(processed_updates: Dict[str, List[Dict[str, Any]]], 
                                        failed_entity_ids: Dict[str, List[str]], 
                                        results: ProcessingResults,
                                        schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Remove references to failed entities from other entity updates.
    """
    all_failed_ids = _build_failed_ids_set(failed_entity_ids)
    if not all_failed_ids:
        return
    
    for entity_type, entities in processed_updates.items():
        _clean_entity_references(entity_type, entities, all_failed_ids, results, schema_cache)

def _build_failed_ids_set(failed_entity_ids: Dict[str, List[str]]) -> set:
    """Build set of all failed IDs for quick lookup."""
    all_failed_ids = set()
    for failed_ids in failed_entity_ids.values():
        all_failed_ids.update(failed_ids)
    return all_failed_ids

def _clean_entity_references(entity_type: str, entities: List[Dict[str, Any]], 
                           all_failed_ids: set, results: ProcessingResults,
                           schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """Clean references to failed entities from entity list."""
    from s3_import_entity_processor import get_cross_reference_attributes
    
    schema = schema_cache.get(entity_type, {})
    cross_ref_attrs = get_cross_reference_attributes(schema)
    entities_to_remove = []
    
    for i, entity in enumerate(entities):
        _process_entity_references(entity, cross_ref_attrs, all_failed_ids)
        
        # Check if entity has meaningful updates left
        meaningful_attrs = [k for k in entity.keys() if not k.endswith('_id')]
        if not meaningful_attrs:
            entities_to_remove.append(i)
            _track_empty_entity_failure(entity_type, entity, i, results, schema_cache)
    
    # Remove entities with no meaningful updates
    for i in reversed(entities_to_remove):
        entities.pop(i)

def _process_entity_references(entity: Dict[str, Any], cross_ref_attrs: List[str], 
                             all_failed_ids: set) -> None:
    """Process and clean references in a single entity."""
    for attr_name in cross_ref_attrs:
        if attr_name not in entity:
            continue
            
        attr_value = entity[attr_name]
        
        if isinstance(attr_value, list):
            new_list = [ref_id for ref_id in attr_value if ref_id not in all_failed_ids]
            entity[attr_name] = new_list
            if not new_list:
                del entity[attr_name]
        elif attr_value in all_failed_ids:
            del entity[attr_name]

def _track_empty_entity_failure(entity_type: str, entity: Dict[str, Any], 
                              index: int, results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """Track entity as failure when it has no meaningful updates left."""
    name_field = get_name_field(entity_type, schema_cache)
    entity_name = entity.get(name_field, f"item_{index}")
    
    if entity_type not in results.update_failures:
        results.update_failures[entity_type] = {}
    
    results.update_failures[entity_type][entity_name] = FailureDetails(
        data=entity.copy(),
        error_message="Update cancelled: all referenced entities failed to create"
    )
