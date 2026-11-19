"""
DynamoDB operations module for the Migration Factory solution.

This module contains a class for interacting with DynamoDB tables,
including formatting values, creating transaction items, and committing transactions.

Author: AWS Professional Services
"""

import logging
import boto3
import json
import time
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Dict, List
from collections import namedtuple
import item_custom_assets

# Configure logging
logger = logging.getLogger()

# Define a named tuple for update expression parts
UpdateExpressionParts = namedtuple(
    "UpdateExpressionParts",
    ["update_parts", "remove_parts", "attr_values", "attr_names"],
)


def set_default(obj):
    """
    Helper function for JSON serialization of sets and Decimal types.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Serializable version of the object
    """
    if isinstance(obj, set):
        return list(obj)
    # Handle Decimal type from DynamoDB
    if hasattr(obj, "to_eng_string"):  # Check for Decimal type
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


class DynamoDBManager:
    """
    Class for managing DynamoDB operations.
    """

    def __init__(self, table_names):
        """
        Initialize the DynamoDBManager.

        Args:
            table_names: Dictionary mapping entity types to table names
        """
        self.table_names = table_names
        self.dynamodb = boto3.resource("dynamodb")
        
        # Configure retry strategy using boto3 config
        self.config = Config(
            retries={
                'mode': 'standard',
                'total_max_attempts': 3
            }
        )

    def get_entity(self, entity_cache, entity_type: str, entity_id: str) -> Dict:
        """
        Retrieve an entity from the entity cache or from its corresponding DynamoDB table.

        Args:
            entity_cache: Cache of entities
            entity_type: Type of the entity (e.g., 'app', 'server')
            entity_id: ID of the entity

        Returns:
            The entity as a dictionary or None if not found
        """
        # Check if the entity is in the cache first
        if entity_type in entity_cache and entity_id in entity_cache[entity_type]:
            return entity_cache[entity_type][entity_id]

        try:
            # Handle custom assets
            if entity_type not in self.table_names:
                custom_assets_table = self.get_custom_assets_table()
                shard_number = item_custom_assets.get_shard_number(entity_id)
                key = {
                    "asset_type#shard": f"{entity_type}#{shard_number}",
                    "asset_id": entity_id
                }
                response = custom_assets_table.get_item(Key=key)
                entity = response.get("Item")
                
                if entity:
                    # Convert from DB format to API format
                    entity = item_custom_assets.adapt_item_to_schema(entity, entity_type, 'custom')
            else:
                # Handle built-in entity types
                table = self.dynamodb.Table(self.table_names[entity_type])
                key = {f"{entity_type}_id": entity_id}
                response = table.get_item(Key=key)
                entity = response.get("Item")

            # Store in cache for future use
            if entity:
                if entity_type not in entity_cache:
                    entity_cache[entity_type] = {}
                entity_cache[entity_type][entity_id] = entity

            return entity
        except ClientError as e:
            logger.error(f"Error getting {entity_type} with ID {entity_id}: {str(e)}")
            return None

    def format_ddb_value(self, value, attr_name=None):
        """
        Format a value with the appropriate DynamoDB type descriptor.

        Args:
            value: The value to format
            attr_name: Optional attribute name for context-specific formatting

        Returns:
            Dictionary with DynamoDB type descriptor
        """
        if value is None:
            return {"NULL": True}
        elif isinstance(value, str):
            # Special handling for server_count attributes - always store as number
            if attr_name and attr_name in ["server_count", "total_server_count"]:
                if value.isdigit():
                    return {"N": value}
            return {"S": value}
        elif isinstance(value, bool):
            return {"BOOL": value}
        elif isinstance(value, (int, float)):
            return {"N": str(value)}
        elif isinstance(value, list):
            # Always use List type for lists to ensure consistent behavior
            return {"L": [self.format_ddb_value(item) for item in value]}
        elif isinstance(value, dict):
            return {"M": {k: self.format_ddb_value(v) for k, v in value.items()}}
        elif isinstance(value, set):
            # Convert sets to lists
            return {"L": [self.format_ddb_value(item) for item in list(value)]}
        else:
            # Default to string representation
            return {"S": str(value)}

    def create_update_expression(self, updates: Dict) -> UpdateExpressionParts:
        """
        Create DynamoDB update expression parts.

        Args:
            updates: Dictionary of updates

        Returns:
            UpdateExpressionParts named tuple with fields:
            - update_parts: List of SET expression parts
            - remove_parts: List of REMOVE expression parts
            - attr_values: Dictionary of expression attribute values
            - attr_names: Dictionary of expression attribute names
        """
        update_expr_parts = []
        remove_expr_parts = []
        expr_attr_values = {}
        expr_attr_names = {}

        for i, (attr, value) in enumerate(updates.items()):
            attr_name = f"#{attr}"
            expr_attr_names[attr_name] = attr
            placeholder = f":val{i}"

            if value is None and attr.endswith("_id"):
                # Remove attributes ending with _id if value is None
                remove_expr_parts.append(attr_name)
            else:
                # Set value for other attributes with proper DynamoDB type descriptor
                expr_attr_values[placeholder] = self.format_ddb_value(value, attr)
                update_expr_parts.append(f"{attr_name} = {placeholder}")

        return UpdateExpressionParts(
            update_parts=update_expr_parts,
            remove_parts=remove_expr_parts,
            attr_values=expr_attr_values,
            attr_names=expr_attr_names,
        )

    def build_update_expression(self, update_expr_parts: List, remove_expr_parts: List) -> str:
        """
        Build the complete update expression.

        Args:
            update_expr_parts: List of update expression parts
            remove_expr_parts: List of remove expression parts

        Returns:
            Complete update expression
        """
        update_expr = ""
        if update_expr_parts:
            update_expr = "SET " + ", ".join(update_expr_parts)

        if remove_expr_parts:
            if update_expr:
                update_expr += " "
            update_expr += "REMOVE " + ", ".join(remove_expr_parts)

        return update_expr

    def _get_table_and_key(self, entity_type: str, entity_id: str) -> tuple:
        """
        Get the table name and key structure for an entity.
        
        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            
        Returns:
            Tuple of (table_name, key)
        """
        if entity_type in self.table_names:
            table_name = self.table_names[entity_type]
            key = {f"{entity_type}_id": {"S": entity_id}}
        else:
            table_name = self.table_names["custom_assets"]
            shard_number = item_custom_assets.get_shard_number(entity_id)
            key = {"asset_type#shard": {"S": f"{entity_type}#{shard_number}"}, "asset_id": {"S": entity_id}}
        return table_name, key

    def create_delete_transaction_item(self, entity_type: str, entity_id: str) -> Dict:
        """
        Create a delete transaction item.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity

        Returns:
            Delete transaction item
        """
        table_name, key = self._get_table_and_key(entity_type, entity_id)
        return {"Delete": {"TableName": table_name, "Key": key}}

    def create_update_transaction_item(self, entity_type: str, entity_id: str, updates: Dict) -> Dict:
        """
        Create an update transaction item.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            updates: Dictionary of updates

        Returns:
            Update transaction item or None if no updates
        """
        table_name, key = self._get_table_and_key(entity_type, entity_id)

        # Build update expression parts
        expr_parts = self.create_update_expression(updates)

        # Build the complete update expression
        update_expr = self.build_update_expression(
            expr_parts.update_parts, expr_parts.remove_parts
        )

        # Only create update item if there are expressions
        if not update_expr:
            return None

        update_item = {
            "Update": {
                "TableName": table_name,
                "Key": key,
                "UpdateExpression": update_expr,
                "ExpressionAttributeNames": expr_parts.attr_names,
            }
        }

        if expr_parts.attr_values:
            update_item["Update"]["ExpressionAttributeValues"] = expr_parts.attr_values

        return update_item

    def create_transaction_items(self, relationship_updates):
        """
        Convert relationship_updates dictionary into DynamoDB transaction items.

        Args:
            relationship_updates: Dictionary of tracked updates

        Returns:
            List of DynamoDB transaction items for TransactWriteItems operation
        """
        transaction_items = []

        for entity_type, entities in relationship_updates.items():

            for entity_id, updates in entities.items():
                # Check if this is a delete operation
                if "__deleted" in updates and updates["__deleted"]:
                    transaction_items.append(
                        self.create_delete_transaction_item(entity_type, entity_id)
                    )
                else:
                    # Create update transaction item
                    update_item = self.create_update_transaction_item(
                        entity_type, entity_id, updates
                    )
                    if update_item:
                        transaction_items.append(update_item)

        return transaction_items

    def commit_transactions(self, transaction_items):
        """
        Commit transaction items to DynamoDB in batches of 100 items.
        Uses the AWS SDK's built-in retry configuration for handling transient errors.

        Args:
            transaction_items: List of transaction items to commit

        Returns:
            List of transaction results
        """
        results = []
        MAX_TRANSACTION_ITEMS = 100

        # Create DynamoDB client with retry configuration
        client = boto3.client("dynamodb", config=self.config)

        logger.info(f"commit_transactions: {json.dumps(transaction_items, default=str, indent=2)}")

        # Split transaction items into batches of 100
        for i in range(0, len(transaction_items), MAX_TRANSACTION_ITEMS):
            batch = transaction_items[i : i + MAX_TRANSACTION_ITEMS]
            batch_num = i // MAX_TRANSACTION_ITEMS + 1

            try:
                # Execute the transaction with built-in retry handling
                response = client.transact_write_items(TransactItems=batch)
                results.append(
                    {
                        "status": "success",
                        "batch": batch_num,
                        "items_count": len(batch),
                    }
                )
                logger.info(
                    f"Successfully committed transaction batch {batch_num} with {len(batch)} items"
                )
            except ClientError as e:
                # Extract error code safely
                error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
                logger.error(
                    f"Error committing transaction batch {batch_num}: {str(e)}"
                )
                results.append(
                    {
                        "status": "error",
                        "batch": batch_num,
                        "error": str(e),
                        "items_count": len(batch),
                    }
                )

        return results
        
    def get_schema_table(self):
        """
        Get the schema table from DynamoDB.
        
        Returns:
            DynamoDB Table resource for the schema table
        """
        return self.dynamodb.Table(self.table_names["schema"])
        
    def build_entity_cache(self, entity_types, entity_cache, entity_manager):
        """
        Build the entity cache by loading entities from DynamoDB tables.
        Uses pagination to handle large tables efficiently.

        Args:
            entity_types: List of entity type names (includes custom asset types)
            entity_cache: Dictionary to store entities
            entity_manager: EntityManager instance to process relationships
            
        Returns:
            Updated entity_cache
        """
        if not entity_cache:
            entity_cache = {}

        for entity_type in entity_types:
            # Check if this is a built-in entity type or custom asset type
            if entity_type in self.table_names:
                # Built-in entity type - use regular table scan
                try:
                    table = self.dynamodb.Table(self.table_names[entity_type])

                    # Initialize cache for this entity type
                    if entity_type not in entity_cache:
                        entity_cache[entity_type] = {}

                    # Use pagination to handle large tables
                    scan_kwargs = {}
                    done = False
                    start_time = time.time()
                    items_processed = 0

                    while not done:
                        response = table.scan(**scan_kwargs)
                        entities = response.get("Items", [])
                        items_processed += len(entities)

                        # Process each entity
                        for entity in entities:
                            entity_id = entity.get(f"{entity_type}_id")
                            if not entity_id:
                                continue

                            # Store entity in cache
                            entity_cache[entity_type][entity_id] = entity

                            # Process relationships
                            entity_manager.process_entity_relationships(entity_type, entity_id, entity)

                        # Check if we need to paginate
                        if "LastEvaluatedKey" in response:
                            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                        else:
                            done = True

                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"Processed {items_processed} {entity_type} entities in {elapsed_time:.2f} seconds"
                    )

                except ClientError as e:
                    logger.error(f"Error scanning {entity_type} table: {str(e)}")
            else:
                # Custom asset type - use query_custom_assets
                try:
                    custom_assets_table = self.get_custom_assets_table()
                    start_time = time.time()
                    
                    # Use query_custom_assets to get all items for this type
                    entities = item_custom_assets.query_custom_assets(custom_assets_table, entity_type)
                    
                    # Initialize cache for this custom asset type
                    if entity_type not in entity_cache:
                        entity_cache[entity_type] = {}
                    
                    # Process each custom asset
                    for entity in entities:
                        entity_id = entity.get("asset_id")
                        if not entity_id:
                            continue
                        
                        # Store entity in cache
                        entity_cache[entity_type][entity_id] = item_custom_assets.adapt_item_to_schema(entity, entity_type, 'custom')
                        
                        # Process relationships
                        entity_manager.process_entity_relationships(entity_type, entity_id, entity)
                    
                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"Processed {len(entities)} {entity_type} custom assets in {elapsed_time:.2f} seconds"
                    )
                    
                except ClientError as e:
                    logger.error(f"Error querying custom assets for {entity_type}: {str(e)}")
                
        return entity_cache
        
    def get_custom_assets_table(self):
        """
        Get the custom_assets table from DynamoDB.
        
        Returns:
            DynamoDB Table resource for the custom_assets table
        """
        return self.dynamodb.Table(self.table_names["custom_assets"])
    
    def _get_custom_asset_types(self):
        """
        Get list of custom asset types from schema table.
        
        Returns:
            List of custom asset type names
        """
        try:
            schema_table = self.get_schema_table()
            response = schema_table.scan(
                FilterExpression="schema_type = :schema_type",
                ExpressionAttributeValues={
                    ":schema_type": "custom"
                }
            )
            return [item["schema_name"] for item in response.get("Items", [])]
        except ClientError as e:
            logger.error(f"Error getting custom asset types: {str(e)}")
            return []