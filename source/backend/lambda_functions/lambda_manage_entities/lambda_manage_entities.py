"""
Lambda function for managing entities in DynamoDB for the Migration Factory solution.

This function supports two main operations:
1. Cleanup: Delete entities and update all references
2. Move: Move entities between containers and update relationships

Entity types supported: wpm_job, move_group, wave, app, server, database, and move_group_request

Author: AWS Professional Services

## Relationship Cache Structure

The relationship_cache is a central data structure that tracks relationships between different entity types.
It's organized as a nested dictionary with the following structure:

{
  "<entity_type>": {
    "outgoing": {
      "<related_entity_type>": ["<attribute_name>", ...],  # List of attribute names in this entity that reference related entities
    },
    "incoming": {
      "<related_entity_type>": ["<attribute_name>", ...],  # List of attribute names in related entities that reference this entity
    },
    "parents": ["<parent_entity_type>", ...],  # Entity types that are parents of this entity
    "children": ["<child_entity_type>", ...],  # Entity types that are children of this entity
    "parent_ids": {
      "<entity_id>": {
        "<parent_type>": ["<parent_id>", ...],  # Parent entities that reference this entity
      }
    },
    "child_ids": {
      "<entity_id>": {
        "<child_type>": ["<child_id>", ...],  # Child entities referenced by this entity
      }
    }
  }
}

Example (simplified):

{
  "wave": {
    "outgoing": {
      "move_group": ["move_group_ids"],  # Wave references move_groups via move_group_ids attribute
      "app": ["app_ids"]                 # Wave references apps via app_ids attribute
    },
    "incoming": {
      "wpm_job": ["wave_ids"]            # WPM job references waves via wave_ids attribute
    },
    "parents": ["wpm_job"],              # Waves have wpm_job as parent
    "children": ["move_group", "app"],   # Waves have move_groups and apps as children
    "parent_ids": {
      "wave-1": {                        # For wave-1
        "wpm_job": ["job-1"]             # Its parent is job-1
      }
    },
    "child_ids": {
      "wave-1": {                        # For wave-1
        "move_group": ["mg-1", "mg-2"],  # Its children are mg-1 and mg-2
        "app": ["app-1", "app-2"]        # And app-1 and app-2
      }
    }
  }
}

This structure enables efficient traversal of entity relationships in both directions
and is used for operations like cleanup (cascading deletes) and move (updating references).
"""

import os
import json
import logging
import re
import traceback
from typing import Dict, List
from botocore.exceptions import ClientError
from relationship_schema import build_relationship_schema_cache, get_entity_types
from dynamodb_operations import (
    DynamoDBManager,
    set_default
)
from entity_management import (
    EntityManager,
    group_entities_by_type
)
from wave_relationship_utils import update_app_wave_relationships
from cmf_utils import default_http_headers
from item_validation import validate_id_string, validate_id_list

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Get environment variables for table names
TABLES = {
    "wpm_job": os.environ.get("WPM_JOBS_TABLE_NAME"),
    "wave": os.environ.get("WAVES_TABLE_NAME"),
    "move_group": os.environ.get("MOVE_GROUPS_TABLE_NAME"),
    "app": os.environ.get("APPS_TABLE_NAME"),
    "server": os.environ.get("SERVERS_TABLE_NAME"),
    "database": os.environ.get("DATABASES_TABLE_NAME"),
    "move_group_request": os.environ.get("MOVE_GROUP_REQUESTS_TABLE_NAME"),
    "schema": os.environ.get("SCHEMA_TABLE_NAME"),
    "custom_assets": os.environ.get("CUSTOM_ASSETS_TABLE_NAME"),
}

# Constants for entity types and relationships
APP_CHILD_ASSETS = ["server", "database"]
PRESERVED_CHILD_TYPES = ["app", "server", "database"]
CONTAINER_TYPES = ["move_group", "wave"]
APP_REFERENCE_ATTRS = ["app_id", "app_ids"]
# The max number of entity IDs cleanup operation can take
# Need fine-tuning.Not efficient if too small, Might take too long to run if too big
CLEANUP_MAX_ENTITY_SIZE = 200

# Validation constants
MAX_ENTITY_IDS_COUNT = 200
MAX_TARGET_ENTITIES_COUNT = 100

# Define global variables at module level. They will never be undeclared during the lifespan of the lambda instance
# but will be ressigned to {} at the beginning of each lambda invocation. When used in a method in the module,
# first declare global by `global var_name`` to ensure the method modifies the global var, not creates a new local var that shadows the global one
# Global relationship cache
relationship_cache = {}

# Global entity cache
entity_cache = {}

# Global schema cache for custom asset types
schema_cache = {}

# Central dictionary to track relationship updates
relationship_updates = {}

# Entity manager instance
entity_manager = None

# DynamoDB manager instance
dynamodb_manager = None


# Using functions from entity_management module
def build_entity_cache():
    """
    Build the entity cache by loading entities from DynamoDB tables.
    Uses pagination to handle large tables efficiently.
    """
    # This declaration will make sure any modification to entity_cache will be saved to the module's global var entity_cache
    # Without this global declaration, you will create a new entity_cache variable that is local to this function
    global entity_cache

    # Get entity types from the relationship_schema module
    # Build the entity cache with data from DynamoDB
    entity_types = get_entity_types(schema_cache)

    # Use the DynamoDBManager to build the entity cache
    entity_cache = dynamodb_manager.build_entity_cache(entity_types, entity_cache, entity_manager)


def build_schema_cache():
    """
    Build the schema cache by loading all schemas from the schema table.
    This is done once during initialization to avoid repeated database calls.
    """
    global schema_cache

    try:
        schema_table = dynamodb_manager.get_schema_table()
        response = schema_table.scan()

        custom_asset_types = []
        for item in response.get("Items", []):
            schema_name = item["schema_name"]
            schema_cache[schema_name] = item

            if item.get("schema_type") == "custom":
                custom_asset_types.append(schema_name)

        schema_cache["_custom_asset_types"] = custom_asset_types
        logger.info(f"Built schema cache with {len(schema_cache)} schemas, {len(custom_asset_types)} custom asset types")
    except Exception as e:
        logger.error(f"Error building schema cache: {str(e)}")
        schema_cache["_custom_asset_types"] = []


def build_relationship_cache():
    """
    Build a cache of relationships between entity types based on schema information.
    This cache is used to efficiently determine how to update related entities during operations.

    The relationship_cache has two main parts:
    1. Schema-based structure (outgoing, incoming, parents, children) - built from the schema table
    2. Entity-based structure (parent_ids, child_ids) - populated from actual entity data

    The cache enables efficient:
    - Traversal of entity hierarchies (parent/child relationships)
    - Identification of affected entities during operations
    - Tracking of bidirectional relationships
    """
    logger.info("Building relationship cache")
    schema_table = dynamodb_manager.get_schema_table()

    # Build the schema cache first
    build_schema_cache()

    # Build the schema portion of the relationship cache
    build_relationship_schema_cache(schema_cache, relationship_cache, schema_table)
    build_entity_cache()
    entity_manager.set_entity_cache(entity_cache)

    logger.info("Relationship cache built successfully with entity IDs")
    logger.info(
        f"Relationship cache structure: {json.dumps({k: len(v) for k, v in relationship_cache.items()}, default=set_default)}"
    )


# Using set_default from dynamodb_operations module


def get_entity(entity_type: str, entity_id: str) -> Dict:
    """
    Retrieve an entity from the entity cache or from its corresponding DynamoDB table.

    Args:
        entity_type: Type of the entity (e.g., 'app', 'server')
        entity_id: ID of the entity

    Returns:
        The entity as a dictionary or None if not found
    """
    return entity_manager.get_entity(entity_type, entity_id)


