"""
Entity management module for the Migration Factory solution.

This module contains classes for managing entities and their relationships,
including tracking updates, handling relationships, and processing entity operations.

Author: AWS Professional Services
"""

import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger()

CONTAINER_TYPES = ["move_group", "wave"]

def normalize_server_count(value: Any) -> int:
    """Convert server_count value to integer regardless of input type.

    Args:
        value: The server_count value which could be string, int, or None

    Returns:
        Integer representation of the value, or 0 if None
    """
    if value is None:
        return 0
    if isinstance(value, str):
        return int(value)
    return int(value)  # Ensure it's an integer


def normalize_list_value(value: Any) -> List:
    """
    Normalize a value to ensure it's a list.

    Args:
        value: Value to normalize

    Returns:
        Normalized list value
    """
    if value is None:
        return []
    elif not isinstance(value, list):
        return [value]
    return value


def get_current_attribute_value(
    attr_name: str, entity: Dict, existing_updates: Dict
) -> Any:
    """
    Get the current value of an attribute, considering pending updates.

    Args:
        attr_name: Name of the attribute
        entity: Entity dictionary
        existing_updates: Dictionary of pending updates

    Returns:
        Current value of the attribute
    """
    # For multi-value relationships with pending updates
    if attr_name.endswith("_ids") and attr_name in existing_updates:
        current_value = existing_updates[attr_name]
        if isinstance(current_value, list):
            return current_value
        else:
            return [current_value] if current_value is not None else []
    # Use entity's current value if available
    elif attr_name in entity:
        return entity[attr_name]
    # Default to None
    else:
        return None


def update_multivalue_relationship(
    current_value: Any, related_id: str, operation: str
) -> List:
    """
    Update a multi-value relationship attribute.

    Args:
        current_value: Current value of the attribute
        related_id: ID of the related entity
        operation: 'add' or 'remove'

    Returns:
        Updated list of related IDs
    """
    # Ensure we're working with a list
    if current_value is None:
        current_value = []
    elif not isinstance(current_value, list):
        current_value = [current_value]

    # Add or remove the related ID
    if operation == "add" and related_id not in current_value:
        return current_value + [related_id]
    elif operation == "remove" and related_id in current_value:
        return [id for id in current_value if id != related_id]

    # No change needed
    return None


def update_singlevalue_relationship(
    current_value: Any, related_id: str, operation: str
) -> Any:
    """
    Update a single-value relationship attribute.

    Args:
        current_value: Current value of the attribute
        related_id: ID of the related entity
        operation: 'add' or 'remove'

    Returns:
        Updated value or None if no change needed
    """
    if operation == "add":
        return related_id
    elif operation == "remove" and current_value == related_id:
        return None

    # No change needed
    return None


def group_entities_by_type(target_entities: List[Dict]) -> Dict[str, List[str]]:
    """
    Group target entities by type.

    Args:
        target_entities: List of entities to move

    Returns:
        Dictionary mapping entity types to lists of entity IDs
    """
    entities_by_type = {}
    for entity in target_entities:
        entity_type = entity["entity_type"]
        entity_id = entity["entity_id"]

        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []

        entities_by_type[entity_type].append(entity_id)

    return entities_by_type


