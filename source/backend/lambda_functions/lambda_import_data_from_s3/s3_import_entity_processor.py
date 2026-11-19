"""
Entity Processing Module

This module handles entity data processing including ULID generation,
cross-reference resolution, and entity transformation operations.

Author: AWS Migration Factory Team
"""

from typing import Dict, List, Any, Optional
from ulid import ULID
from request import Entity
from results import ProcessingResults, FailureDetails
from cmf_logger import logger
from s3_import_dynamodb_operations import fetch_all_entities_for_import
from s3_import_exceptions import EntityProcessingError
import json

def process_entities_for_import(entities_to_create: List[Entity], entities_to_update: List[Entity], 
                               schema_cache: Dict[str, Dict[str, Any]], results: ProcessingResults) -> Dict[str, Any]:
    """
    Process entities for import: generate ULIDs, extract cross-references, build mappings.
    
    Args:
        entities_to_create: List of entities to create
        entities_to_update: List of entities to update
        schema_cache: Cache of all schemas
        results: Results tracking object
        
    Returns:
        dict: Processed data with entities_to_create, entities_to_update, and name_to_id_map
    """
    try:
        # Step 1: Generate ULIDs and organize entities by type
        processed_creates = prepare_entities_for_creation(entities_to_create, schema_cache)
        processed_updates = group_entities_by_type(entities_to_update)
        
        # Step 2: Build name-to-ID mapping from pre-loaded backend
        name_to_id_map = load_existing_entities(schema_cache)
        
        # Step 3: Validate entity existence, move between create/update, and validate cross-references
        validate_and_move_entities(processed_creates, processed_updates, results, name_to_id_map, schema_cache)
        
        # Step 4: Extract cross-references from CREATE entities and move to UPDATE
        move_relationships_to_updates(processed_creates, processed_updates, schema_cache)
        
        # Step 5: Add bi-directional cross-references
        add_bidirectional_cross_references(processed_creates, processed_updates, schema_cache, name_to_id_map)
        
        # Step 6: Resolve cross-reference names to IDs for UPDATE entities
        resolve_cross_references_to_ids(processed_updates, name_to_id_map, schema_cache)
        logger.info(f"Entities processed for import - processed_creates: {json.dumps(processed_creates, indent=2)}")
        logger.info(f"Entities processed for import - processed_updates: {json.dumps(processed_updates, indent=2)}")
        return {
            'entities_to_create': processed_creates,
            'entities_to_update': processed_updates,
            'name_to_id_map': name_to_id_map
        }
        
    except Exception as e:
        logger.error(f"Failed to process entities for import: {e}")
        raise EntityProcessingError(f"Failed to process entities for import: {e}") from e