def delete_entity(entity_type: str, entity_id: str) -> bool:
    """
    Track entity deletion in the central dictionary without deleting from DynamoDB.

    Args:
        entity_type: Type of the entity (e.g., 'app', 'server')
        entity_id: ID of the entity

    Returns:
        True always as we're just tracking changes
    """
    return entity_manager.delete_entity(entity_type, entity_id)


def update_entity(entity_type: str, entity_id: str, updates: Dict) -> bool:
    """
    Track entity updates in the central dictionary without updating DynamoDB.
    Also updates the entity cache to ensure consistent state.

    Args:
        entity_type: Type of the entity (e.g., 'app', 'server')
        entity_id: ID of the entity
        updates: Dictionary of attribute updates

    Returns:
        True always as we're just tracking changes
    """
    return entity_manager.update_entity(entity_type, entity_id, updates)


def get_related_entities(entity_type: str, entity_id: str) -> Dict[str, List[str]]:
    """
    Get all entities related to the specified entity.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity

    Returns:
        Dictionary mapping entity types to lists of entity IDs
    """
    return entity_manager.get_related_entities(entity_type, entity_id)


def update_relationship(
    entity_type: str, entity_id: str, related_type: str, related_id: str, operation: str
) -> bool:
    """
    Track relationship updates in the central dictionary without updating DynamoDB.

    Args:
        entity_type: Type of the entity to update
        entity_id: ID of the entity to update
        related_type: Type of the related entity
        related_id: ID of the related entity
        operation: 'add' or 'remove'

    Returns:
        True if successful, False otherwise
    """
    return entity_manager.update_relationship(entity_type, entity_id, related_type, related_id, operation)


def update_preserved_entity_references(
    child_type: str, child_ids: set, entity_type: str, entity_id: str
) -> None:
    """
    Update references for entities that should be preserved.

    Args:
        child_type: Type of the child entity
        child_ids: Set of child entity IDs
        entity_type: Type of the parent entity being deleted
        entity_id: ID of the parent entity being deleted
    """
    entity_manager.update_preserved_entity_references(
        child_type, child_ids, entity_type, entity_id, update_app_planning_status
    )


def remove_incoming_references(entity_type: str, entity_id: str, containers_only = False) -> None:
    """
    Remove all incoming references to an entity.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity
        containers_only: If True, only remove references from containers
    """
    entity_manager.remove_incoming_references(entity_type, entity_id, containers_only)


def get_app_ids_from_entity(entity: Dict) -> set:
    """
    Extract app IDs from an entity using standard app reference attributes.

    Args:
        entity: Entity dictionary

    Returns:
        Set of app IDs referenced by the entity
    """
    app_ids = set()
    for attr in APP_REFERENCE_ATTRS:
        if attr in entity and entity[attr]:
            if isinstance(entity[attr], list):
                app_ids.update(entity[attr])
            else:
                app_ids.add(entity[attr])
    return app_ids


def get_container_ids_from_entity(entity: Dict) -> Dict[str, str]:
    """
    Extract container IDs from an entity.

    Args:
        entity: Entity dictionary

    Returns:
        Dictionary mapping container types to their IDs
    """
    containers = {}
    for container_type in CONTAINER_TYPES:
        container_attr = f"{container_type}_id"
        if container_attr in entity and entity[container_attr]:
            containers[container_type] = entity[container_attr]
    return containers


def should_delete_asset(asset_entity: Dict, app_id: str) -> bool:
    """
    Determine if an asset should be deleted when its app is being cleaned up.

    Args:
        asset_entity: The asset entity dictionary
        app_id: ID of the app being cleaned up

    Returns:
        True if asset should be deleted, False otherwise
    """
    app_ids = get_app_ids_from_entity(asset_entity)
    return len(app_ids) == 1 and app_id in app_ids


def handle_app_cleanup(app_id: str, outgoing_refs: Dict) -> None:
    """
    Handle cleanup logic specific to app entities.

    Args:
        app_id: ID of the app being cleaned up
        outgoing_refs: Dictionary of outgoing references from relationship cache
    """
    # Process app child assets (servers/databases and custom assets)
    for asset_type in APP_CHILD_ASSETS + get_custom_asset_types():
        asset_ids = outgoing_refs.get(asset_type, set())
        for asset_id in list(asset_ids):
            asset_entity = get_entity(asset_type, asset_id)
            if not asset_entity:
                continue

            if should_delete_asset(asset_entity, app_id):
                cleanup_entity(asset_type, [asset_id])
            else:
                update_preserved_entity_references(
                    asset_type, {asset_id}, "app", app_id
                )


def get_custom_asset_types() -> List[str]:
    """
    Get list of custom asset types from the schema cache.

    Returns:
        List of custom asset type names
    """
    return schema_cache.get("_custom_asset_types", [])


def update_app_custom_asset_reference(app_id: str, entity_type: str, entity_id: str, operation: str) -> None:
    """
    Update an app's reference to a custom asset.

    Args:
        app_id: ID of the app to update
        entity_type: Type of the custom asset
        entity_id: ID of the custom asset
        operation: 'add' or 'remove'
    """
    app_entity = get_entity("app", app_id)
    if not app_entity:
        return

    asset_ids_attr = f"{entity_type}_ids"
    current_asset_ids = app_entity.get(asset_ids_attr, [])

    if operation == "add" and entity_id not in current_asset_ids:
        current_asset_ids.append(entity_id)
        update_entity("app", app_id, {asset_ids_attr: current_asset_ids})
    elif operation == "remove" and entity_id in current_asset_ids:
        new_asset_ids = [id for id in current_asset_ids if id != entity_id]
        update_entity("app", app_id, {asset_ids_attr: new_asset_ids})


def move_custom_assets(target_entities: List[Dict]) -> Dict:
    """
    Move custom assets by updating only the bidirectional pointers between assets and apps.
    This function handles custom asset moves without requiring source/destination containers.

    Args:
        target_entities: List of custom assets to move with their new app_ids

    Returns:
        Response dictionary with status and results
    """
    logger.info(f"Moving custom assets: {target_entities}")

    results = {}
    has_errors = False

    for target_entity in target_entities:
        entity_type = target_entity["entity_type"]
        entity_id = target_entity["entity_id"]
        new_app_ids = get_app_ids_from_entity(target_entity)

        if entity_type not in results:
            results[entity_type] = []

        # Get current entity
        entity = get_entity(entity_type, entity_id)
        if not entity:
            results[entity_type].append({
                "entity_id": entity_id,
                "status": "error",
                "message": f"{entity_type} with ID {entity_id} not found",
            })
            has_errors = True
            continue

        current_app_ids = get_app_ids_from_entity(entity)

        # Update the custom asset's app_ids
        update_entity(entity_type, entity_id, {"app_ids": list(new_app_ids)})

        # Update app references - remove from apps no longer associated
        for app_id in current_app_ids - new_app_ids:
            update_app_custom_asset_reference(app_id, entity_type, entity_id, "remove")

        # Update app references - add to newly associated apps
        for app_id in new_app_ids - current_app_ids:
            update_app_custom_asset_reference(app_id, entity_type, entity_id, "add")

        results[entity_type].append({
            "entity_id": entity_id,
            "status": "success",
            "message": f"Moved {entity_type} with ID {entity_id}",
        })

    message = "Move operation completed with errors. Check individual entity results for details." if has_errors else "Successfully moved custom assets"

    return {
        "headers": {**default_http_headers},
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": message,
                "results": results,
            },
            default=set_default,
        ),
    }