class EntityManager:
    """
    Class for managing entities and their relationships.
    """

    def __init__(self, dynamodb_manager, relationship_cache, entity_cache, relationship_updates):
        """
        Initialize the EntityManager.

        Args:
            dynamodb_manager: DynamoDBManager instance for database operations
            relationship_cache: Cache of entity relationships
            entity_cache: Cache of entities
            relationship_updates: Dictionary tracking relationship updates
        """
        self.dynamodb_manager = dynamodb_manager
        self.table_names = dynamodb_manager.table_names
        self.relationship_cache = relationship_cache
        self.entity_cache = entity_cache
        self.relationship_updates = relationship_updates
    
    def set_entity_cache(self, entity_cache):
        """
        Set the entity cache.

        Args:
            entity_cache: Entity cache to set
        """
        self.entity_cache = entity_cache
        
    def get_entity(self, entity_type: str, entity_id: str) -> Dict:
        """
        Retrieve an entity from the entity cache or from its corresponding DynamoDB table.

        Args:
            entity_type: Type of the entity (e.g., 'app', 'server')
            entity_id: ID of the entity

        Returns:
            The entity as a dictionary or None if not found
        """
        return self.dynamodb_manager.get_entity(self.entity_cache, entity_type, entity_id)

    def initialize_entity_in_cache(self, entity_type, entity_id):
        """
        Initialize an entity in the relationship cache.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
        """
        # Initialize child_ids for this entity with empty dict
        self.relationship_cache[entity_type]["child_ids"][entity_id] = {}

    def process_multivalue_relationship(self, entity_type, entity_id, related_type, related_id):
        """
        Process a multi-value relationship.

        Args:
            entity_type: Source entity type
            entity_id: Source entity ID
            related_type: Related entity type
            related_id: Related entity ID
        """
        # Only populate based on strict parent-child relationships
        if related_type in self.relationship_cache[entity_type]["children"]:
            # Add related ID to child_ids
            self.relationship_cache[entity_type]["child_ids"].setdefault(entity_id, {}).setdefault(
                related_type, set()
            ).add(related_id)
            
            # Update parent_ids for the related entity
            self.relationship_cache[related_type]["parent_ids"].setdefault(
                related_id, {}
            ).setdefault(entity_type, set()).add(entity_id)
        elif related_type in self.relationship_cache[entity_type]["parents"]:
            # Add related ID to parent_ids
            self.relationship_cache[entity_type]["parent_ids"].setdefault(entity_id, {}).setdefault(
                related_type, set()
            ).add(related_id)
            
            # Update child_ids for the related entity
            self.relationship_cache[related_type]["child_ids"].setdefault(
                related_id, {}
            ).setdefault(entity_type, set()).add(entity_id)

    def process_singlevalue_relationship(self, entity_type, entity_id, related_type, related_id):
        """
        Process a single-value relationship.

        Args:
            entity_type: Source entity type
            entity_id: Source entity ID
            related_type: Related entity type
            related_id: Related entity ID
        """
        # Determine relation type
        relation_type = (
            "child"
            if related_type in self.relationship_cache[entity_type]["children"]
            else "parent"
        )
        reverse_relation_type = (
            "parent"
            if related_type in self.relationship_cache[entity_type]["children"]
            else "child"
        )

        # Update child_ids for this entity - use dict.setdefault for cleaner initialization
        self.relationship_cache[entity_type][f"{relation_type}_ids"].setdefault(
            entity_id, {}
        ).setdefault(related_type, set()).add(related_id)

        # Update parent_ids for the related entity - use dict.setdefault for cleaner initialization
        self.relationship_cache[related_type][f"{reverse_relation_type}_ids"].setdefault(
            related_id, {}
        ).setdefault(entity_type, set()).add(entity_id)

    def process_entity_attributes(self, entity_type, entity_id, entity, attr_names, related_type):
        """
        Process entity attributes for a specific related type.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            entity: Entity dictionary
            attr_names: Set of attribute names
            related_type: Related entity type
        """
        for attr_name in attr_names:
            if attr_name not in entity:
                continue

            # Handle both single and multi-value relationships
            if isinstance(entity[attr_name], list):
                for related_id in entity[attr_name]:
                    if related_id:
                        self.process_multivalue_relationship(
                            entity_type, entity_id, related_type, related_id
                        )
            elif entity[attr_name]:
                related_id = entity[attr_name]
                self.process_singlevalue_relationship(
                    entity_type, entity_id, related_type, related_id
                )

    def process_entity_relationships(self, entity_type, entity_id, entity):
        """
        Process all relationships for an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            entity: Entity dictionary
        """
        # Initialize entity in cache
        self.initialize_entity_in_cache(entity_type, entity_id)

        # Process outgoing relationships (children)
        for related_type, attr_names in self.relationship_cache[entity_type]["outgoing"].items():
            self.process_entity_attributes(
                entity_type, entity_id, entity, attr_names, related_type
            )

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """
        Track entity deletion in the central dictionary without deleting from DynamoDB.

        Args:
            entity_type: Type of the entity (e.g., 'app', 'server')
            entity_id: ID of the entity

        Returns:
            True always as we're just tracking changes
        """
        # Track the entity deletion in the central dictionary
        if entity_type not in self.relationship_updates:
            self.relationship_updates[entity_type] = {}

        self.relationship_updates[entity_type][entity_id] = {"__deleted": True}

        logger.info(f"Tracked deletion of {entity_type} with ID {entity_id}")
        return True

    def ensure_entity_update_structure(self, entity_type: str, entity_id: str) -> None:
        """
        Ensure the update structure exists for an entity.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
        """
        self.relationship_updates.setdefault(entity_type, {}).setdefault(entity_id, {})

    def update_multivalue_attribute(self, entity_type: str, entity_id: str, attr: str, value: Any, operation = "add") -> None:
        """
        Update a multi-value attribute in the relationship updates.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            attr: Attribute name
            value: New value
            operation (optional): The type of update operation to perform:
                - "add" (default): Merges the new value with existing list value
                - "remove": Replaces the existing value with the new value
        """
        value = normalize_list_value(value)

        # If we already have updates for this attribute
        if attr in self.relationship_updates[entity_type][entity_id]:
            existing_value = normalize_list_value(
                self.relationship_updates[entity_type][entity_id][attr]
            )

            # For empty list values, use them directly (this is for clearing lists)
            if len(value) == 0:
                self.relationship_updates[entity_type][entity_id][attr] = []
            elif operation == "remove":
                self.relationship_updates[entity_type][entity_id][attr] = value    
            else:
                # Otherwise merge lists, ensuring no duplicates
                merged_list = list(existing_value)
                for item in value:
                    if item not in merged_list:
                        merged_list.append(item)
                self.relationship_updates[entity_type][entity_id][attr] = merged_list
        else:
            # No existing updates, just use the value
            self.relationship_updates[entity_type][entity_id][attr] = value

    def update_entity(self, entity_type: str, entity_id: str, updates: Dict, operation = "add") -> bool:
        """
        Track entity updates in the central dictionary without updating DynamoDB.
        Also updates the entity cache to ensure consistent state.

        Args:
            entity_type: Type of the entity (e.g., 'app', 'server')
            entity_id: ID of the entity
            updates: Dictionary of attribute updates
            operation (optional): The type of update operation to perform:
                - "add" (default): Merges the new value with existing list value
                - "remove": Replaces the existing value with the new value

        Returns:
            True always as we're just tracking changes
        """
        # Ensure update structure exists
        self.ensure_entity_update_structure(entity_type, entity_id)

        # Add updates to the central dictionary
        for attr, value in updates.items():
            # Special handling for server_count to ensure it's an integer
            if attr == "server_count" and value is not None:
                value = normalize_server_count(value)

            # Special handling for multi-value attributes (ending with _ids)
            if attr.endswith("_ids"):
                self.update_multivalue_attribute(entity_type, entity_id, attr, value, operation)
            else:
                # For non-multi-value attributes, just set the value
                self.relationship_updates[entity_type][entity_id][attr] = value

            # Update the entity cache to maintain consistency
            if entity_type in self.entity_cache and entity_id in self.entity_cache[entity_type]:
                self.entity_cache[entity_type][entity_id][attr] = value

        logger.info(f"Tracked update for {entity_type} with ID {entity_id} updates={updates}")
        return True

    def get_related_entities(self, entity_type: str, entity_id: str) -> Dict[str, List[str]]:
        """
        Get all entities related to the specified entity.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity

        Returns:
            Dictionary mapping entity types to lists of entity IDs
        """
        return self.relationship_cache[entity_type]["child_ids"][entity_id]

    def update_relationship(self, entity_type: str, entity_id: str, related_type: str, related_id: str, operation: str) -> bool:
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
        entity = self.get_entity(entity_type, entity_id)
        if not entity:
            return False

        # Find the attribute that holds the relationship
        attr_names = self.relationship_cache[entity_type]["outgoing"].get(related_type, [])
        if not attr_names:
            logger.warning(f"No relationship found from {entity_type} to {related_type}")
            return False

        # Get existing updates if any
        existing_updates = self.relationship_updates.get(entity_type, {}).get(entity_id, {})

        updates = {}
        for attr_name in attr_names:
            # Get current value considering pending updates
            current_value = get_current_attribute_value(attr_name, entity, existing_updates)

            # Process based on attribute type
            if attr_name.endswith("_ids"):
                new_value = update_multivalue_relationship(
                    current_value, related_id, operation
                )
                if new_value is not None:
                    updates[attr_name] = new_value
            else:
                new_value = update_singlevalue_relationship(
                    current_value, related_id, operation
                )
                if new_value is not None:
                    updates[attr_name] = new_value
            
        if updates:
            # Call update_entity which now only tracks changes
            return self.update_entity(entity_type, entity_id, updates, operation)
        return True

    def update_preserved_entity_references(self, child_type: str, child_ids: set, entity_type: str, entity_id: str, update_app_planning_status_fn=None) -> None:
        """
        Update references for entities that should be preserved.

        Args:
            child_type: Type of the child entity
            child_ids: Set of child entity IDs
            entity_type: Type of the parent entity being deleted
            entity_id: ID of the parent entity being deleted
            update_app_planning_status_fn: Optional function to update app planning status
        """
        logger.info(
            f"Tracking updates for {len(child_ids)} {child_type} entities to remove references to {entity_type}:{entity_id}"
        )

        for child_id in child_ids:
            child_entity = self.get_entity(child_type, child_id)
            if not child_entity:
                logger.warning(f"Child entity {child_type}:{child_id} not found")
                continue

            # Find attributes in the child that reference this entity
            for attr_name in self.relationship_cache[child_type]["outgoing"].get(
                entity_type, []
            ):
                if attr_name not in child_entity:
                    continue

                # Handle list attributes
                if isinstance(child_entity[attr_name], list):
                    if entity_id in child_entity[attr_name]:
                        new_list = [id for id in child_entity[attr_name] if id != entity_id]
                        self.update_entity(child_type, child_id, {attr_name: new_list})
                        logger.info(
                            f"Tracked removal of {entity_type}:{entity_id} from {child_type}:{child_id}.{attr_name}"
                        )
                # Handle single value attributes
                elif child_entity[attr_name] == entity_id:
                    self.update_entity(child_type, child_id, {attr_name: None})
                    logger.info(
                        f"Tracked removal of {entity_type}:{entity_id} from {child_type}:{child_id}.{attr_name}"
                    )

            # Update app planning_status if this is a server or database
            if update_app_planning_status_fn and child_type in ["server", "database"] and "app_ids" in child_entity:
                for app_id in child_entity["app_ids"]:
                    update_app_planning_status_fn(app_id)

    def remove_incoming_references(self, entity_type: str, entity_id: str, containers_only: bool) -> None:
        """
        Remove all incoming references to an entity.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            containers_only: If True, only remove references from containers
        """
        # Get incoming relationships (entities that reference this entity)
        parent_ids = self.relationship_cache[entity_type]["parent_ids"].get(entity_id, {})
        
        for ref_type, ref_ids in parent_ids.items():
            if containers_only and ref_type not in CONTAINER_TYPES:
                continue
            for ref_id in ref_ids:
                self.update_relationship(ref_type, ref_id, entity_type, entity_id, "remove")

    def update_server_count(self, entity_type: str, entity_id: str, count_change: int) -> None:
        """
        Update server_count for an entity using relationship_updates.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            count_change: Change to apply to server_count (positive or negative)
        """
        if entity_type not in CONTAINER_TYPES:
            return

        entity = self.get_entity(entity_type, entity_id)
        if not entity:
            return

        # Convert to int using our utility function
        current_count = normalize_server_count(entity.get("server_count", 0))

        new_count = max(0, current_count + count_change)  # Ensure count doesn't go below 0

        # Use update_entity to track the change in relationship_updates
        self.update_entity(entity_type, entity_id, {"server_count": new_count})
        logger.info(
            f"Updated {entity_type} {entity_id} server_count from {current_count} to {new_count}"
        )

    def initialize_server_count(self, entity_type: str, entity_id: str) -> None:
        """
        Initialize server_count for an entity if it doesn't exist.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
        """
        if entity_type not in CONTAINER_TYPES:
            return

        entity = self.get_entity(entity_type, entity_id)
        if not entity:
            return

        # Convert existing server_count to int using our utility function
        if "server_count" in entity:
            count = normalize_server_count(entity["server_count"])
            self.update_entity(entity_type, entity_id, {"server_count": count})
            logger.info(
                f"Normalized {entity_type} {entity_id} server_count to int: {count}"
            )
        else:
            # Count servers in the entity
            server_ids = entity.get("server_ids", [])
            count = len(server_ids) if server_ids else 0
            self.update_entity(entity_type, entity_id, {"server_count": int(count)})
            logger.info(f"Initialized {entity_type} {entity_id} server_count to {count}")