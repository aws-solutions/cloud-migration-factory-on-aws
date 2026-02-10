"""
Schema processing module for building relationship cache in the Migration Factory solution.

This module contains functions for processing schema attributes to build a relationship cache
that maps entity types to their relationships.

Author: AWS Professional Services
"""

import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()

# Relationship types
RELATIONSHIP = "relationship"
MULTIVALUE_RELATIONSHIP = "multivalue-relationship"

# Built-in entity types
BUILT_IN_ENTITY_TYPES = [
    "wpm_job",
    "wave",
    "move_group",
    "app",
    "server",
    "database",
    "move_group_request",
]


def get_entity_types(schema_cache=None):
    """
    Get the list of all entity types including custom assets.

    Args:
        schema_cache: Schema cache dictionary containing custom asset types

    Returns:
        List of entity type names
    """
    if schema_cache:
        custom_asset_types = schema_cache.get("_custom_asset_types", [])
        return BUILT_IN_ENTITY_TYPES + custom_asset_types
    return BUILT_IN_ENTITY_TYPES


def initialize_cache_structure(entity_types, relationship_cache):
    """
    Initialize the relationship cache structure for all entity types.

    Args:
        entity_types: List of entity type names
        relationship_cache: The relationship cache dictionary to initialize
    """
    for entity_type in entity_types:
        relationship_cache[entity_type] = {
            "outgoing": {},  # entity_type -> related_entity_type -> attribute_name
            "incoming": {},  # related_entity_type -> attribute_name
            "parents": set(),  # entity types that are parents of this entity
            "children": set(),  # entity types that are children of this entity
            "parent_ids": {},  # entity_id -> {parent_type: [parent_ids]}
            "child_ids": {},  # entity_id -> {child_type: [child_ids]}
        }


def add_outgoing_relationship(entity_type, rel_entity, attr_name, relationship_cache):
    """
    Add an outgoing relationship to the cache.

    Args:
        entity_type: Source entity type
        rel_entity: Related entity type
        attr_name: Attribute name for the relationship
        relationship_cache: The relationship cache dictionary
    """
    relationship_cache[entity_type]["outgoing"].setdefault(rel_entity, set()).add(
        attr_name
    )


def add_incoming_relationship(entity_type, rel_entity, attr_name, relationship_cache):
    """
    Add an incoming relationship to the cache.

    Args:
        entity_type: Source entity type
        rel_entity: Related entity type
        attr_name: Attribute name for the relationship
        relationship_cache: The relationship cache dictionary
    """
    relationship_cache[rel_entity]["incoming"].setdefault(entity_type, set()).add(
        attr_name
    )


def set_parent_child_relationship(entity_type, rel_entity, attr_name, relationship_cache):
    """
    Set parent-child relationship based on attribute name.

    Args:
        entity_type: Source entity type
        rel_entity: Related entity type
        attr_name: Attribute name for the relationship
        relationship_cache: The relationship cache dictionary
    """
    # Single-value relationship indicates parent
    if not attr_name.endswith("_ids"):
        # This entity has a parent relationship to rel_entity
        relationship_cache[entity_type]["parents"].add(rel_entity)
        # The related entity has a child relationship to this entity
        relationship_cache[rel_entity]["children"].add(entity_type)
    # Special case for app entity
    elif attr_name.endswith("_ids") and entity_type == "app":
        if rel_entity in ["move_group", "wave"]:
            # App is child to move_group and wave entities
            relationship_cache[entity_type]["parents"].add(rel_entity)
            relationship_cache[rel_entity]["children"].add(entity_type)
        else:
            # App is parent to servers, databases and other custom assets
            relationship_cache[entity_type]["children"].add(rel_entity)
            relationship_cache[rel_entity]["parents"].add(entity_type)


def process_schema_attribute(entity_type, attr, relationship_cache):
    """
    Process a schema attribute to find relationships.

    Args:
        entity_type: Entity type
        attr: Attribute dictionary
        relationship_cache: The relationship cache dictionary
    """
    if (
        "type" in attr
        and attr["type"] in [RELATIONSHIP, MULTIVALUE_RELATIONSHIP]
        and "name" in attr
        and (attr["name"].endswith("_id") or attr["name"].endswith("_ids"))
    ):
        rel_entity = attr["rel_entity"]
        attr_name = attr["name"]

        # Add relationships to cache
        add_outgoing_relationship(entity_type, rel_entity, attr_name, relationship_cache)
        add_incoming_relationship(entity_type, rel_entity, attr_name, relationship_cache)

        # Set parent-child relationship
        set_parent_child_relationship(entity_type, rel_entity, attr_name, relationship_cache)


def fetch_and_process_schema(entity_type, schema_cache, relationship_cache, schema_table=None):
    """
    Fetch schema for an entity type from cache and process its attributes.
    Falls back to database if not found in cache.

    Args:
        entity_type: Entity type
        schema_cache: Schema cache dictionary containing all schemas
        relationship_cache: The relationship cache dictionary
        schema_table: DynamoDB table for schemas (for fallback)
    """
    schema = None
    
    # Try to get from cache first
    if entity_type in schema_cache:
        schema = schema_cache[entity_type]
    # Fallback to database if not in cache
    elif schema_table:
        try:
            response = schema_table.get_item(Key={"schema_name": entity_type})
            if "Item" in response:
                schema = response["Item"]
                # Cache it for future use
                schema_cache[entity_type] = schema
                logger.info(f"Fetched and cached schema for {entity_type} from database")
        except ClientError as e:
            logger.error(f"Error fetching schema for {entity_type}: {str(e)}")
    
    if not schema:
        logger.error(f"Schema not found for entity type: {entity_type}")
        raise ValueError(f"Schema not found for entity type: {entity_type}")

    # Process attributes to find relationships
    if "attributes" in schema:
        for attr in schema["attributes"]:
            process_schema_attribute(entity_type, attr, relationship_cache)


def fill_missing_bidirectional_relationships(entity_types, relationship_cache):
    """
    Fill in missing bi-directional relationships.

    Args:
        entity_types: List of entity type names
        relationship_cache: The relationship cache dictionary
    """
    for entity_type in entity_types:
        for related_type in relationship_cache[entity_type]["outgoing"]:
            if entity_type not in relationship_cache[related_type]["outgoing"]:
                logger.info(
                    f"Adding missing bi-directional relationship from {related_type} to {entity_type}"
                )
                relationship_cache[related_type]["outgoing"].setdefault(
                    entity_type, set()
                )


def build_relationship_schema_cache(schema_cache, relationship_cache, schema_table=None):
    """
    Build the schema portion of the relationship cache.
    This processes schema information to determine relationships between entity types.

    Args:
        schema_cache: Schema cache dictionary containing all schemas
        relationship_cache: The relationship cache dictionary to populate
        schema_table: DynamoDB table for schemas (for fallback)
    """
    logger.info("Building relationship schema cache")

    # Get all entity types including custom assets from schema cache
    entity_types = get_entity_types(schema_cache)

    # Initialize cache structure for all entity types
    initialize_cache_structure(entity_types, relationship_cache)

    # Fetch schemas and process relationships
    for entity_type in entity_types:
        fetch_and_process_schema(entity_type, schema_cache, relationship_cache, schema_table)

    # Fill in missing bi-directional relationships
    fill_missing_bidirectional_relationships(entity_types, relationship_cache)

    logger.info("Relationship schema cache built successfully")