def move_regular_entities(json_body: Dict, target_entities: List[Dict]) -> Dict:
    """
    Move regular entities between containers (move groups, waves, etc.).
    This function handles the traditional move operation that requires source/destination containers.

    Args:
        json_body: The original request body containing source/destination information
        target_entities: List of regular entities to move

    Returns:
        Response dictionary with status and results
    """
    logger.info(f"Moving regular entities: {target_entities}")

    source_type = json_body.get("source_entity_type")
    source_id = json_body.get("source_entity_id")
    destination_type = json_body.get("destination_entity_type", source_type)
    source_type = source_type if source_type else destination_type
    destination_id = json_body.get("destination_entity_id")

    # Ensure at least one of source_id or destination_id is provided
    if not source_id and not destination_id:
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": json.dumps(
                {
                    "message": "Either source_entity_id or destination_entity_id must be provided for regular entity moves"
                }
            ),
        }

    # If source_type is not provided but source_id is, use destination_type as source_type
    if source_id and not source_type:
        source_type = destination_type

    # Validate entity types
    valid_source = not source_id or source_type in TABLES
    valid_dest = not destination_id or destination_type in TABLES

    if not valid_source or not valid_dest:
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": json.dumps(
                {
                    "message": f"Invalid entity type: {source_type} or {destination_type}"
                }
            ),
        }

    return move_entities(
        source_type,
        source_id,
        destination_type,
        destination_id,
        target_entities,
    )


def handle_asset_cleanup(asset_type: str, asset_id: str) -> None:
    """
    Handle cleanup logic for app child assets (servers/databases).

    Args:
        asset_type: Type of the asset being cleaned up
        asset_id: ID of the asset being cleaned up
    """
    asset_entity = get_entity(asset_type, asset_id)
    if not asset_entity:
        return

    app_ids = get_app_ids_from_entity(asset_entity)
    containers = get_container_ids_from_entity(asset_entity)

    # Remove apps from containers if they have no other assets there
    for app_id in app_ids:
        for container_type, container_id in containers.items():
            ref_count = count_app_references_in_container(
                app_id, container_type, container_id, asset_id, asset_type
            )
            if ref_count == 0:
                update_app_container_relationships(
                    app_id, container_type, container_id, "remove"
                )


def process_child_entities(entity_type: str, entity_id: str, outgoing_refs: Dict) -> None:
    """
    Process child entities using relationship cache structure.

    Args:
        entity_type: Type of the parent entity
        entity_id: ID of the parent entity
        outgoing_refs: Dictionary of outgoing references from relationship cache
    """
    for child_type, child_ids in outgoing_refs.items():
        # Skip parent entities
        if child_type in relationship_cache[entity_type]["parents"]:
            logger.info(f"Preserving {len(child_ids)} {child_type} entities (parent type)")
            continue

        # Skip already processed child types for app cleanup
        if entity_type == "app" and child_type in [*APP_CHILD_ASSETS, *get_custom_asset_types()]:
            continue

        # Handle preserved vs non-preserved child types
        if child_type in PRESERVED_CHILD_TYPES:
            logger.info(f"Preserving {len(child_ids)} {child_type} entities (preserved type)")
            update_preserved_entity_references(child_type, child_ids, entity_type, entity_id)
            # While asset itself is preserved, the references from containers need to be cleaned up
            if child_type != "app":
                for child_id in list(child_ids):
                    handle_asset_cleanup(child_type, child_id)
                    remove_incoming_references(child_type, child_id, True)
                    update_parent_server_count(child_type, child_id)
                    
        else:
            logger.info(f"Tracking deletion of {len(child_ids)} {child_type} entities")
            for child_id in list(child_ids):
                cleanup_entity(child_type, [child_id])


def update_parent_server_count(entity_type: str, entity_id: str) -> None:
    """
    Update server_count for parent entities when a server is deleted.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity
    """
    if entity_type != "server":
        return

    entity = get_entity(entity_type, entity_id)
    if not entity:
        return

    # Update server count for container parents
    containers = get_container_ids_from_entity(entity)
    for container_type, container_id in containers.items():
        update_server_count(container_type, container_id, -1)


def _validate_entity_type(entity_type):
    """
    Validate if an entity type is valid using the schema cache.

    Args:
        entity_type: The entity type to validate

    Returns:
        bool: True if entity type is valid, False otherwise
    """
    return entity_type in TABLES or entity_type in get_custom_asset_types()


def cleanup_entity(entity_type: str, entity_ids: List[str]) -> Dict:
    """
    Track entity deletion and reference updates without modifying DynamoDB.

    Args:
        entity_type: Type of the entity to delete
        entity_ids: list of IDs of the entities to delete

    Returns:
        Dictionary with status, message and relationship updates
    """

    for entity_id in entity_ids:
        logger.info(f"Tracking cleanup for {entity_type} with ID {entity_id}")
        # Check if entity exists (works for both built-in and custom assets)
        entity = get_entity(entity_type, entity_id)
        if not entity:
            return {
                "headers": {**default_http_headers},
                "statusCode": 404,
                "body": json.dumps(
                    {"message": f"{entity_type} with ID {entity_id} not found"}
                ),
            }

        # Get outgoing relationships from cache (only for built-in types)
        outgoing_refs = relationship_cache[entity_type]["child_ids"].get(entity_id, {})
        logger.info(f"Found outgoing references: {outgoing_refs}")

        # Handle entity-specific cleanup logic
        if entity_type == "app":
            handle_app_cleanup(entity_id, outgoing_refs)
        elif entity_type in APP_CHILD_ASSETS:
            handle_asset_cleanup(entity_type, entity_id)

        # Process remaining child entities using relationship cache
        process_child_entities(entity_type, entity_id, outgoing_refs)

        # Remove incoming references to this entity
        remove_incoming_references(entity_type, entity_id)

        # Update server counts if deleting a server
        if entity_type == "server":
            update_parent_server_count(entity_type, entity_id)

        # Track entity deletion
        delete_entity(entity_type, entity_id)

    return {
        "headers": {**default_http_headers},
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": f"Successfully tracked deletion of {entity_type} with IDs {entity_ids}",
            },
            default=set_default,
        ),
    }


def validate_move_entities_input(
    source_id: str, source_type: str, destination_id: str, destination_type: str
) -> Dict:
    """
    Validate input parameters for move_entities function.

    Args:
        source_id: ID of the source container entity
        source_type: Type of the source container entity
        destination_id: ID of the destination container entity
        destination_type: Type of the destination container entity

    Returns:
        Error response dict if validation fails, None if validation passes
    """
    # Ensure at least one of source or destination is provided
    if not source_id and not destination_id:
        logger.error("Both source_id and destination_id cannot be None")
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": json.dumps(
                {"message": "Either source_id or destination_id must be provided"}
            ),
        }

    # Check if source exists (only if source_id is provided)
    if source_id:
        source = get_entity(source_type, source_id)
        if not source:
            return {
                "headers": {**default_http_headers},
                "statusCode": 404,
                "body": json.dumps(
                    {"message": f"Source {source_type} with ID {source_id} not found"}
                ),
            }

    # Check if destination exists (only if destination_id is provided)
    if destination_id:
        destination = get_entity(destination_type, destination_id)
        if not destination:
            return {
                "headers": {**default_http_headers},
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "message": f"Destination {destination_type} with ID {destination_id} not found"
                    }
                ),
            }

    return None


# Using group_entities_by_type from entity_management module


def update_source_container(
    source_type: str, source_id: str, entities_by_type: Dict[str, List[str]]
) -> None:
    """
    Update the source container to remove entities.

    Args:
        source_type: Type of the source container entity
        source_id: ID of the source container entity
        entities_by_type: Dictionary mapping entity types to lists of entity IDs
    """
    if not source_id:
        return

    # Get a fresh copy of the source entity to ensure we have the latest data
    fresh_source = get_entity(source_type, source_id)
    if not fresh_source:
        return

    for entity_type, entity_ids in entities_by_type.items():
        entity_ids_attr = f"{entity_type}_ids"
        if entity_ids_attr in fresh_source and isinstance(
            fresh_source[entity_ids_attr], list
        ):
            # Create a new list without the entities being removed
            updated_ids = [
                id for id in fresh_source[entity_ids_attr] if id not in entity_ids
            ]
            # Directly update the entity with the new list
            update_entity(source_type, source_id, {entity_ids_attr: updated_ids})