def prepare_entities_for_creation(entities: List[Entity], schema_cache: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate ULIDs for entities and organize by type.
    
    Args:
        entities: List of entities to process
        schema_cache: Schema cache for field name resolution
        
    Returns:
        dict: Entities organized by type with ULIDs generated
    """
    organized_entities = {}
    
    for entity in entities:
        entity_name = normalize_entity_name(entity)
        processed_data = generate_ulids_for_entity(entity, entity_name, schema_cache)
        organized_entities[entity_name] = processed_data
    
    return organized_entities

def group_entities_by_type(entities: List[Entity]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Organize entities by type without generating ULIDs (for updates).
    
    Args:
        entities: List of entities to organize
        
    Returns:
        dict: Entities organized by type
    """
    organized_entities = {}
    
    for entity in entities:
        entity_name = normalize_entity_name(entity)
        entity_data = list(entity.data.values())
        organized_entities[entity_name] = entity_data
    
    return organized_entities

def load_existing_entities(schema_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Load existing entities from backend and build name-to-ID mapping.
    
    Args:
        schema_cache: Cache of all schemas
        
    Returns:
        dict: Name-to-ID mappings {entity_type: {name: id}}
    """
    return fetch_all_entities_for_import(schema_cache)

def normalize_entity_name(entity: Entity) -> str:
    """
    Normalize entity name (convert 'application' to 'app').
    
    Args:
        entity: Entity to normalize
        
    Returns:
        str: Normalized entity name
    """
    if entity.entityName == 'application':
        return 'app'
    else:
        return entity.entityName

def get_name_field(entity_type: str, schema_cache: Dict[str, Dict[str, Any]] = None) -> str:
    """Get the name field for an entity type (API format)."""
    if entity_type == 'app':
        return 'app_name'
    elif is_custom_asset_type(entity_type, schema_cache):
        return f'{entity_type}_name'  # API expects {schema_name}_name format
    else:
        return f'{entity_type}_name'

def get_id_field(entity_type: str, schema_cache: Dict[str, Dict[str, Any]] = None) -> str:
    """Get the ID field for an entity type (API format)."""
    if entity_type == 'app':
        return 'app_id'
    elif is_custom_asset_type(entity_type, schema_cache):
        return f'{entity_type}_id'  # API expects {schema_name}_id format
    else:
        return f'{entity_type}_id'

def is_custom_asset_type(entity_type: str, schema_cache: Dict[str, Dict[str, Any]] = None) -> bool:
    """Check if entity type is a custom asset."""
    if schema_cache and entity_type in schema_cache:
        return schema_cache[entity_type].get('schema_type') == 'custom'
    # Fallback: assume standard entities if no schema cache
    standard_entities = {'application', 'app', 'server', 'wave'}
    return entity_type not in standard_entities

def generate_ulids_for_entity(entity: Entity, entity_name: str, schema_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate ULIDs for a single entity.
    
    Args:
        entity: Entity to process
        entity_name: Normalized entity name
        schema_cache: Schema cache for field name resolution
        
    Returns:
        list: Processed entity data with ULIDs
    """
    if not entity or not entity.data:
        logger.warning(f"Entity {entity_name} has no data to process")
        return []
    
    processed_data = []
    id_field = get_id_field(entity_name, schema_cache)
    
    for key, item in entity.data.items():
        try:
            if not isinstance(item, dict):
                logger.error(f"Invalid item in {entity_name} at key {key}: must be a dictionary")
                continue
            
            new_item = item.copy()
            
            # Generate ULID if ID not already specified
            if id_field not in new_item or not new_item[id_field]:
                new_item[id_field] = str(ULID())
            
            processed_data.append(new_item)
                
        except Exception as e:
            logger.error(f"Failed to process item {key} in {entity_name}: {e}")
    
    return processed_data

def validate_all_cross_references(processed_creates: Dict[str, List[Dict[str, Any]]],
                                 processed_updates: Dict[str, List[Dict[str, Any]]],
                                 name_to_id_map: Dict[str, Dict[str, str]],
                                 results: ProcessingResults,
                                 schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Validate cross-references for both CREATE and UPDATE entities.
    Remove entities with invalid references to prevent broken operations.
    """
    # Validate CREATE entities
    _validate_entity_list(processed_creates, name_to_id_map, results, schema_cache, is_create_list=True)
    
    # Validate UPDATE entities  
    _validate_entity_list(processed_updates, name_to_id_map, results, schema_cache, is_create_list=False)

def _validate_entity_list(entity_dict: Dict[str, List[Dict[str, Any]]],
                         name_to_id_map: Dict[str, Dict[str, str]],
                         results: ProcessingResults,
                         schema_cache: Dict[str, Dict[str, Any]],
                         is_create_list: bool = False) -> None:
    """
    Validate cross-references for a dictionary of entity lists.
    """
    for entity_type, entities in list(entity_dict.items()):
        schema = schema_cache.get(entity_type, {})
        cross_ref_attrs = get_cross_reference_attributes(schema)
        
        if not cross_ref_attrs:
            continue
            
        entities_to_remove = []
        
        for i, entity in enumerate(entities):
            entity_name = entity.get(get_name_field(entity_type, schema_cache), f"item_{i}")
            invalid_refs = []
            
            for attr_name in cross_ref_attrs:
                if attr_name in entity and entity[attr_name]:
                    attr_value = entity[attr_name]
                    if not _can_resolve_cross_reference(attr_value, name_to_id_map):
                        invalid_refs.append(attr_name)
            
            if invalid_refs:
                _track_invalid_reference_failure(entity_type, entity_name, entity, invalid_refs, results, is_create_list)
                entities_to_remove.append(i)
        
        # Remove entities with invalid cross-references
        for i in reversed(entities_to_remove):
            entities.pop(i)

def _can_resolve_cross_reference(value: Any, name_to_id_map: Dict[str, Dict[str, str]]) -> bool:
    """
    Check if cross-reference value can be resolved without modifying it.
    """
    if isinstance(value, list):
        return all(find_id_by_name(item, name_to_id_map) is not None or is_valid_id(item) for item in value)
    else:
        return find_id_by_name(value, name_to_id_map) is not None or is_valid_id(value)

def move_relationships_to_updates(processed_creates: Dict[str, List[Dict[str, Any]]], 
                                 processed_updates: Dict[str, List[Dict[str, Any]]],
                                 schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Extract cross-references from CREATE entities and move them to UPDATE entities.
    
    Args:
        processed_creates: Entities being created
        processed_updates: Entities being updated (will be modified)
        schema_cache: Cache of all schemas
    """
    for entity_type, entities in processed_creates.items():
        schema = schema_cache.get(entity_type, {})
        cross_ref_attrs = get_cross_reference_attributes(schema)
        
        if not cross_ref_attrs:
            continue
            
        # Extract cross-references from each entity
        for entity in entities:
            cross_refs_to_move = {}
            
            for attr_name in cross_ref_attrs:
                if attr_name in entity and entity[attr_name]:
                    cross_refs_to_move[attr_name] = entity[attr_name]
                    del entity[attr_name]  # Remove from CREATE data
            
            # Add to UPDATE list if there are cross-references to move
            if cross_refs_to_move:
                if entity_type not in processed_updates:
                    processed_updates[entity_type] = []
                
                # Create update record with ID and cross-references
                id_field = get_id_field(entity_type, schema_cache)
                update_record = {
                    id_field: entity[id_field],
                    **cross_refs_to_move
                }
                processed_updates[entity_type].append(update_record)

def get_cross_reference_attributes(schema: Dict[str, Any]) -> List[str]:
    """
    Get list of cross-reference attribute names from schema.
    
    Args:
        schema: Entity schema
        
    Returns:
        list: List of cross-reference attribute names
    """
    cross_ref_attrs = []
    attributes = schema.get('attributes', [])
    
    for attr in attributes:
        if attr.get('type') in ['relationship', 'multivalue-relationship']:
            attr_name = attr.get('name')
            if attr_name:
                cross_ref_attrs.append(attr_name)
    
    return cross_ref_attrs

def add_bidirectional_cross_references(processed_creates: Dict[str, List[Dict[str, Any]]], 
                                      processed_updates: Dict[str, List[Dict[str, Any]]],
                                      schema_cache: Dict[str, Dict[str, Any]],
                                      name_to_id_map: Dict[str, Dict[str, str]]) -> None:
    """
    Add bi-directional cross-references to UPDATE entities.
    """
    all_entities = _combine_create_and_update_entities(processed_creates, processed_updates)
    
    for entity_type, entities in all_entities.items():
        _process_entity_type_references(entity_type, entities, processed_updates, 
                                      schema_cache, name_to_id_map)

def _combine_create_and_update_entities(processed_creates: Dict[str, List[Dict[str, Any]]], 
                                      processed_updates: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """Combine CREATE and UPDATE entities into single dictionary."""
    all_entities = {}
    
    for entity_type, entities in processed_creates.items():
        if entity_type not in all_entities:
            all_entities[entity_type] = []
        all_entities[entity_type].extend(entities)
    
    for entity_type, entities in processed_updates.items():
        if entity_type not in all_entities:
            all_entities[entity_type] = []
        all_entities[entity_type].extend(entities)
    
    return all_entities

def _process_entity_type_references(entity_type: str, entities: List[Dict[str, Any]], 
                                  processed_updates: Dict[str, List[Dict[str, Any]]],
                                  schema_cache: Dict[str, Dict[str, Any]],
                                  name_to_id_map: Dict[str, Dict[str, str]]) -> None:
    """Process references for all entities of a given type."""
    schema = schema_cache.get(entity_type, {})
    cross_ref_attrs = get_cross_reference_attributes_with_targets(schema)
    
    for entity in entities:
        entity_name = entity.get(get_name_field(entity_type, schema_cache))
        entity_id = entity.get(get_id_field(entity_type, schema_cache))
        
        if not entity_name or not entity_id:
            continue
            
        _process_single_entity_references(entity_type, entity_name, entity_id, entity, 
                                        cross_ref_attrs, processed_updates, 
                                        schema_cache, name_to_id_map)

def _process_single_entity_references(entity_type: str, entity_name: str, entity_id: str,
                                    entity: Dict[str, Any], cross_ref_attrs: Dict[str, str],
                                    processed_updates: Dict[str, List[Dict[str, Any]]],
                                    schema_cache: Dict[str, Dict[str, Any]],
                                    name_to_id_map: Dict[str, Dict[str, str]]) -> None:
    """Process references for a single entity."""
    # Process references from the main entity data
    for attr_name, target_entity_type in cross_ref_attrs.items():
        if attr_name in entity:
            referenced_names = entity[attr_name]
            if not isinstance(referenced_names, list):
                referenced_names = [referenced_names]
            
            if referenced_names:
                add_reverse_references(entity_type, entity_name, target_entity_type, 
                                     referenced_names, processed_updates, schema_cache, name_to_id_map)
    
    # Also process any additional references from update records
    update_entities = processed_updates.get(entity_type, [])
    entity_updates = [u for u in update_entities if u.get(get_id_field(entity_type, schema_cache)) == entity_id]
    
    for update_entity in entity_updates:
        for attr_name, target_entity_type in cross_ref_attrs.items():
            if attr_name in update_entity and attr_name not in entity:
                referenced_names = update_entity[attr_name]
                if not isinstance(referenced_names, list):
                    referenced_names = [referenced_names]
                
                if referenced_names:
                    add_reverse_references(entity_type, entity_name, target_entity_type, 
                                         referenced_names, processed_updates, schema_cache, name_to_id_map)


def get_cross_reference_attributes_with_targets(schema: Dict[str, Any]) -> Dict[str, str]:
    """
    Get cross-reference attributes with their target entity types.
    
    Args:
        schema: Entity schema
        
    Returns:
        dict: {attr_name: target_entity_type}
    """
    cross_ref_attrs = {}
    attributes = schema.get('attributes', [])
    
    for attr in attributes:
        if attr.get('type') in ['relationship', 'multivalue-relationship']:
            attr_name = attr.get('name')
            rel_entity = attr.get('rel_entity')
            if attr_name and rel_entity:
                # Normalize entity name
                normalized_rel_entity = 'app' if rel_entity == 'application' else rel_entity
                cross_ref_attrs[attr_name] = normalized_rel_entity
    
    return cross_ref_attrs

def add_reverse_references(source_entity_type: str, source_entity_name: str, 
                          target_entity_type: str, target_entity_names: List[str],
                          processed_updates: Dict[str, List[Dict[str, Any]]],
                          schema_cache: Dict[str, Dict[str, Any]],
                          name_to_id_map: Dict[str, Dict[str, str]]) -> None:
    """
    Add reverse cross-references to target entities.
    """
    target_schema = schema_cache.get(target_entity_type, {})
    reverse_attr = find_reverse_cross_reference_attribute(target_schema, source_entity_type)
    
    if not reverse_attr:
        return  # No bi-directional relationship
    
    source_entity_id = name_to_id_map.get(source_entity_type, {}).get(source_entity_name)
    if not source_entity_id:
        return
    
    if target_entity_type not in processed_updates:
        processed_updates[target_entity_type] = []
    
    for target_name in target_entity_names:
        _add_single_reverse_reference(target_entity_type, target_name, reverse_attr, 
                                    source_entity_name, processed_updates, name_to_id_map, schema_cache)

def _add_single_reverse_reference(target_entity_type: str, target_name: str, 
                                reverse_attr: str, source_entity_name: str,
                                processed_updates: Dict[str, List[Dict[str, Any]]],
                                name_to_id_map: Dict[str, Dict[str, str]], 
                                schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """Add reverse reference to a single target entity."""
    target_id = name_to_id_map.get(target_entity_type, {}).get(target_name)
    if not target_id:
        return
        
    existing_update = _find_or_create_update_record(target_entity_type, target_id, processed_updates, schema_cache)
    _add_to_reference_list(existing_update, reverse_attr, source_entity_name)

def _find_or_create_update_record(target_entity_type: str, target_id: str,
                                processed_updates: Dict[str, List[Dict[str, Any]]], 
                                schema_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Find existing update record or create new one."""
    target_id_field = get_id_field(target_entity_type, schema_cache)
    
    for update in processed_updates[target_entity_type]:
        if update.get(target_id_field) == target_id:
            return update
    
    new_update = {target_id_field: target_id}
    processed_updates[target_entity_type].append(new_update)
    return new_update

def _add_to_reference_list(update_record: Dict[str, Any], attr_name: str, entity_name: str) -> None:
    """Add entity name to reference list in update record."""
    if attr_name not in update_record:
        update_record[attr_name] = []
    elif not isinstance(update_record[attr_name], list):
        update_record[attr_name] = [update_record[attr_name]]
    
    if entity_name not in update_record[attr_name]:
        update_record[attr_name].append(entity_name)

def find_reverse_cross_reference_attribute(schema: Dict[str, Any], referenced_entity_type: str) -> Optional[str]:
    """
    Find the attribute in the schema that references the given entity type.
    
    Args:
        schema: Entity schema
        referenced_entity_type: The entity type to find references to
        
    Returns:
        str: Attribute name that references the entity type, or None if not found
    """
    attributes = schema.get('attributes', [])
    for attr in attributes:
        if attr.get('rel_entity') == referenced_entity_type:
            return attr.get('name')
    return None

def resolve_cross_references_to_ids(processed_updates: Dict[str, List[Dict[str, Any]]],
                                   name_to_id_map: Dict[str, Dict[str, str]],
                                   schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Resolve cross-reference names to IDs (validation already done early).
    """
    for entity_type, entities in processed_updates.items():
        schema = schema_cache.get(entity_type, {})
        cross_ref_attrs = get_cross_reference_attributes(schema)
        
        for entity in entities:
            for attr_name in cross_ref_attrs:
                if attr_name in entity:
                    attr_value = entity[attr_name]
                    if isinstance(attr_value, list):
                        resolved_list = []
                        for item in attr_value:
                            resolved_id = find_id_by_name(item, name_to_id_map)
                            resolved_list.append(resolved_id if resolved_id else item)
                        entity[attr_name] = resolved_list
                    elif isinstance(attr_value, str):
                        resolved_id = find_id_by_name(attr_value, name_to_id_map)
                        if resolved_id:
                            entity[attr_name] = resolved_id

def _track_invalid_reference_failure(entity_type: str, entity_name: str, entity: Dict[str, Any],
                                   invalid_refs: List[str], results: ProcessingResults, is_create: bool = False) -> None:
    """Track entity with invalid cross-references as failure."""
    failure_dict = results.create_failures if is_create else results.update_failures
    
    if entity_type not in failure_dict:
        failure_dict[entity_type] = {}
    
    failure_dict[entity_type][entity_name] = FailureDetails(
        data=entity.copy(),
        error_message=f"Cross-reference validation failed for attributes: {', '.join(invalid_refs)}"
    )

def resolve_cross_reference_value(value: Any, name_to_id_map: Dict[str, Dict[str, str]]) -> Any:
    """
    Resolve cross-reference value (name or list of names) to IDs.
    
    Args:
        value: Cross-reference value to resolve
        name_to_id_map: Name-to-ID mappings
        
    Returns:
        Resolved value (ID or list of IDs)
    """
    if isinstance(value, list):
        resolved_list = []
        for item in value:
            resolved_id = find_id_by_name(item, name_to_id_map)
            if resolved_id:
                resolved_list.append(resolved_id)
        return resolved_list if resolved_list else value
    else:
        resolved_id = find_id_by_name(value, name_to_id_map)
        return resolved_id if resolved_id else value

def find_id_by_name(name: str, name_to_id_map: Dict[str, Dict[str, str]]) -> Optional[str]:
    """
    Find ID by name across all entity types.
    
    Args:
        name: Entity name to find
        name_to_id_map: Name-to-ID mappings
        
    Returns:
        Entity ID if found, None otherwise
    """
    for entity_type, mappings in name_to_id_map.items():
        if name in mappings:
            return mappings[name]
    return None

def is_valid_id(value: Any) -> bool:
    """
    Check if value looks like a valid ID (ULID format).
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if looks like a valid ID
    """
    if isinstance(value, str) and len(value) == 26:
        return True  # Assume ULID format
    return False



def validate_and_move_entities(processed_creates: Dict[str, List[Dict[str, Any]]], 
                              processed_updates: Dict[str, List[Dict[str, Any]]],
                              results: ProcessingResults,
                              name_to_id_map: Dict[str, Dict[str, str]], 
                              schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Validate entity existence using pre-loaded data and move between create/update.
    
    Args:
        processed_creates: Entities to create (will be modified)
        processed_updates: Entities to update (will be modified)
        results: Results tracking object
        name_to_id_map: Pre-loaded name-to-ID mappings (will be modified)
        schema_cache: Schema cache for field name resolution
    """
    move_existing_creates_to_updates(processed_creates, processed_updates, name_to_id_map, schema_cache)
    remove_non_existing_updates(processed_updates, results, name_to_id_map, schema_cache)
    add_new_creates_to_mapping(processed_creates, name_to_id_map, schema_cache)
    
    # Validate cross-references for all entities
    validate_all_cross_references(processed_creates, processed_updates, name_to_id_map, results, schema_cache)

def move_existing_creates_to_updates(processed_creates: Dict[str, List[Dict[str, Any]]], 
                                    processed_updates: Dict[str, List[Dict[str, Any]]],
                                    name_to_id_map: Dict[str, Dict[str, str]], 
                                    schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Move entities that already exist from create list to update list using pre-loaded data.
    
    Args:
        processed_creates: Entities to create (will be modified)
        processed_updates: Entities to update (will be modified)
        name_to_id_map: Pre-loaded name-to-ID mappings
        schema_cache: Schema cache for field name resolution
    """
    for entity_type, entities in list(processed_creates.items()):
        if not entities or entity_type not in name_to_id_map:
            continue
            
        existing_names = set(name_to_id_map[entity_type].keys())
        name_field = get_name_field(entity_type, schema_cache)
        id_field = get_id_field(entity_type, schema_cache)
        
        entities_to_move = [e for e in entities if e.get(name_field) in existing_names]
        entities_to_keep = [e for e in entities if e.get(name_field) not in existing_names]
        
        if entities_to_move:
            if entity_type not in processed_updates:
                processed_updates[entity_type] = []
            
            # Set correct IDs from pre-loaded data
            for entity in entities_to_move:
                entity_name = entity.get(name_field)
                entity[id_field] = name_to_id_map[entity_type][entity_name]
            
            processed_updates[entity_type].extend(entities_to_move)
            processed_creates[entity_type] = entities_to_keep
            
            logger.info(f"Moved {len(entities_to_move)} existing {entity_type} entities from create to update")

def remove_non_existing_updates(processed_updates: Dict[str, List[Dict[str, Any]]], 
                               results: ProcessingResults,
                               name_to_id_map: Dict[str, Dict[str, str]], 
                               schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Remove entities that don't exist from update list using pre-loaded data.
    
    Args:
        processed_updates: Entities to update (will be modified)
        results: Results tracking object
        name_to_id_map: Pre-loaded name-to-ID mappings
        schema_cache: Schema cache for field name resolution
    """
    for entity_type, entities in list(processed_updates.items()):
        if not entities or entity_type not in name_to_id_map:
            continue
            
        existing_names = set(name_to_id_map[entity_type].keys())
        name_field = get_name_field(entity_type, schema_cache)
        id_field = get_id_field(entity_type, schema_cache)
        
        entities_to_keep = [e for e in entities if e.get(name_field) in existing_names]
        entities_not_found = [e for e in entities if e.get(name_field) not in existing_names]
        
        # Track non-existent entities as update failures
        for entity in entities_not_found:
            entity_name = entity.get(name_field, 'unknown')
            
            if entity_type not in results.update_failures:
                results.update_failures[entity_type] = {}
            
            results.update_failures[entity_type][entity_name] = FailureDetails(
                data=entity.copy(),
                error_message=f"Entity '{entity_name}' does not exist and cannot be updated"
            )
        
        # Populate ID fields for entities that exist
        for entity in entities_to_keep:
            entity_name = entity.get(name_field)
            entity[id_field] = name_to_id_map[entity_type][entity_name]
        
        processed_updates[entity_type] = entities_to_keep
        
        if entities_not_found:
            logger.info(f"Marked {len(entities_not_found)} non-existing {entity_type} entities as update failures")
        if entities_to_keep:
            logger.info(f"Populated IDs for {len(entities_to_keep)} existing {entity_type} entities in update list")

def add_new_creates_to_mapping(processed_creates: Dict[str, List[Dict[str, Any]]], 
                              name_to_id_map: Dict[str, Dict[str, str]], 
                              schema_cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Add new entities being created to the name-to-ID mapping.
    
    Args:
        processed_creates: Entities to create (after existing ones moved to updates)
        name_to_id_map: Name-to-ID mappings (will be modified)
        schema_cache: Schema cache for field name resolution
    """
    for entity_type, entities in processed_creates.items():
        if not entities:
            continue
            
        if entity_type not in name_to_id_map:
            name_to_id_map[entity_type] = {}
        
        name_field = get_name_field(entity_type, schema_cache)
        id_field = get_id_field(entity_type, schema_cache)
        
        for entity in entities:
            name = entity.get(name_field)
            entity_id = entity.get(id_field)
            if name and entity_id:
                name_to_id_map[entity_type][name] = entity_id
