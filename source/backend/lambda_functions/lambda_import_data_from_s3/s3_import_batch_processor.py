"""
Batch Processing Module

This module handles batch processing of entities through API calls,
including POST and PUT operations with parallel execution and error handling.

Author: AWS Migration Factory Team
"""

from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from cmf_logger import logger
from results import ProcessingResults, FailureDetails
from s3_import_exceptions import APIError, ValidationError
from s3_import_entity_processor import get_name_field, get_id_field
from s3_import_lambda_client import invoke_lambda_function

EntityData = List[Dict[str, Any]]
ProcessedEntities = Dict[str, EntityData]

def execute_create_phase(processed_creates: ProcessedEntities, auth_info: Dict[str, Any], results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> Dict[str, List[str]]:
    """
    Execute CREATE phase - POST entities without cross-references.
    """
    logger.info("Starting CREATE phase - posting entities via API")
    
    failed_entity_ids = {}
    
    for entity_type, entity_data in processed_creates.items():
        try:
            logger.info(f"Creating {len(entity_data)} {entity_type} entities via POST")
            entity_failed_ids = _process_create_batches(entity_type, entity_data, auth_info, results, schema_cache)
            
            if entity_failed_ids:
                failed_entity_ids[entity_type] = entity_failed_ids
                
        except Exception as e:
            handle_create_entity_type_failure(entity_type, entity_data, e, results, failed_entity_ids, schema_cache)
    
    logger.info(f"CREATE phase completed: {results.get_successful_creates_count()} created, {results.get_failed_creates_count()} failed")
    return failed_entity_ids

def _process_create_batches(entity_type: str, entity_data: EntityData, 
                          auth_info: Dict[str, Any], results: ProcessingResults, 
                          schema_cache: Dict[str, Dict[str, Any]] = None) -> List[str]:
    """Process entity data in batches for CREATE operations in parallel."""
    batch_size = 200
    batches = [entity_data[i:i + batch_size] for i in range(0, len(entity_data), batch_size)]
    entity_failed_ids = []
    
    with ThreadPoolExecutor(max_workers=75) as executor:
        future_to_batch = {
            executor.submit(_process_single_create_batch, entity_type, batch_num, batch, auth_info, results, schema_cache): (batch_num, batch)
            for batch_num, batch in enumerate(batches, 1)
        }
        
        for future in as_completed(future_to_batch):
            batch_num, batch = future_to_batch[future]
            try:
                batch_failed_ids = future.result()
                entity_failed_ids.extend(batch_failed_ids)
            except Exception as e:
                handle_create_batch_error(entity_type, batch, e, results, entity_failed_ids, schema_cache)
    
    return entity_failed_ids

def _process_single_create_batch(entity_type: str, batch_num: int, batch: EntityData, 
                               auth_info: Dict[str, Any], results: ProcessingResults, 
                               schema_cache: Dict[str, Dict[str, Any]] = None) -> List[str]:
    """Process a single CREATE batch."""
    batch_failed_ids = []
    
    try:
        response = invoke_lambda_function('POST', entity_type, batch, auth_info)
        
        if response and response.get('success'):
            _track_successful_creates(entity_type, batch_num, response, results)
        else:
            handle_create_batch_failure(entity_type, batch, response, results, batch_failed_ids, schema_cache)
            
    except Exception as e:
        handle_create_batch_error(entity_type, batch, e, results, batch_failed_ids, schema_cache)
    
    return batch_failed_ids

def _track_successful_creates(entity_type: str, batch_num: int, 
                            response: Dict[str, Any], results: ProcessingResults) -> None:
    """Track successful CREATE operations."""
    new_items = response.get('new_items', [])
    if new_items:
        if entity_type not in results.created_items:
            results.created_items[entity_type] = []
        
        results.created_items[entity_type].extend(new_items)
    
    logger.info(f"Batch {batch_num} for {entity_type}: {len(new_items)} created successfully")

def handle_create_batch_failure(entity_type: str, batch: EntityData, response: Dict[str, Any], 
                               results: ProcessingResults, entity_failed_ids: List[str], 
                               schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Handle failure of a CREATE batch.
    
    Args:
        entity_type: Type of entity that failed
        batch: Batch of entities that failed
        response: API response with error details
        results: Results to update
        entity_failed_ids: List to add failed IDs to
        schema_cache: Schema cache for field name resolution
    """
    api_errors = response.get('api_errors', {}) if response else {}
    error_message = f"POST request failed: {api_errors.get('error', 'Unknown error')}"
    
    name_field = get_name_field(entity_type, schema_cache)
    id_field = get_id_field(entity_type, schema_cache)
    
    # Track each entity in the batch as failed
    for entity in batch:
        entity_name = entity.get(name_field, 'unknown')
        entity_id = entity.get(id_field)
        
        if entity_id:
            entity_failed_ids.append(entity_id)
        
        # Add to create failures
        if entity_type not in results.create_failures:
            results.create_failures[entity_type] = {}
        
        results.create_failures[entity_type][entity_name] = FailureDetails(
            data=entity,
            error_message=error_message
        )
    
    logger.error(f"Batch failed for {entity_type}: {len(batch)} entities failed - {error_message}")

def handle_create_batch_error(entity_type: str, batch: EntityData, error: Exception, 
                             results: ProcessingResults, entity_failed_ids: List[str], 
                             schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Handle error during CREATE batch processing.
    
    Args:
        entity_type: Type of entity that failed
        batch: Batch of entities that failed
        error: Exception that occurred
        results: Results to update
        entity_failed_ids: List to add failed IDs to
        schema_cache: Schema cache for field name resolution
    """
    error_message = f"POST request error: {str(error)}"
    
    name_field = get_name_field(entity_type, schema_cache)
    id_field = get_id_field(entity_type, schema_cache)
    
    # Track each entity in the batch as failed
    for entity in batch:
        entity_name = entity.get(name_field, 'unknown')
        entity_id = entity.get(id_field)
        
        if entity_id:
            entity_failed_ids.append(entity_id)
        
        # Add to create failures
        if entity_type not in results.create_failures:
            results.create_failures[entity_type] = {}
        
        results.create_failures[entity_type][entity_name] = FailureDetails(
            data=entity,
            error_message=error_message
        )
    
    logger.error(f"Batch error for {entity_type}: {len(batch)} entities failed - {error_message}")

def handle_create_entity_type_failure(entity_type: str, entity_data: EntityData, error: Exception, 
                                     results: ProcessingResults, failed_entity_ids: Dict[str, List[str]], 
                                     schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Handle failure of entire entity type during CREATE phase.
    
    Args:
        entity_type: Type of entity that failed
        entity_data: All entities of this type
        error: Exception that occurred
        results: Results to update
        failed_entity_ids: Dictionary to add failed IDs to
        schema_cache: Schema cache for field name resolution
    """
    error_message = f"Entity type creation failed: {str(error)}"
    
    name_field = get_name_field(entity_type, schema_cache)
    id_field = get_id_field(entity_type, schema_cache)
    
    entity_failed_ids_list = []
    
    # Track all entities as failed
    for entity in entity_data:
        entity_name = entity.get(name_field, 'unknown')
        entity_id = entity.get(id_field)
        
        if entity_id:
            entity_failed_ids_list.append(entity_id)
        
        # Add to create failures
        if entity_type not in results.create_failures:
            results.create_failures[entity_type] = {}
        
        results.create_failures[entity_type][entity_name] = FailureDetails(
            data=entity,
            error_message=error_message
        )
    
    if entity_failed_ids_list:
        failed_entity_ids[entity_type] = entity_failed_ids_list
    
    logger.error(f"Entity type {entity_type} creation failed: {len(entity_data)} entities failed - {error_message}")

def execute_update_phase(processed_updates: ProcessedEntities, auth_info: Dict[str, Any], results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Execute UPDATE phase - PUT entities with cross-references and file updates.
    """
    logger.info("Starting UPDATE phase - putting entities via API")
    
    for entity_type, entity_data in processed_updates.items():
        if not entity_data:
            continue
            
        try:
            logger.info(f"Updating {len(entity_data)} {entity_type} entities via bulk PUT")
            _process_update_batches(entity_type, entity_data, auth_info, results, schema_cache)
                    
        except Exception as e:
            handle_update_entity_type_failure(entity_type, entity_data, e, results, schema_cache)
    
    logger.info(f"UPDATE phase completed: {results.get_successful_updates_count()} updated, {results.get_failed_updates_count()} failed")

def _process_update_batches(entity_type: str, entity_data: EntityData, 
                          auth_info: Dict[str, Any], results: ProcessingResults, 
                          schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """Process entity data in batches for UPDATE operations in parallel."""
    batch_size = 200
    batches = [entity_data[i:i + batch_size] for i in range(0, len(entity_data), batch_size)]
    
    with ThreadPoolExecutor(max_workers=75) as executor:
        future_to_batch = {
            executor.submit(_process_single_update_batch, entity_type, batch_num, batch, auth_info, results, schema_cache): (batch_num, batch)
            for batch_num, batch in enumerate(batches, 1)
        }
        
        for future in as_completed(future_to_batch):
            batch_num, batch = future_to_batch[future]
            try:
                future.result()
            except Exception as e:
                handle_update_batch_error(entity_type, batch, e, results, schema_cache)

def _process_single_update_batch(entity_type: str, batch_num: int, batch: EntityData, 
                               auth_info: Dict[str, Any], results: ProcessingResults, 
                               schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """Process a single UPDATE batch."""
    try:
        response = invoke_lambda_function('PUT', entity_type, batch, auth_info)
        
        if response and response.get('success'):
            _track_successful_updates(entity_type, batch_num, batch, results, schema_cache)
        else:
            handle_update_batch_failure(entity_type, batch, response, results, schema_cache)
            
    except Exception as e:
        handle_update_batch_error(entity_type, batch, e, results, schema_cache)

def _track_successful_updates(entity_type: str, batch_num: int, batch: EntityData, 
                            results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """Track successful UPDATE operations, excluding entities created in this run."""
    created_entity_ids = _get_created_entity_ids(entity_type, results, schema_cache)
    updates_to_track = _filter_updates_to_track(batch, entity_type, created_entity_ids, schema_cache)
    
    if updates_to_track:
        if entity_type not in results.updated_items:
            results.updated_items[entity_type] = []
        results.updated_items[entity_type].extend(updates_to_track)
    
    excluded_count = len(batch) - len(updates_to_track)
    logger.info(f"Batch {batch_num} for {entity_type}: {len(updates_to_track)} updated successfully (excluding {excluded_count} created entities)")

def _get_created_entity_ids(entity_type: str, results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> set:
    """Get set of entity IDs that were created in this run."""
    created_entity_ids = set()
    if entity_type in results.created_items:
        id_field = get_id_field(entity_type, schema_cache)
        for created_item in results.created_items[entity_type]:
            if id_field in created_item:
                created_entity_ids.add(created_item[id_field])
    return created_entity_ids

def _filter_updates_to_track(batch: EntityData, entity_type: str, created_entity_ids: set, schema_cache: Dict[str, Dict[str, Any]] = None) -> EntityData:
    """Filter batch to only include entities that weren't created in this run."""
    id_field = get_id_field(entity_type, schema_cache)
    return [entity for entity in batch if entity.get(id_field) not in created_entity_ids]

def handle_update_batch_failure(entity_type: str, batch: EntityData, response: Dict[str, Any], 
                               results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Handle failure of an UPDATE batch.
    
    Args:
        entity_type: Type of entity that failed
        batch: Batch of entities that failed
        response: API response with error details
        results: Results to update
        schema_cache: Schema cache for field name resolution
    """
    api_errors = response.get('api_errors', {}) if response else {}
    error_message = f"PUT request failed: {api_errors.get('error', 'Unknown error')}"
    
    name_field = get_name_field(entity_type, schema_cache)
    
    # Track each entity in the batch as failed
    for entity in batch:
        entity_name = entity.get(name_field, 'unknown')
        
        # Add to update failures
        if entity_type not in results.update_failures:
            results.update_failures[entity_type] = {}
        
        results.update_failures[entity_type][entity_name] = FailureDetails(
            data=entity,
            error_message=error_message
        )
    
    logger.error(f"Batch failed for {entity_type}: {len(batch)} entities failed - {error_message}")

def handle_update_batch_error(entity_type: str, batch: EntityData, error: Exception, 
                             results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Handle error during UPDATE batch processing.
    
    Args:
        entity_type: Type of entity that failed
        batch: Batch of entities that failed
        error: Exception that occurred
        results: Results to update
        schema_cache: Schema cache for field name resolution
    """
    error_message = f"PUT request error: {str(error)}"
    
    name_field = get_name_field(entity_type, schema_cache)
    
    # Track each entity in the batch as failed
    for entity in batch:
        entity_name = entity.get(name_field, 'unknown')
        
        # Add to update failures
        if entity_type not in results.update_failures:
            results.update_failures[entity_type] = {}
        
        results.update_failures[entity_type][entity_name] = FailureDetails(
            data=entity,
            error_message=error_message
        )
    
    logger.error(f"Batch error for {entity_type}: {len(batch)} entities failed - {error_message}")

def handle_update_entity_type_failure(entity_type: str, entity_data: EntityData, error: Exception, 
                                     results: ProcessingResults, schema_cache: Dict[str, Dict[str, Any]] = None) -> None:
    """
    Handle failure of entire entity type during UPDATE phase.
    
    Args:
        entity_type: Type of entity that failed
        entity_data: All entities of this type
        error: Exception that occurred
        results: Results to update
        schema_cache: Schema cache for field name resolution
    """
    error_message = f"Entity type update failed: {str(error)}"
    
    name_field = get_name_field(entity_type, schema_cache)
    
    # Track all entities as failed
    for entity in entity_data:
        entity_name = entity.get(name_field, 'unknown')
        
        # Add to update failures
        if entity_type not in results.update_failures:
            results.update_failures[entity_type] = {}
        
        results.update_failures[entity_type][entity_name] = FailureDetails(
            data=entity,
            error_message=error_message
        )
    
    logger.error(f"Entity type {entity_type} update failed: {len(entity_data)} entities failed - {error_message}")