def update_server_count(entity_type: str, entity_id: str, count_change: int) -> None:
    """
    Update server_count for an entity using relationship_updates.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity
        count_change: Change to apply to server_count (positive or negative)
    """
    entity_manager.update_server_count(entity_type, entity_id, count_change)


def update_app_planning_status(app_id: str) -> None:
    """
    Update the planning_status of an app based on its assets' grouping status.

    Status values:
    - COMPLETED: All assets (servers/databases) are in move groups
    - PARTIAL: Some assets are in move groups, some are not
    - NOT_STARTED: No assets are in move groups

    Args:
        app_id: ID of the app to update
    """
    app = get_entity("app", app_id)
    if not app:
        return

    # Get all servers and databases for this app
    server_ids = app.get("server_ids", [])
    database_ids = app.get("database_ids", [])

    # If no assets, consider it NOT_STARTED
    if not server_ids and not database_ids:
        update_entity("app", app_id, {"planning_status": "NOT_STARTED"})
        return

    # Count assets in move groups
    grouped_servers = 0
    grouped_databases = 0

    # Check servers
    for server_id in server_ids:
        server = get_entity("server", server_id)
        if server and "move_group_id" in server and server["move_group_id"]:
            grouped_servers += 1

    # Check databases
    for db_id in database_ids:
        db = get_entity("database", db_id)
        if db and "move_group_id" in db and db["move_group_id"]:
            grouped_databases += 1

    # Calculate total assets and grouped assets
    total_assets = len(server_ids) + len(database_ids)
    grouped_assets = grouped_servers + grouped_databases

    # Determine status
    if grouped_assets == 0:
        status = "NOT_STARTED"
    elif grouped_assets == total_assets:
        status = "COMPLETED"
    else:
        status = "PARTIAL"

    # Update app status
    update_entity("app", app_id, {"planning_status": status})
    logger.info(f"Updated app {app_id} planning_status to {status}")


def update_app_container_relationships(app_id: str, container_type: str, container_id: str, operation: str) -> None:
    """
    Update app relationships with containers (move_group, wave, etc.).

    Args:
        app_id: ID of the app
        container_type: Type of the container (e.g., 'move_group', 'wave')
        container_id: ID of the container
        operation: 'add' or 'remove'
    """
    # Update container -> app relationship
    update_relationship(container_type, container_id, "app", app_id, operation)

    # Update container's app_ids list directly
    container = get_entity(container_type, container_id)
    if container:
        current_app_ids = container.get("app_ids", [])

        if operation == "add" and app_id not in current_app_ids:
            current_app_ids.append(app_id)
        elif operation == "remove" and app_id in current_app_ids:
            current_app_ids = [id for id in current_app_ids if id != app_id]

        update_entity(container_type, container_id, {"app_ids": current_app_ids})

    # Update app -> container relationship
    app = get_entity("app", app_id)
    if app:
        container_ids_attr = f"{container_type}_ids"
        current_ids = app.get(container_ids_attr, [])

        if operation == "add" and container_id not in current_ids:
            current_ids.append(container_id)
        elif operation == "remove" and container_id in current_ids:
            current_ids = [id for id in current_ids if id != container_id]

        update_entity("app", app_id, {container_ids_attr: current_ids})

        # Handle parent relationships (e.g., wave for move_group)
        container_entity = get_entity(container_type, container_id)
        if container_entity:
            for parent_type in relationship_cache.get(container_type, {}).get("parents", []):
                parent_id_attr = f"{parent_type}_id"
                if parent_id_attr in container_entity and container_entity[parent_id_attr]:
                    parent_id = container_entity[parent_id_attr]
                    update_app_container_relationships(app_id, parent_type, parent_id, operation)


def count_app_references_in_container(app_id: str, container_type: str, container_id: str, exclude_entity_id: str = None, exclude_entity_type: str = None) -> int:
    """
    Count how many assets in a container reference an app.

    Args:
        app_id: ID of the app
        container_type: Type of the container
        container_id: ID of the container
        exclude_entity_id: ID of entity to exclude from count
        exclude_entity_type: Type of entity to exclude from count

    Returns:
        Number of references to the app from assets in the container
    """
    count = 0
    container = get_entity(container_type, container_id)
    if not container:
        return 0

    for asset_type in APP_CHILD_ASSETS:
        asset_ids_attr = f"{asset_type}_ids"
        if asset_ids_attr in container:
            for asset_id in container.get(asset_ids_attr, []):
                if exclude_entity_type == asset_type and asset_id == exclude_entity_id:
                    continue
                asset_entity = get_entity(asset_type, asset_id)
                if asset_entity and app_id in get_app_ids_from_entity(asset_entity):
                    count += 1

    return count


def process_custom_asset(
    entity_type: str,
    entity_id: str,
    source_type: str,
    source_id: str,
    destination_type: str,
    destination_id: str,
    target_entity: Dict = None,
) -> Dict:
    """
    Process a custom asset during a move operation.

    Args:
        entity_type: Type of the custom asset
        entity_id: ID of the custom asset
        source_type: Type of the source container (should be "app")
        source_id: ID of the source app
        destination_type: Type of the destination container (should be "app")
        destination_id: ID of the destination app
        target_entity: Optional target entity data with additional attributes

    Returns:
        Result dictionary for this custom asset
    """
    entity = get_entity(entity_type, entity_id)
    if not entity:
        return {
            "entity_id": entity_id,
            "status": "error",
            "message": f"{entity_type} with ID {entity_id} not found",
        }

    # Get current app_ids or use target entity's app_ids
    if target_entity and "app_ids" in target_entity:
        new_app_ids = target_entity["app_ids"]
    else:
        new_app_ids = entity.get("app_ids", [])

        # Handle move between apps
        if source_id and source_id in new_app_ids:
            new_app_ids = [id for id in new_app_ids if id != source_id]
        if destination_id and destination_id not in new_app_ids:
            new_app_ids.append(destination_id)

    # Update the custom asset's app_ids
    update_entity(entity_type, entity_id, {"app_ids": new_app_ids})

    # Update source app to remove this asset
    if source_id:
        source_app = get_entity("app", source_id)
        if source_app:
            asset_ids_attr = f"{entity_type}_ids"
            current_asset_ids = source_app.get(asset_ids_attr, [])
            if entity_id in current_asset_ids:
                new_asset_ids = [id for id in current_asset_ids if id != entity_id]
                update_entity("app", source_id, {asset_ids_attr: new_asset_ids})

    # Update destination app to add this asset
    if destination_id:
        dest_app = get_entity("app", destination_id)
        if dest_app:
            asset_ids_attr = f"{entity_type}_ids"
            current_asset_ids = dest_app.get(asset_ids_attr, [])
            if entity_id not in current_asset_ids:
                current_asset_ids.append(entity_id)
                update_entity("app", destination_id, {asset_ids_attr: current_asset_ids})

    return {
        "entity_id": entity_id,
        "status": "success",
        "message": f"Moved {entity_type} with ID {entity_id}",
    }


def process_entity(
    entity_type: str,
    entity_id: str,
    source_type: str,
    source_id: str,
    destination_type: str,
    destination_id: str,
    apps_to_process: Dict,
    target_entity: Dict = None,
) -> Dict:
    """
    Process a single entity during a move operation.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity
        source_type: Type of the source container entity
        source_id: ID of the source container entity
        destination_type: Type of the destination container entity
        destination_id: ID of the destination container entity
        apps_to_process: Dictionary to track apps that need processing
        target_entity: Optional target entity data with additional attributes

    Returns:
        Result dictionary for this entity
    """
    # Handle custom assets separately
    if entity_type in get_custom_asset_types():
        return process_custom_asset(
            entity_type, entity_id, source_type, source_id,
            destination_type, destination_id, target_entity
        )

    entity = get_entity(entity_type, entity_id)
    if not entity:
        return {
            "entity_id": entity_id,
            "status": "error",
            "message": f"{entity_type} with ID {entity_id} not found",
        }

    # Handle app_ids update for entities with different app lists
    if target_entity and "app_ids" in target_entity and "app" in relationship_cache[entity_type]["outgoing"]:
        new_app_ids = target_entity["app_ids"]
        current_app_ids = entity.get("app_ids", [])

        # Find removed and added apps
        removed_apps = set(current_app_ids) - set(new_app_ids)
        added_apps = set(new_app_ids) - set(current_app_ids)

        # Update removed apps - remove container references
        for app_id in removed_apps:
            if source_id:
                update_app_container_relationships(app_id, source_type, source_id, "remove")

        # Update added apps - add container references
        for app_id in added_apps:
            if destination_id:
                update_app_container_relationships(app_id, destination_type, destination_id, "add")

        # Update the entity's app_ids
        update_entity(entity_type, entity_id, {"app_ids": new_app_ids})

    # Track child entities for app processing using relationship cache
    app_ids_to_track = []

    # Use new app_ids if provided, otherwise use current entity app relationships
    if target_entity and "app_ids" in target_entity:
        app_ids_to_track = target_entity["app_ids"]
    else:
        # Get app relationships from the entity directly
        if "app_ids" in entity and entity["app_ids"]:
            app_ids_to_track.extend(entity["app_ids"])
        elif "app_id" in entity and entity["app_id"]:
            app_ids_to_track.append(entity["app_id"])

    # Handle app relationships using reference counting when moving between move groups
    if source_id and destination_id and source_type == "move_group" and destination_type == "move_group" and app_ids_to_track:
        for app_id in app_ids_to_track:
            # Check if app should be removed from source container
            source_ref_count = count_app_references_in_container(app_id, source_type, source_id, entity_id, entity_type)
            if source_ref_count == 0:  # No other entities reference the app
                update_app_container_relationships(app_id, source_type, source_id, "remove")

            # Add app to destination container
            dest_ref_count = count_app_references_in_container(app_id, destination_type, destination_id)
            if dest_ref_count == 0:  # App not yet in destination
                update_app_container_relationships(app_id, destination_type, destination_id, "add")

    # Only add to apps_to_process if we haven't already handled with reference counting
    # and if the current entity type is actually a child of app
    if (not (source_id and destination_id and source_type == "move_group" and destination_type == "move_group" and app_ids_to_track)
        and entity_type in relationship_cache["app"]["children"]):
        for app_id in app_ids_to_track:
            if app_id not in apps_to_process:
                # Initialize with all possible child types from relationship cache
                child_data = {}
                for child_type in relationship_cache["app"]["children"]:
                    child_data[f"{child_type}s"] = []
                    child_data[f"moving_{child_type}s"] = []
                apps_to_process[app_id] = child_data

            apps_to_process[app_id][f"moving_{entity_type}s"].append(entity_id)

    # Remove from source if provided
    if source_id:
        update_relationship(source_type, source_id, entity_type, entity_id, "remove")
        source_attr = f"{source_type}_id"
        updates = {source_attr: None}

        # Remove related parent attributes dynamically
        if source_type in relationship_cache[entity_type]["parents"]:
            source_entity = get_entity(source_type, source_id)
            if source_entity:
                # Check what other parents this source entity has
                for parent_type in relationship_cache[source_type]["parents"]:
                    if parent_type in relationship_cache[entity_type]["outgoing"]:
                        parent_attrs = relationship_cache[entity_type]["outgoing"][parent_type]
                        for attr in parent_attrs:
                            if attr in source_entity and source_entity[attr]:
                                # Remove wave entity reference if removing from move_group
                                if parent_type == "wave" and source_type == "move_group":
                                    update_relationship("wave", source_entity[attr], entity_type, entity_id, "remove")
                                updates[attr] = None

        update_entity(entity_type, entity_id, updates)

        # Update server count in source if entity is a server
        if entity_type == "server":
            update_server_count(source_type, source_id, -1)

    # Add to destination if provided
    if destination_id:
        update_relationship(
            destination_type, destination_id, entity_type, entity_id, "add"
        )
        dest_attr = f"{destination_type}_id"
        updates = {dest_attr: destination_id}

        # Add related parent attributes dynamically
        if destination_type in relationship_cache[entity_type]["parents"]:
            dest_entity = get_entity(destination_type, destination_id)
            if dest_entity:
                # Check what other parents this destination entity has
                for parent_type in relationship_cache[destination_type]["parents"]:
                    if parent_type in relationship_cache[entity_type]["outgoing"]:
                        parent_attrs = relationship_cache[entity_type]["outgoing"][parent_type]
                        for attr in parent_attrs:
                            if attr in dest_entity and dest_entity[attr]:
                                updates[attr] = dest_entity[attr]

                                # Update wave with entity reference if moving to move_group
                                if parent_type == "wave" and destination_type == "move_group":
                                    update_relationship("wave", dest_entity[attr], entity_type, entity_id, "add")

        update_entity(entity_type, entity_id, updates)

        # Update server count in destination if entity is a server
        if entity_type == "server":
            update_server_count(destination_type, destination_id, 1)

    # Update parent references if needed
    if destination_id and source_type == destination_type:
        update_parent_references(entity_type, entity_id, source_type, destination_id)

    # Update all child references to point to new parent
    move_child_refs(entity_type, entity_id, source_type, source_id, destination_type, destination_id)

    # Update app planning_status for entities that have app relationships
    if "app" in relationship_cache[entity_type]["outgoing"]:
        app_attrs = relationship_cache[entity_type]["outgoing"]["app"]
        for attr in app_attrs:
            if attr in entity:
                if isinstance(entity[attr], list):
                    for app_id in entity[attr]:
                        update_app_planning_status(app_id)
                elif entity[attr]:
                    update_app_planning_status(entity[attr])

    return {
        "entity_id": entity_id,
        "status": "success",
        "message": f"Moved {entity_type} with ID {entity_id}",
    }


def move_child_refs(
    entity_type: str, 
    entity_id: str, 
    source_type: str, 
    source_id: str, 
    destination_type: str, 
    destination_id: str
) -> None:
    """    
    A generic method that searches through all child references and updates them
    to point to a new parent reference. It also updates the parent to reference the child.
    
    Supports three scenarios:
    1. Move from source to destination (both source_id and destination_id provided)
    2. Add to destination only (only destination_id provided)
    3. Remove from source only (only source_id provided)
    
    Args:
        entity_type: Type of the entity being moved
        entity_id: ID of the entity being moved
        source_type: Type of the source container entity
        source_id: ID of the source container entity (can be None for add-only operations)
        destination_type: Type of the destination container entity
        destination_id: ID of the destination container entity (can be None for remove-only operations)
    """
    entity = get_entity(entity_type, entity_id)
    if not entity:
        return
    
    # Get all child entities for this entity using relationship cache
    if entity_type not in relationship_cache or "children" not in relationship_cache[entity_type]:
        return
        
    for child_type in relationship_cache[entity_type]["children"]:
        child_ids_attr = f"{child_type}_ids"
        single_child_attr = f"{child_type}_id"
        all_child_ids = set()
        
        # Check entity for child references (both single and multiple)
        if child_ids_attr in entity and entity[child_ids_attr]:
            all_child_ids.update(entity[child_ids_attr])
        if single_child_attr in entity and entity[single_child_attr]:
            all_child_ids.add(entity[single_child_attr])
            
        # Also check relationship cache for additional child references
        child_ids = get_related_entities(entity_type, entity_id).get(child_type, [])
        if child_ids:
            all_child_ids.update(child_ids)
            
        # Additionally, scan all entities of this type to find ones that reference this entity
        # This ensures we capture all children even if the entity's child_ids list is incomplete
        if child_type in entity_cache:
            for child_entity_id, child_entity in entity_cache[child_type].items():
                parent_ids_attr = f"{entity_type}_ids"
                parent_id_attr = f"{entity_type}_id"
                
                # Check if child references this entity
                if parent_ids_attr in child_entity and entity_id in child_entity[parent_ids_attr]:
                    all_child_ids.add(child_entity_id)
                elif parent_id_attr in child_entity and child_entity[parent_id_attr] == entity_id:
                    all_child_ids.add(child_entity_id)
        
        # Update each child to point to the new parent
        for child_id in all_child_ids:
            child_entity = get_entity(child_type, child_id)
            if not child_entity:
                continue
                
            updates = {}
            
            # Update parent reference in child (remove old, add new)
            if source_id and destination_id:
                # Moving from one parent to another
                source_ids_attr = f"{source_type}_ids"
                source_id_attr = f"{source_type}_id"
                dest_ids_attr = f"{destination_type}_ids"
                dest_id_attr = f"{destination_type}_id"
                
                # Handle source removal
                if source_ids_attr in child_entity and source_id in child_entity[source_ids_attr]:
                    current_source_ids = child_entity[source_ids_attr].copy()
                    current_source_ids.remove(source_id)
                    updates[source_ids_attr] = current_source_ids
                elif source_id_attr in child_entity and child_entity[source_id_attr] == source_id:
                    updates[source_id_attr] = None
                    
                # Handle destination addition
                if dest_ids_attr in child_entity:
                    current_dest_ids = child_entity.get(dest_ids_attr, [])
                    if destination_id not in current_dest_ids:
                        current_dest_ids.append(destination_id)
                        updates[dest_ids_attr] = current_dest_ids
                else:
                    # Always set the singular ID field for direct parent-child relationships
                    updates[dest_id_attr] = destination_id
                    
            elif destination_id:
                # Only adding to destination (no source removal)
                dest_ids_attr = f"{destination_type}_ids"
                dest_id_attr = f"{destination_type}_id"
                
                if dest_ids_attr in child_entity:
                    current_dest_ids = child_entity.get(dest_ids_attr, [])
                    if destination_id not in current_dest_ids:
                        current_dest_ids.append(destination_id)
                        updates[dest_ids_attr] = current_dest_ids
                else:
                    # Always set the singular ID field for direct parent-child relationships
                    updates[dest_id_attr] = destination_id
                    
            elif source_id:
                # Only removing from source (no destination)
                source_ids_attr = f"{source_type}_ids"
                source_id_attr = f"{source_type}_id"
                
                # Handle source removal
                if source_ids_attr in child_entity and source_id in child_entity[source_ids_attr]:
                    current_source_ids = child_entity[source_ids_attr].copy()
                    current_source_ids.remove(source_id)
                    updates[source_ids_attr] = current_source_ids
                elif source_id_attr in child_entity and child_entity[source_id_attr] == source_id:
                    updates[source_id_attr] = None
                    
            # Apply updates to child entity
            if updates:
                update_entity(child_type, child_id, updates)
                
        # Update parent entities to reference the children
        if source_id and destination_id:
            # Remove child references from source parent
            for child_id in all_child_ids:
                update_relationship(source_type, source_id, child_type, child_id, "remove")
                
            # Add child references to destination parent  
            for child_id in all_child_ids:
                update_relationship(destination_type, destination_id, child_type, child_id, "add")
                
        elif destination_id:
            # Only add child references to destination parent
            for child_id in all_child_ids:
                update_relationship(destination_type, destination_id, child_type, child_id, "add")
                
        elif source_id:
            # Only remove child references from source parent
            for child_id in all_child_ids:
                update_relationship(source_type, source_id, child_type, child_id, "remove")


def update_parent_references(
    entity_type: str, entity_id: str, parent_type: str, parent_id: str
) -> None:
    """
    Update parent references for an entity and its children.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity
        parent_type: Type of the parent entity
        parent_id: ID of the parent entity
    """
    parent_attr = f"{parent_type}_id"
    entity = get_entity(entity_type, entity_id)

    if not entity:
        return

    # Check if the schema defines this parent relationship, not just if the entity has it
    if (entity_type in relationship_cache and 
        parent_type in relationship_cache[entity_type].get("outgoing", {}) and 
        parent_attr in relationship_cache[entity_type]["outgoing"][parent_type]):
        update_entity(entity_type, entity_id, {parent_attr: parent_id})

    # Recursively update all children to point to the new parent
    child_entities = get_related_entities(entity_type, entity_id)
    for child_type, child_ids in child_entities.items():
        for child_id in child_ids:
            child = get_entity(child_type, child_id)
            if not child:
                continue

            # Check schema for parent_type_id relationship
            if (child_type in relationship_cache and 
                parent_type in relationship_cache[child_type].get("outgoing", {}) and 
                f"{parent_type}_id" in relationship_cache[child_type]["outgoing"][parent_type]):
                update_entity(child_type, child_id, {f"{parent_type}_id": parent_id})
            
            # Check schema for parent_type_ids relationship
            if (child_type in relationship_cache and 
                parent_type in relationship_cache[child_type].get("outgoing", {}) and 
                f"{parent_type}_ids" in relationship_cache[child_type]["outgoing"][parent_type]):
                update_entity(child_type, child_id, {f"{parent_type}_ids": parent_id})


def process_app(
    app_id: str,
    app_data: Dict,
    source_type: str,
    source_id: str,
    destination_type: str,
    destination_id: str,
) -> Dict:
    """
    Process an app during a move operation.

    Args:
        app_id: ID of the app
        app_data: Data about the app's children
        source_type: Type of the source container entity
        source_id: ID of the source container entity
        destination_type: Type of the destination container entity
        destination_id: ID of the destination container entity

    Returns:
        Result dictionary for this app
    """
    app = get_entity("app", app_id)
    if not app:
        return None

    # Get all child entities for this app using relationship cache
    for child_type in relationship_cache["app"]["children"]:
        child_ids_attr = f"{child_type}_ids"
        all_child_ids = set()

        # Check app entity first
        if child_ids_attr in app and app[child_ids_attr]:
            all_child_ids.update(app[child_ids_attr])

        # Also check relationship cache
        child_ids = get_related_entities("app", app_id).get(child_type, [])
        if child_ids:
            all_child_ids.update(child_ids)

        # Additionally, scan all entities of this type to find ones that reference this app
        # This ensures we capture all children even if the app's child_ids list is incomplete
        if child_type in entity_cache:
            for entity_id, entity in entity_cache[child_type].items():
                if "app_ids" in entity and app_id in entity["app_ids"]:
                    all_child_ids.add(entity_id)

        app_data[f"{child_type}s"] = list(all_child_ids)

    # Check if all children are moving
    all_servers_moving = set(app_data["servers"]).issubset(
        set(app_data["moving_servers"])
    )
    all_databases_moving = set(app_data["databases"]).issubset(
        set(app_data["moving_databases"])
    )
    all_children_moving = all_servers_moving and all_databases_moving

    # Handle the case where we're only removing from source (destination_id is None)
    if destination_id is None:
        # Only process if we have a source to remove from and all children are moving
        if source_id and all_children_moving:
            # Remove app from source
            update_relationship(source_type, source_id, "app", app_id, "remove")

            # Update the app's relationship list
            current_source_ids = app.get(f"{source_type}_ids", [])
            if source_id in current_source_ids:
                current_source_ids.remove(source_id)
                updates = {f"{source_type}_ids": current_source_ids}

                # Update wave relationships using helper function
                updates = update_app_wave_relationships(
                    app_id, app, source_type, source_id, None, None, updates, get_entity, update_relationship
                )

                update_entity("app", app_id, updates)

            # Update app planning_status
            update_app_planning_status(app_id)

            return {
                "entity_id": app_id,
                "status": "success",
                "message": f"Removed app with ID {app_id} from {source_type}",
            }
        else:
            # If not all children are moving, or no source specified, just update planning status
            update_app_planning_status(app_id)
            return {
                "entity_id": app_id,
                "status": "success",
                "message": f"Updated app with ID {app_id} (partial move)",
            }

    # Handle the case where we have a destination
    current_destination_ids = app.get(f"{destination_type}_ids", [])

    if all_children_moving:
        # Move app (remove from source, add to destination)
        if source_id:
            update_relationship(source_type, source_id, "app", app_id, "remove")
        update_relationship(destination_type, destination_id, "app", app_id, "add")

        if source_id and source_id in current_destination_ids:
            current_destination_ids.remove(source_id)
        if destination_id not in current_destination_ids:
            current_destination_ids.append(destination_id)

        updates = {f"{destination_type}_ids": current_destination_ids}

        # Update wave relationships using helper function
        updates = update_app_wave_relationships(
            app_id, app, source_type, source_id, destination_type, destination_id, updates, get_entity, update_relationship
        )

        update_entity("app", app_id, updates)

        # Update app planning_status
        update_app_planning_status(app_id)

        return {
            "entity_id": app_id,
            "status": "success",
            "message": f"Moved app with ID {app_id}",
        }
    else:
        # Copy app to destination (don't remove from source)
        update_relationship(destination_type, destination_id, "app", app_id, "add")

        if destination_id not in current_destination_ids:
            current_destination_ids.append(destination_id)

        updates = {f"{destination_type}_ids": current_destination_ids}

        # Update wave relationships using helper function
        updates = update_app_wave_relationships(
            app_id, app, None, None, destination_type, destination_id, updates, get_entity, update_relationship
        )

        update_entity("app", app_id, updates)

        # Update app planning_status
        update_app_planning_status(app_id)

        return {
            "entity_id": app_id,
            "status": "success",
            "message": f"Copied app with ID {app_id}",
        }


def create_move_response(
    source_type: str,
    source_id: str,
    destination_type: str,
    destination_id: str,
    results: Dict,
) -> Dict:
    """
    Create the response for a move operation.

    Args:
        source_type: Type of the source container entity
        source_id: ID of the source container entity
        destination_type: Type of the destination container entity
        destination_id: ID of the destination container entity
        results: Results of the move operation

    Returns:
        Response dictionary
    """
    # Check if any process_entity returned an error status
    has_errors = False
    for entity_type, entity_results in results.items():
        for result in entity_results:
            if result.get("status") == "error":
                has_errors = True
                break
        if has_errors:
            break

    if has_errors:
        message = "Move operation completed with errors. Check individual entity results for details."
    else:
        if source_id and destination_id:
            message = f"Successfully moved entities from {source_type}:{source_id} to {destination_type}:{destination_id}"
        elif source_id:
            message = f"Successfully removed entities from {source_type}:{source_id}"
        else:  # destination_id must be present based on earlier validation
            message = f"Successfully added entities to {destination_type}:{destination_id}"

    return {
        "headers": {**default_http_headers},
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": message,
                "results": results,
            },
            default=set_default,
        ),
    }


def initialize_server_count(entity_type: str, entity_id: str) -> None:
    """
    Initialize server_count for an entity if it doesn't exist.

    Args:
        entity_type: Type of the entity
        entity_id: ID of the entity
    """
    entity_manager.initialize_server_count(entity_type, entity_id)


def move_entities(
    source_type: str,
    source_id: str,
    destination_type: str,
    destination_id: str,
    target_entities: List[Dict],
) -> Dict:
    """
    Move entities between containers and update relationships.

    Args:
        source_type: Type of the source container entity
        source_id: ID of the source container entity (if None, entities will be added to destination only)
        destination_type: Type of the destination container entity
        destination_id: ID of the destination container entity (if None, entities will be removed from source only)
        target_entities: List of entities to move (each with entity_type and entity_id)

    Returns:
        Dictionary with status and message and relationship updates
    """
    # Log the operation
    if source_id and destination_id:
        logger.info(
            f"Moving entities {target_entities} from {source_type}:{source_id} to {destination_type}:{destination_id}"
        )
    elif source_id:
        logger.info(
            f"Removing entities {target_entities} from {source_type}:{source_id}"
        )
    elif destination_id:
        logger.info(
            f"Adding entities {target_entities} to {destination_type}:{destination_id}"
        )

    # Validate input parameters
    validation_error = validate_move_entities_input(
        source_id, source_type, destination_id, destination_type
    )
    if validation_error:
        return validation_error

    # Initialize server_count for source and destination if needed
    if source_id:
        initialize_server_count(source_type, source_id)
    if destination_id:
        initialize_server_count(destination_type, destination_id)

    # Group target entities by type
    entities_by_type = group_entities_by_type(target_entities)

    # Update source container
    update_source_container(source_type, source_id, entities_by_type)

    # Track apps that need to be processed after entities
    apps_to_process = {}

    # Process each entity type
    results = {}
    for entity_type, entity_ids in entities_by_type.items():
        results[entity_type] = []

        # For each entity of this type
        for entity_id in entity_ids:
            # Find the target entity data for this entity_id
            target_entity = None
            for target in target_entities:
                if target["entity_type"] == entity_type and target["entity_id"] == entity_id:
                    target_entity = target
                    break

            result = process_entity(
                entity_type,
                entity_id,
                source_type,
                source_id,
                destination_type,
                destination_id,
                apps_to_process,
                target_entity,
            )
            results[entity_type].append(result)

    # Process apps after all entities have been moved
    if apps_to_process:
        if "app" not in results:
            results["app"] = []

        for app_id, app_data in apps_to_process.items():
            app_result = process_app(
                app_id,
                app_data,
                source_type,
                source_id,
                destination_type,
                destination_id,
            )
            if app_result:
                results["app"].append(app_result)

    # Return appropriate response
    return create_move_response(
        source_type, source_id, destination_type, destination_id, results
    )


def validate_request_body(event: Dict) -> Dict:
    """Validates the request body for manage entities operations"""

    # Basic checks
    if "body" not in event:
        return {"valid": False, "error": "Missing request body"}
    
    # Parse JSON
    try:
        json_body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
    except json.JSONDecodeError:
        return {"valid": False, "error": "Invalid JSON format"}
    
    # Validate operation
    if "operation" not in json_body:
        return {"valid": False, "error": "Missing required parameter: operation"}
    
    operation = json_body["operation"]
    if operation not in ["cleanup", "move"]:
        return {"valid": False, "error": "Unsupported operation"}
    
    # Route to specific validators
    if operation == "cleanup":
        return validate_cleanup_request(json_body)
    else:
        return validate_move_request(json_body)


def validate_cleanup_request(json_body: Dict) -> Dict:
    """Validates cleanup operation request body"""
    # Check required fields
    for field in ["entity_type", "entity_ids"]:
        if field not in json_body:
            return {"valid": False, "error": f"Missing required parameter: {field}"}
    
    # Validate entity_type
    error = validate_id_string(json_body["entity_type"], "entity_type")
    if error:
        return {"valid": False, "error": error}
    
    # Validate entity_ids
    error = validate_id_list(json_body["entity_ids"], "entity_ids", MAX_ENTITY_IDS_COUNT)
    if error:
        return {"valid": False, "error": error}
    
    return {"valid": True, "json_body": json_body}


def validate_move_request(json_body: Dict) -> Dict:
    """Validates move operation request body"""
    # Check required field
    if "target_entities" not in json_body:
        return {"valid": False, "error": "Missing required parameter: target_entities"}
    
    target_entities = json_body["target_entities"]
    if not isinstance(target_entities, list) or not target_entities:
        return {"valid": False, "error": "target_entities must be a non-empty list"}
    
    if len(target_entities) > MAX_TARGET_ENTITIES_COUNT:
        return {"valid": False, "error": f"Too many target entities. Maximum allowed is {MAX_TARGET_ENTITIES_COUNT}"}
    
    # Check for duplicate entity_type+entity_id combinations
    entity_keys = set()
    for entity in target_entities:
        if not isinstance(entity, dict):
            return {"valid": False, "error": "Each target entity must be an object"}
        
        # Check required fields
        for field in ["entity_type", "entity_id"]:
            if field not in entity:
                return {"valid": False, "error": f"Each target entity must have {field}"}
            
            error = validate_id_string(entity[field], field)
            if error:
                return {"valid": False, "error": error}
        
        # Check for duplicate entity_type+entity_id combination
        entity_key = (entity["entity_type"], entity["entity_id"])
        if entity_key in entity_keys:
            return {"valid": False, "error": "Duplicate entity_id found"}
        entity_keys.add(entity_key)
    
    # Validate optional source/destination fields
    for field in ["source_entity_type", "source_entity_id", "destination_entity_type", "destination_entity_id"]:
        if field in json_body and json_body[field] != "":
            error = validate_id_string(json_body[field], field)
            if error:
                return {"valid": False, "error": error}
    
    return {"valid": True, "json_body": json_body}


def lambda_handler(event, context):
    """
    Main Lambda handler function.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response object with statusCode and body
    """
    event_body = event.get("body", {})
    logger.info(f"Received event with body: {json.dumps(event_body)}")

    # Validate input
    validation_result = validate_request_body(event)
    if not validation_result["valid"]:
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": json.dumps({"message": validation_result["error"]}),
        }
    
    json_body = validation_result["json_body"]
    operation = json_body["operation"]

    try:
        if operation == "cleanup":
            # For cleanup operations, check schema-specific delete permission
            entity_type = json_body.get("entity_type")
            if entity_type:
                from policy import MFAuth
                auth = MFAuth()
                # Set httpMethod to DELETE for proper permission checking
                event_copy = event.copy()
                event_copy['httpMethod'] = 'DELETE'
                auth_response = auth.get_user_resource_creation_policy(event_copy, entity_type)
                if auth_response['action'] != 'allow':
                    return {
                        "headers": {**default_http_headers},
                        "statusCode": 403,
                        "body": json.dumps({"error": "Unauthorized", "message": f"Delete permission required for {entity_type}"}),
                    }
        elif operation == "move":
            # For move operations, check update permission for specific fields
            target_entities = json_body.get("target_entities", [])
            source_type = json_body.get("source_entity_type")
            destination_type = json_body.get("destination_entity_type", source_type)
            source_type = source_type if source_type else destination_type
            
            if target_entities:
                from policy import MFAuth
                auth = MFAuth()
                
                # Check permissions for each target entity type
                for target_entity in target_entities:
                    entity_type = target_entity.get("entity_type")
                    if not entity_type:
                        continue
                        
                    # Determine which field to check based on entity type and container type
                    fields_to_check = []
                    
                    # Check source field permissions
                    if source_type:
                        if entity_type in ["server", "database", "move_group"] and source_type in ["wave", "move_group"]:
                            fields_to_check.append(f"{source_type}_id")
                        else:
                            fields_to_check.append(f"{source_type}_ids")
                    
                    # Check update permission for each field
                    for field in fields_to_check:
                        # Create a mock event body with just the field to check
                        mock_event = event.copy()
                        mock_event['httpMethod'] = 'PUT'
                        mock_event['body'] = json.dumps({field: "test_value"})
                        
                        auth_response = auth.get_user_attribute_policy(mock_event, entity_type)
                        if auth_response['action'] != 'allow':
                            return {
                                "headers": {**default_http_headers},
                                "statusCode": 403,
                                "body": json.dumps({"error": "Unauthorized", "message": f"Update permission required for {entity_type}.{field}"}),
                            }
        else:
            return {
                "headers": {**default_http_headers},
                "statusCode": 400,
                "body": json.dumps({"message": f"Unsupported operation: {operation}"}),
            }
    except Exception:
        logger.error(f"Unexpected error in permission check: {traceback.format_exc()}")
        return {
            "headers": {**default_http_headers},
            "statusCode": 403,
            "body": json.dumps({"error": "Unauthorized", "message": "Permission required"}),
        }

    # Declare global variables to make sure all modifications to these variables are against the module-level variables
    global relationship_updates, entity_cache, schema_cache, entity_manager, dynamodb_manager
    # Clear the assigned values from previous lambda invocations on the same lambda instance
    relationship_updates = {}
    entity_cache = {}
    schema_cache = {}

    # Initialize the managers for this particular lambda invocation - DynamoDBManager first, then EntityManager
    dynamodb_manager = DynamoDBManager(TABLES)
    entity_manager = EntityManager(dynamodb_manager, relationship_cache, entity_cache, relationship_updates)

    # Build relationship cache on initialization
    build_relationship_cache()

    try:
        # Handle cleanup operation
        if operation == "cleanup":
            entity_type = json_body["entity_type"]
            entity_ids = json_body["entity_ids"]

            # Validate entity type
            if not _validate_entity_type(entity_type):
                return {
                    "headers": {**default_http_headers},
                    "statusCode": 400,
                    "body": json.dumps(
                        {"message": f"Invalid entity_type: {entity_type}"}
                    ),
                }

            response = cleanup_entity(entity_type, entity_ids)

            # Create transaction items from relationship updates
            transaction_items = dynamodb_manager.create_transaction_items(relationship_updates)

            # Commit transactions to DynamoDB if response is successful
            transaction_results = []
            if response["statusCode"] == 200:
                transaction_results = dynamodb_manager.commit_transactions(transaction_items)

                # Add transaction results to the response
                response_body = json.loads(response["body"])
                response_body["transaction_results"] = transaction_results
                response["body"] = json.dumps(response_body, default=set_default)

            return response

        # Handle move operation
        elif operation == "move":
            target_entities = json_body["target_entities"]

            # Categorize entities by type
            custom_asset_types = get_custom_asset_types()
            custom_entities = []
            regular_entities = []

            for entity in target_entities:
                entity_type = entity.get("entity_type")
                if entity_type in custom_asset_types:
                    custom_entities.append(entity)
                elif entity_type in TABLES:
                    regular_entities.append(entity)
                else:
                    return {
                        "headers": {**default_http_headers},
                        "statusCode": 400,
                        "body": json.dumps(
                            {
                                "message": f"Invalid entity_type: {entity_type}"
                            }
                        ),
                    }

            # Check for mixed entity types - not allowed
            if custom_entities and regular_entities:
                return {
                    "headers": {**default_http_headers},
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "message": "Cannot mix custom assets and regular entities in the same move operation"
                        }
                    ),
                }

            # Route to appropriate handler
            if custom_entities:
                response = move_custom_assets(custom_entities)
            else:
                response = move_regular_entities(json_body, regular_entities)

            # Create transaction items from relationship updates
            transaction_items = dynamodb_manager.create_transaction_items(relationship_updates)

            # Commit transactions to DynamoDB
            transaction_results = dynamodb_manager.commit_transactions(transaction_items)

            # Add transaction results to the response
            response_body = json.loads(response["body"])
            response_body["transaction_results"] = transaction_results
            response["body"] = json.dumps(response_body, default=set_default)

            return response

        else:
            return {
                "headers": {**default_http_headers},
                "statusCode": 400,
                "body": json.dumps({"message": f"Unsupported operation: {operation}"}),
            }

    except KeyError as e:
        logger.error(f"Missing key in request: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": json.dumps({"message": f"Missing required field: {str(e)}"}),
        }
    except ClientError as e:
        error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        logger.error(f"DynamoDB error ({error_code}): {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "headers": {**default_http_headers},
            "statusCode": 500,
            "body": json.dumps({"message": f"Database error: {str(e)}"}),
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "headers": {**default_http_headers},
            "statusCode": 500,
            "body": json.dumps({"message": f"Internal server error: {str(e)}"}),
        }
