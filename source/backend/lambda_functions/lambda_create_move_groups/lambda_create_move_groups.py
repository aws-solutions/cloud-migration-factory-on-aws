import json
import logging
import os
import random
import re
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Iterable,
    TypeVar,
)
from ulid import ULID

import cmf_boto
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import item_custom_assets

from policy import MFAuth
from cmf_utils import update_job_array_field, default_http_headers, convert_floats_to_decimal, send_anonymous_usage_data
from item_validation import validate_id_string, validate_id_list

# Constants

schema_table_name = os.environ["SCHEMA_TABLE_NAME"]
rules_table_name = os.environ["RULES_TABLE_NAME"]
apps_table_name = os.environ["APPS_TABLE_NAME"]
servers_table_name = os.environ["SERVERS_TABLE_NAME"]
databases_table_name = os.environ["DATABASES_TABLE_NAME"]
move_groups_table_name = os.environ["MOVE_GROUPS_TABLE_NAME"]
move_group_requests_table_name = os.environ["MOVE_GROUP_REQUESTS_TABLE_NAME"]
jobs_table_name = os.environ["WPM_JOBS_TABLE_NAME"]
custom_assets_table_name = os.environ["CUSTOM_ASSETS_TABLE_NAME"]

built_in_asset_types = ['app', 'server', 'database']

# Validation constants
MAX_APP_IDS_COUNT = 100

TABLE_NAMES = {
    "schema": schema_table_name,
    "rules": rules_table_name,
    "apps": apps_table_name,
    "servers": servers_table_name,
    "databases": databases_table_name,
    "move_groups": move_groups_table_name,
    "move_group_requests": move_group_requests_table_name,
    "jobs": jobs_table_name,
    "custom_assets": custom_assets_table_name,
}

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


T = TypeVar("T")


@dataclass(frozen=True)
class Asset:
    """
    Represents an asset in the migration system with its properties and relationships.

    Attributes:
        asset_id: Unique identifier for the asset
        asset_name: Display name of the asset
        asset_type: Type of asset (app, server, database, etc.)
        attributes: Dictionary of asset attributes
        storage_size: Size of the asset storage in GB
        complexity_score: Complexity score for migration planning
        _relationships: Dictionary mapping relationship names to related asset IDs
    """

    asset_id: str
    asset_name: str
    asset_type: str
    attributes: Dict[str, Any] = None
    storage_size: Optional[float] = None
    complexity_score: Optional[int] = 0
    _relationships: Dict[str, tuple] = None
    is_custom_asset: bool = False

    def __post_init__(self):
        """Initialize default values for mutable attributes."""
        if self.attributes is None:
            object.__setattr__(self, "attributes", {})
        if self._relationships is None:
            object.__setattr__(self, "_relationships", {})

    def __hash__(self):
        """
        Generate a hash for the asset based on its properties.

        Returns:
            int: Hash value for the asset
        """
        return hash(
            (
                self.asset_id,
                self.asset_name,
                self.asset_type,
                self.storage_size,
                self.complexity_score,
            )
        )

    def get_related_ids(self, relationship_name: str) -> tuple:
        """
        Get IDs of assets related through the specified relationship.

        Args:
            relationship_name: Name of the relationship

        Returns:
            tuple: IDs of related assets
        """
        return self._relationships.get(relationship_name, tuple())

    def set_related_ids(self, relationship_name: str, ids: Iterable[str]) -> None:
        """
        Set related asset IDs for a specific relationship.

        Args:
            relationship_name: Name of the relationship
            ids: Iterable of related asset IDs
        """
        self._relationships[relationship_name] = tuple(ids)
        
    @classmethod
    def from_custom_asset_item(cls, item: Dict[str, Any]) -> "Asset":
        """
        Create an Asset object from a custom asset DynamoDB item.
        
        Args:
            item: DynamoDB item representing a custom asset
            
        Returns:
            Asset: Asset object created from the custom asset data
        """
        # Extract asset_type and asset_id from the composite key
        asset_type_key = item.get("asset_type#shard", "")
        asset_type = asset_type_key.split("#")[0] if "#" in asset_type_key else asset_type_key
        asset_id = item.get("asset_id", "")
        
        # Create attributes dictionary excluding Asset class attributes
        asset_class_attrs = set(cls.__dataclass_fields__.keys())
        
        attributes = {}
        for key, value in item.items():
            if key not in asset_class_attrs:
                attributes[key] = value
        
        # Create the Asset object
        asset = cls(
            asset_id=f"{asset_type}-{asset_id}",
            asset_name=item.get("asset_name", asset_id),
            asset_type=asset_type,
            attributes=attributes,
            complexity_score=item.get("complexity_score", 0),
            is_custom_asset=True,
        )
        
        # Set relationships
        if "app_ids" in item and item["app_ids"]:
            asset.set_related_ids("app_ids", item["app_ids"])
            
        return asset


@dataclass
class MoveGroup:
    """
    Represents a group of assets to be migrated together.

    Attributes:
        move_group_id: Unique identifier for the move group
        move_group_name: Display name of the move group
        wave_id: Optional ID of the migration wave this group belongs to
        wpm_job_id: Optional ID of the WPM job this group is associated with
        server_count: Number of servers in this group
        total_server_storage: Total storage size of all servers in GB
        complexity_score: Calculated complexity score for migration planning
        app_ids: List of application IDs in this group
        server_ids: List of server IDs in this group
        database_ids: List of database IDs in this group
        _history: Dictionary containing audit information (created by, timestamp)
    """

    move_group_id: str
    move_group_name: str
    wave_id: Optional[str]
    wpm_job_id: Optional[str]
    server_count: int
    total_server_storage: float
    complexity_score: float
    app_ids: List[str]
    server_ids: List[str]
    database_ids: List[str]
    _history: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchemaAttribute:
    name: str
    type: str
    rel_entity: Optional[str] = None
    rel_key: Optional[str] = None
    rel_display_attribute: Optional[str] = None

    @classmethod
    def from_dynamodb(cls, data: Dict) -> "SchemaAttribute":
        """Create SchemaAttribute from DynamoDB attribute map"""
        return cls(
            name=data.get("name"),
            type=data.get("type"),
            rel_entity=data.get("rel_entity"),
            rel_key=data.get("rel_key"),
            rel_display_attribute=data.get("rel_display_attribute"),
        )


@dataclass(frozen=True)
class Schema:
    schema_name: str
    schema_type: str
    attributes: List[SchemaAttribute]

    @classmethod
    def from_dynamodb(cls, item: Dict) -> "Schema":
        """Create Schema from DynamoDB item"""
        attributes = [
            SchemaAttribute.from_dynamodb(attr) for attr in item.get("attributes", [])
        ]

        return cls(
            schema_name=item.get("schema_name", ""),
            schema_type=item.get("schema_type", ""),
            attributes=attributes,
        )


@dataclass(frozen=True)
class Rule:
    rule_id: str
    rule_type: str
    rule_name: str
    status: str
    relationships: List[Dict[str, str]]

    @classmethod
    def from_dynamodb(cls, item: Dict) -> "Rule":
        """Create Rule from DynamoDB item"""
        relationships = []
        for rel in item.get("relationships", []):
            relationships.append(
                {
                    "asset_key": rel.get("asset_key", ""),
                    "asset_type": rel.get("asset_type", ""),
                }
            )

        return cls(
            rule_id=item.get("rule_id", ""),
            rule_type=item.get("rule_type", ""),
            rule_name=item.get("rule_name", ""),
            status=item.get("status", ""),
            relationships=relationships,
        )

    def infer_relationships(self, schemas: Dict[str, Schema]) -> List[Dict[str, str]]:
        """Dynamically infers relationships based on schema definitions with multivalue-relationship priority."""
        inferred = []

        for rel in self.relationships:
            # Find the schema for this asset type
            source_schema = schemas.get(rel["asset_type"])
            if not source_schema:
                # This is a relationship for custom assets - validate required fields
                if "asset_key" not in rel or "asset_type" not in rel:
                    logger.warning(f"Skipping malformed relationship: {rel}")
                    continue
                    
                inferred.append(
                    {
                        "asset_key": rel["asset_key"],
                        "asset_type": rel["asset_type"],
                        "target_asset_type": rel["asset_type"],
                        "is_custom_asset": True,
                    }
                )                
                continue

            # Find the relationship attribute in the schema
            attr = next(
                (
                    attr
                    for attr in source_schema.attributes
                    if attr.name == rel["asset_key"]
                ),
                None,
            )

            if not attr:
                continue

            if attr.type != "relationship" and attr.type != "multivalue-relationship":
                inferred.append(
                    {
                        "asset_key": rel["asset_key"],
                        "asset_type": rel["asset_type"],
                        "target_asset_type": rel["asset_type"],
                        "is_custom_asset": source_schema.schema_type == "custom",
                    }
                )
                continue

            # Add original relationship
            inferred.append(
                {
                    "asset_key": rel["asset_key"],
                    "asset_type": rel["asset_type"],
                    "target_asset_type": attr.rel_entity,
                    "is_custom_asset": source_schema.schema_type == "custom",
                }
            )

            # Find the target schema
            target_schema = schemas.get(attr.rel_entity)
            if not target_schema:
                continue

            # Find reverse relationships in target schema, prioritizing multivalue-relationship
            multivalue_reverse_rels = [
                attr
                for attr in target_schema.attributes
                if attr.type == "multivalue-relationship"
                and attr.rel_entity == source_schema.schema_name
            ]

            # If no multivalue relationships found, look for regular relationships
            reverse_rels = (
                multivalue_reverse_rels
                if multivalue_reverse_rels
                else [
                    attr
                    for attr in target_schema.attributes
                    if attr.type == "relationship"
                    and attr.rel_entity == source_schema.schema_name
                ]
            )

            # Add reverse relationships
            for reverse_rel in reverse_rels:
                inferred.append(
                    {
                        "asset_key": reverse_rel.name,
                        "asset_type": target_schema.schema_name,
                        "target_asset_type": source_schema.schema_name,
                        "is_custom_asset": target_schema.schema_type == "custom",
                    }
                )

        return inferred


def get_custom_assets(custom_asset_types: list[str]) -> List[Asset]:
    """
    Retrieve custom assets from the custom assets table and convert them to Asset objects.
    Only loads if custom_asset_types is not empty.
    
    Args:
        custom_asset_types: List of custom asset types
        
    Returns:
        List[Asset]: List of Asset objects created from custom assets
    """
    if not custom_asset_types:
        logger.info("No custom asset types with rules, skipping custom asset loading")
        return []
        
    dynamodb = cmf_boto.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAMES["custom_assets"])
    assets = []

    try:
        for custom_asset_type in custom_asset_types:
            logger.info(f"Loading custom assets of type: {custom_asset_type}")
            custom_items = item_custom_assets.query_custom_assets(table, custom_asset_type)
            assets.extend(
                map(
                    lambda item: Asset.from_custom_asset_item(item),
                    custom_items,
                )
            )
            logger.info(f"Loaded {len(custom_items)} custom assets of type {custom_asset_type}")
    except ClientError as e:
        logger.error(f"Error retrieving custom assets: {str(e)}")
        raise RuntimeError(f"Failed to retrieve custom assets: {str(e)}") from e
        
    return assets

class DynamoDBManager:
    """
    Manages interactions with DynamoDB tables.

    Attributes:
        tables: Dictionary mapping table names to DynamoDB Table objects
        dynamodb: The DynamoDB resource
    """

    def __init__(self):
        """Initialize the DynamoDB manager with table references."""
        self.dynamodb = cmf_boto.resource("dynamodb")
        self.tables = {
            name: self.dynamodb.Table(table_name)
            for name, table_name in TABLE_NAMES.items()
        }
        
        # Add logging to debug table initialization
        logger.info(f"Initialized DynamoDBManager with TABLE_NAMES: {TABLE_NAMES}")
        logger.info(f"Table objects: {[(name, table.name) for name, table in self.tables.items()]}")

    def query_table(self, table_name: str, key_condition) -> List[Dict]:
        table = self.tables[table_name]
        items: List[Dict] = []
        query_kwargs = {"KeyConditionExpression": key_condition, "ConsistentRead": True}

        while True:
            response = table.query(**query_kwargs)
            items.extend(response["Items"])

            if "LastEvaluatedKey" not in response:
                break

            query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        return items

    def scan_table(self, table_name: str, filter_condition=None) -> List[Dict]:
        table = self.tables[table_name]
        items: List[Dict] = []
        scan_kwargs = {"ConsistentRead": True}

        if filter_condition:
            scan_kwargs["FilterExpression"] = filter_condition

        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            if "LastEvaluatedKey" not in response:
                break

            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        return items

    def update_move_group_request(
        self, move_group_request_id: str, updates: Dict[str, Any]
    ) -> bool:
        try:
            update_expression = "SET " + ", ".join(
                f"#{k} = :{k}" for k in updates.keys()
            )
            expression_attribute_names = {f"#{k}": k for k in updates.keys()}
            expression_attribute_values = {f":{k}": v for k, v in updates.items()}

            logger.info(
                f"Updating move group request {move_group_request_id} with updates: {json.dumps(updates)}"
            )

            self.tables["move_group_requests"].update_item(
                Key={"move_group_request_id": move_group_request_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
            )
            logger.info(
                f"Successfully updated move group request {move_group_request_id}"
            )
            return True
        except ClientError as e:
            logger.error(
                f"Error updating move group request {move_group_request_id}: {str(e)}"
            )
            return False
            
    def update_wpm_job(self, wpm_job_id: str, move_group_id: str) -> bool:
        """
        Updates a WPM job by adding a move_group_id to its move_group_ids array.
        
        Args:
            wpm_job_id: The ID of the WPM job to update
            move_group_id: The move group ID to add to the WPM job
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        
        # Use the shared utility function to update the move_group_ids field
        return update_job_array_field(
            table=self.tables["jobs"],
            wpm_job_id=wpm_job_id,
            item_id=move_group_id,
            field_name="move_group_ids"
        )

    def update_assets_with_move_group(self, move_group: MoveGroup) -> bool:
        """
        Updates apps, servers, and databases with move group ID and WPM job ID using batch operations.
        
        Args:
            move_group: The move group containing asset IDs to update
            
        Returns:
            bool: True if all updates were successful, False otherwise
        """
        if not move_group.move_group_id:
            logger.warning("Cannot update assets: Missing move_group_id")
            return False
        
        # Process each asset type separately to reduce complexity
        app_success = self._update_apps_with_move_group(move_group)
        server_success = self._update_servers_with_move_group(move_group)
        database_success = self._update_databases_with_move_group(move_group)
        
        return app_success and server_success and database_success
    
    def _validate_and_get_existing_items(self, asset_ids: List[str], table_name: str, id_field: str) -> Dict[str, Dict]:
        """
        Validates asset existence and retrieves existing items.
        
        Args:
            asset_ids: List of asset IDs to validate
            table_name: Name of the table to query
            id_field: Primary key field name
            
        Returns:
            Dictionary mapping asset IDs to their existing items
        """
        existing_items = {}
        if not asset_ids:
            return existing_items
            
        try:
            for asset_id in asset_ids:
                response = self.tables[table_name].get_item(Key={id_field: asset_id})
                if "Item" in response:
                    existing_items[asset_id] = response["Item"]
                else:
                    logger.warning(f"{table_name.capitalize()} ID {asset_id} not found in database, skipping update")
        except ClientError as e:
            logger.error(f"Error validating {table_name} items: {str(e)}")
            raise
        
        return existing_items
    
    def _process_batch_with_retry(self, batch_items: List[Dict], table_name: str) -> bool:
        """
        Processes batch write with retry mechanism for unprocessed items.
        
        Args:
            batch_items: List of batch write items
            table_name: Name of the table
            
        Returns:
            bool: True if all items were processed successfully
        """
        if not batch_items:
            return True
            
        success = True
        max_retries = 3
        
        # Process in chunks of 25 (DynamoDB limit)
        for i in range(0, len(batch_items), 25):
            batch_chunk = batch_items[i:i+25]
            unprocessed = batch_chunk
            retry_count = 0
            
            while unprocessed and retry_count < max_retries:
                try:
                    response = self.dynamodb.batch_write_item(
                        RequestItems={TABLE_NAMES[table_name]: unprocessed}
                    )
                    unprocessed = response.get("UnprocessedItems", {}).get(TABLE_NAMES[table_name], [])
                    
                    if unprocessed:
                        retry_count += 1
                        logger.info(f"Retrying {len(unprocessed)} unprocessed {table_name} items (attempt {retry_count})")
                except ClientError as e:
                    logger.error(f"Error in batch write for {table_name}: {str(e)}")
                    return False
            
            if unprocessed:
                logger.warning(f"Some {table_name} updates still not processed after retries: {len(unprocessed)} items")
                success = False
        
        return success
    
    def _update_apps_with_move_group(self, move_group: MoveGroup) -> bool:
        """
        Updates apps with move group ID and WPM job ID.
        
        Args:
            move_group: The move group containing app IDs to update
            
        Returns:
            bool: True if all updates were successful
        """
        if not move_group.app_ids:
            return True
            
        try:
            # Validate and get existing app items
            app_items = self._validate_and_get_existing_items(
                move_group.app_ids, "apps", "app_id"
            )
            
            # Prepare batch items only for existing apps
            app_batch_items = []
            for app_id in move_group.app_ids:
                if app_id not in app_items:
                    continue
                    
                item = app_items[app_id].copy()
                
                # Update move_group_ids as a list
                if "move_group_ids" not in item:
                    item["move_group_ids"] = [move_group.move_group_id]
                else:
                    if move_group.move_group_id not in item["move_group_ids"]:
                        item["move_group_ids"].append(move_group.move_group_id)
                    
                # Update wpm_job_ids if wpm_job_id exists
                if move_group.wpm_job_id:
                    if "wpm_job_ids" not in item:
                        item["wpm_job_ids"] = [move_group.wpm_job_id]
                    else:
                        if move_group.wpm_job_id not in item["wpm_job_ids"]:
                            item["wpm_job_ids"].append(move_group.wpm_job_id)
                
                app_batch_items.append({"PutRequest": {"Item": item}})
            
            return self._process_batch_with_retry(app_batch_items, "apps")
            
        except Exception as e:
            logger.error(f"Error updating apps: {str(e)}")
            return False
    
    def _update_servers_with_move_group(self, move_group: MoveGroup) -> bool:
        """
        Updates servers with move group ID and WPM job ID.
        
        Args:
            move_group: The move group containing server IDs to update
            
        Returns:
            bool: True if all updates were successful
        """
        if not move_group.server_ids:
            return True
            
        try:
            # Validate and get existing server items
            server_items = self._validate_and_get_existing_items(
                move_group.server_ids, "servers", "server_id"
            )
            
            # Prepare batch items only for existing servers
            server_batch_items = []
            for server_id in move_group.server_ids:
                if server_id not in server_items:
                    continue
                    
                item = server_items[server_id].copy()
                item["move_group_id"] = move_group.move_group_id
                
                if move_group.wpm_job_id:
                    item["wpm_job_id"] = move_group.wpm_job_id
                
                server_batch_items.append({"PutRequest": {"Item": item}})
            
            return self._process_batch_with_retry(server_batch_items, "servers")
            
        except Exception as e:
            logger.error(f"Error updating servers: {str(e)}")
            return False
    
    def _update_databases_with_move_group(self, move_group: MoveGroup) -> bool:
        """
        Updates databases with move group ID and WPM job ID.
        
        Args:
            move_group: The move group containing database IDs to update
            
        Returns:
            bool: True if all updates were successful
        """
        if not move_group.database_ids:
            return True
            
        try:
            # Validate and get existing database items
            database_items = self._validate_and_get_existing_items(
                move_group.database_ids, "databases", "database_id"
            )
            
            # Prepare batch items only for existing databases
            database_batch_items = []
            for database_id in move_group.database_ids:
                if database_id not in database_items:
                    continue
                    
                item = database_items[database_id].copy()
                item["move_group_id"] = move_group.move_group_id
                
                if move_group.wpm_job_id:
                    item["wpm_job_id"] = move_group.wpm_job_id
                
                database_batch_items.append({"PutRequest": {"Item": item}})
            
            return self._process_batch_with_retry(database_batch_items, "databases")
            
        except Exception as e:
            logger.error(f"Error updating databases: {str(e)}")
            return False


class AssetManager:
    """
    Manages asset-related operations including loading schemas and converting data to assets.
    """

    def __init__(self, db_manager: DynamoDBManager):
        """
        Initialize the AssetManager with a database manager.

        Args:
            db_manager: The DynamoDB manager to use for database operations
        """
        self.db_manager = db_manager
        self.schemas = self._load_schemas()

    def _load_schemas(self) -> Dict[str, Schema]:
        """
        Load schemas from the database.

        Returns:
            Dictionary mapping schema names to Schema objects

        Raises:
            ClientError: If there's an error accessing the database
        """
        try:
            schemas = {}
            raw_schemas = self.db_manager.scan_table("schema")
            for item in raw_schemas:
                schema = Schema.from_dynamodb(item)
                schemas[schema.schema_name] = schema
            logger.info(f"Loaded {len(schemas)} schemas")
            return schemas
        except Exception as e:
            logger.error(f"Error loading schemas: {str(e)}")
            raise

    def query_apps(self, app_ids: List[str]) -> List[Dict]:
        if not app_ids:
            return []

        apps = []
        for app_id in app_ids:
            apps.extend(self.db_manager.query_table("apps", Key("app_id").eq(app_id)))
        return apps

    def scan(self, table) -> List[Dict]:
        return self.db_manager.scan_table(table)


    def convert_to_assets(self, json_data: Dict[str, Any]) -> Dict[str, Asset]:
        assets = {}

        # Convert each type of data using its schema
        for entity_type, items in json_data.items():
            # Remove 's' from plural form to get schema name
            schema_name = entity_type[:-1] if entity_type.endswith("s") else entity_type
            if schema_name in self.schemas:
                schema = self.schemas[schema_name]
                for item in items:
                    asset = self.create_asset_from_data(item, schema)
                    assets[asset.asset_id] = asset

        return assets

    def create_asset_from_data(self, data: Dict[str, Any], schema: Schema) -> Asset:
        attributes = {}
        relationships = {}

        # Process each schema attribute
        for attr in schema.attributes:
            if attr.type in ("relationship", "multivalue-relationship"):
                # Convert relationship field names to standardized format
                rel_name = f"{attr.rel_entity}_ids"
                if attr.name in data:
                    # Handle both single and multi-value relationships
                    ids = data[attr.name]
                    if isinstance(ids, str):
                        ids = [ids]
                    relationships[rel_name] = tuple(ids)
            else:
                # Handle regular attributes
                if attr.name in data:
                    attributes[attr.name] = data[attr.name]

        asset = Asset(
            asset_id=f"{schema.schema_name}-{attributes[f'{schema.schema_name}_id']}",
            asset_name=attributes[f"{schema.schema_name}_name"],
            asset_type=schema.schema_name,
            attributes=attributes,
        )

        # Set relationships after creation
        for rel_name, ids in relationships.items():
            asset.set_related_ids(rel_name, ids)

        return asset


class MoveGroupManager:
    def __init__(self, db_manager: DynamoDBManager):
        self.custom_asset_types_used_by_rules = set()
        self.db_manager = db_manager
        self.schemas = self._load_schemas()
        self.rules = self._load_rules()

    def _load_schemas(self) -> Dict[str, Schema]:
        """Load schemas from DynamoDB table"""
        schemas = {}
        try:
            raw_schemas = self.db_manager.scan_table("schema")
            for item in raw_schemas:
                schema = Schema.from_dynamodb(item)
                schemas[schema.schema_name] = schema
        except Exception as e:
            logger.error(f"Error loading schemas: {str(e)}")
            raise
        return schemas

    def _load_rules(self) -> List[Rule]:
        """Load rules from DynamoDB table"""
        rules = []
        try:
            raw_rules = self.db_manager.scan_table("rules")
            for item in raw_rules:
                rule = Rule.from_dynamodb(item)
                if rule.status == "ENABLED":
                    rules.append(rule)
                for relationship in rule.relationships:
                    # Check both asset_type and the asset_type derived from asset_key
                    # For rule like "asset_type": "app", "asset_key": "storage_ids"
                    asset_type = relationship.get("asset_type")
                    asset_key = relationship.get("asset_key")
                    asset_type_from_key = asset_key.rsplit("_", 1)[0] if asset_key and "_" in asset_key else None

                    if asset_type and asset_type not in built_in_asset_types:
                        self.custom_asset_types_used_by_rules.add(asset_type)
                    if asset_type_from_key and asset_type_from_key not in built_in_asset_types:
                        self.custom_asset_types_used_by_rules.add(asset_type_from_key)
        except Exception as e:
            logger.error(f"Error loading rules: {str(e)}")
            raise
        return rules
    
    def _group_apps_by_custom_asset_attribute(self, relationship, ungrouped_assets, assets_to_process):
        """Groups apps based on custom asset attribute values."""
        asset_type = relationship["asset_type"]
        asset_key = relationship["asset_key"]
        
        # Find custom assets and group apps by attribute value
        attribute_value_to_apps = self._build_custom_asset_attribute_mapping(
            ungrouped_assets, asset_type, asset_key
        )
        
        # Create efficient lookup for app-to-attribute-value mapping
        app_id_to_attr_value = self._build_app_attribute_lookup(attribute_value_to_apps)
        
        # Collect apps with matching attribute values
        return self._collect_apps_with_matching_attributes(
            assets_to_process, app_id_to_attr_value, attribute_value_to_apps
        )
    
    def _build_custom_asset_attribute_mapping(self, ungrouped_assets, asset_type, asset_key):
        """Builds mapping from attribute values to related apps."""
        attribute_value_to_apps = {}
        custom_assets = [asset for asset in ungrouped_assets.values() if asset.asset_type == asset_type]
        
        for custom_asset in custom_assets:
            if asset_key in custom_asset.attributes:
                attr_value = custom_asset.attributes[asset_key] if isinstance(custom_asset.attributes[asset_key], list) else [custom_asset.attributes[asset_key]]
                # Process each value in the list
                for value in attr_value:
                    if value not in attribute_value_to_apps:
                        attribute_value_to_apps[value] = set()
                    
                    for app_id in custom_asset.get_related_ids("app_ids"):
                        app_asset_id = f"app-{app_id}"
                        if app_asset_id in ungrouped_assets:
                            attribute_value_to_apps[value].add(ungrouped_assets[app_asset_id])
        
        return attribute_value_to_apps
    
    def _build_app_attribute_lookup(self, attribute_value_to_apps):
        """Creates efficient lookup from app ID to attribute value."""
        app_id_to_attr_value = {}
        for attr_value, apps in attribute_value_to_apps.items():
            for app in apps:
                app_id = app.asset_id.split("-")[1]
                app_id_to_attr_value[app_id] = attr_value
        return app_id_to_attr_value
    
    def _collect_apps_with_matching_attributes(self, assets_to_process, app_id_to_attr_value, attribute_value_to_apps):
        """Collects apps that share the same custom asset attribute values."""
        collected_assets = set()
        for asset in assets_to_process:
            if asset.asset_type == "app":
                app_id = asset.asset_id.split("-")[1]
                if app_id in app_id_to_attr_value:
                    attr_value = app_id_to_attr_value[app_id]
                    collected_assets.update(attribute_value_to_apps[attr_value])
        return collected_assets  
    
    def get_custom_asset_types_used_by_rules(self) -> list[str]:
        return list(self.custom_asset_types_used_by_rules)

    def find_related_assets_by_rule(self, ungrouped_assets: Dict[str, Asset], assets_to_process: Set[Asset], rule: Rule) -> Set[Asset]:
        """Finds all assets related by a rule through recursive relationship traversal."""
        all_assets = set(assets_to_process)
        relationships = rule.infer_relationships(self.schemas)
        
        while True:
            new_assets = self._find_assets_for_relationships(relationships, all_assets, ungrouped_assets)
            new_assets -= all_assets  # Remove already processed assets
            
            if not new_assets:
                break
                
            all_assets.update(new_assets)

        return all_assets
    
    def _find_assets_for_relationships(self, relationships, all_assets, ungrouped_assets):
        """Processes all relationships to find new related assets."""
        new_assets = set()
        
        for relationship in relationships:
            if relationship.get("is_custom_asset"):
                new_assets.update(self._process_custom_asset_relationship(relationship, ungrouped_assets, all_assets))
            else:
                new_assets.update(self._process_standard_relationship(relationship, all_assets, ungrouped_assets))
        
        return new_assets
    
    def _process_custom_asset_relationship(self, relationship, ungrouped_assets, all_assets):
        """Processes custom asset relationships."""
        if "asset_type" in relationship and "asset_key" in relationship:
            return self._group_apps_by_custom_asset_attribute(relationship, ungrouped_assets, all_assets)
        else:
            logger.warning(f"Skipping invalid relationship structure: {relationship}")
            return set()
    
    def _process_standard_relationship(self, relationship, all_assets, ungrouped_assets):
        """Processes standard asset relationships (cross-type and same-type)."""
        new_assets = set()
        
        if relationship.get("asset_type") != relationship.get("target_asset_type"):
            new_assets.update(self._process_cross_type_relationship(relationship, all_assets, ungrouped_assets))
        else:
            new_assets.update(self._process_same_type_relationship(relationship, all_assets, ungrouped_assets))
        
        return new_assets
    
    def _process_cross_type_relationship(self, relationship, all_assets, ungrouped_assets):
        """Processes cross-type relationships (e.g., app -> server)."""
        new_assets = set()
        target_asset_type = relationship["target_asset_type"]
        
        # Pre-compute lookup dictionary
        target_assets = {
            asset.asset_id.split("-")[1]: asset 
            for asset in ungrouped_assets.values() 
            if asset.asset_type == target_asset_type
        }
        
        for asset in all_assets:
            if asset.asset_type == relationship["asset_type"]:
                for id in asset.get_related_ids(relationship["asset_key"]):
                    if id in target_assets:
                        new_assets.add(target_assets[id])
        
        return new_assets
    
    def _process_same_type_relationship(self, relationship, all_assets, ungrouped_assets):
        """Processes same-type relationships (e.g., app -> app by attribute)."""
        new_assets = set()
        asset_type = relationship["asset_type"]
        asset_key = relationship["asset_key"]
        
        # Pre-compute lookup dictionary
        attr_value_to_assets = {}
        for asset in ungrouped_assets.values():
            if asset.asset_type == asset_type and asset_key in asset.attributes:
                value = asset.attributes[asset_key]
                if value not in attr_value_to_assets:
                    attr_value_to_assets[value] = set()
                attr_value_to_assets[value].add(asset)
        
        # Use the lookup structure
        for asset in all_assets:
            if asset.asset_type == asset_type and asset_key in asset.attributes:
                value = asset.attributes[asset_key]
                if value in attr_value_to_assets:
                    new_assets.update(attr_value_to_assets[value])
        
        return new_assets
    

    def create_move_groups_from_app(
        self,
        initial_app: Asset,
        ungrouped_assets: Dict[str, Asset],
        wpm_job_id: str,
        createdBy: str,
    ) -> Tuple[List[MoveGroup], Set[Asset]]:
        """
        Creates move groups by applying grouping rules to assets.
        
        This is the core grouping algorithm that:
        1. Starts with an initial app
        2. Applies GROUPING_INCLUSIVE rules to find related assets recursively
        3. Applies GROUPING_EXCLUSIVE rules to split groups if needed
        4. Creates MoveGroup objects for each final group
        
        Args:
            initial_app: The starting app asset for grouping
            ungrouped_assets: Dictionary of all available assets
            wpm_job_id: WPM job ID to associate with the move groups
            createdBy: User who created the move groups
            
        Returns:
            Tuple of (list of created MoveGroup objects, set of all grouped assets)
        """
        if wpm_job_id is None:
            raise ValueError("wpm_job_id cannot be None")

        group = {initial_app}

        # Build initial group with related assets
        group = self._build_inclusive_group(initial_app, ungrouped_assets)
        
        # Split group based on exclusive rules
        final_groups = self._apply_exclusive_rules(group)
        
        # Convert to MoveGroup objects
        move_groups = self._create_move_group_objects(
            final_groups, wpm_job_id, createdBy
        )
        
        all_grouped_assets = set().union(*final_groups)
        return move_groups, all_grouped_assets
    
    def _build_inclusive_group(self, initial_app: Asset, ungrouped_assets: Dict[str, Asset]) -> Set[Asset]:
        """Builds a group by applying inclusive rules recursively."""
        group = {initial_app}
        
        while True:
            new_assets = set()
            for rule in self.rules:
                if rule.rule_type == "GROUPING_INCLUSIVE":
                    collected_assets = self.find_related_assets_by_rule(ungrouped_assets, group, rule)
                    new_assets.update(collected_assets - group)

            if not new_assets:
                break

            group.update(new_assets)
        
        return group
    
    def _apply_exclusive_rules(self, group: Set[Asset]) -> List[Set[Asset]]:
        """Applies exclusive rules to split groups."""
        final_groups = [group]
        for rule in self.rules:
            if rule.rule_type == "GROUPING_EXCLUSIVE":
                final_groups = self.split_group_by_attribute(group, rule)
        return final_groups
    
    def _create_move_group_objects(
        self, 
        final_groups: List[Set[Asset]], 
        wpm_job_id: str, 
        createdBy: str
    ) -> List[MoveGroup]:
        """Converts asset groups to MoveGroup objects."""
        return [
            self._create_move_group(group, wpm_job_id, createdBy)
            for group in final_groups
        ]

    def _create_move_group(
        self, group_assets: Set[Asset], wpm_job_id: str, createdBy: str
    ) -> MoveGroup:
        if not wpm_job_id:
            raise ValueError("wpm_job_id cannot be None or empty")
        if not createdBy:
            raise ValueError("createdBy cannot be None or empty")

        asset_ids = self.collect_asset_ids(group_assets)
        total_storage = self.calculate_storage_metrics(group_assets)
        complexity = self.calculate_complexity_score(group_assets)

        metrics = {
            "server_count": len(asset_ids["server_ids"])
            if "server_ids" in asset_ids
            else 0,
            "total_server_storage": round(total_storage, 2),
            "complexity_score": complexity,
            "app_ids": list(asset_ids["app_ids"]) if "app_ids" in asset_ids else [],
            "server_ids": list(asset_ids["server_ids"])
            if "server_ids" in asset_ids
            else [],
            "database_ids": list(asset_ids["database_ids"])
            if "database_ids" in asset_ids
            else [],
        }

        return MoveGroup(
            move_group_id=str(ULID()),
            move_group_name=self.generate_unique_name(group_assets),
            wave_id=None,
            wpm_job_id=wpm_job_id,
            _history={
                'createdBy': createdBy,
                'createdTimestamp': datetime.now(timezone.utc).isoformat()
            },
            **metrics,
        )

    def calculate_storage_metrics(self, assets: Set[Asset]) -> float:
        total = 0
        for asset in assets:
            if asset.asset_type == "server" and asset.attributes.get("storage_size"):
                try:
                    # Convert storage_size to float to handle both numeric and string values
                    storage_size = float(asset.attributes.get("storage_size"))
                    total += storage_size
                except (ValueError, TypeError):
                    # Log warning for invalid storage size values
                    logger.warning(f"Invalid storage_size for server {asset.asset_id}: {asset.attributes.get('storage_size')}")
        return total

    def calculate_complexity_score(self, assets: Set[Asset]) -> float:
        return sum(asset.complexity_score or 0 for asset in assets)

    def generate_unique_name(self, group_assets: Set[Asset]) -> str:
        """Generate a unique name for the move group using timestamp with milliseconds and random string."""
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d-%H%M%S.%f")[:-3]
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        
        return f"Move Group {timestamp}-{random_string}"
    
    def _name_exists(self, name: str) -> bool:
        """Check if a move group name already exists using NameIndex GSI."""
        try:
            response = self.db_manager.tables["move_groups"].query(
                IndexName="NameIndex",
                KeyConditionExpression=Key("move_group_name").eq(name),
                Limit=1
            )
            return len(response.get("Items", [])) > 0
        except ClientError as e:
            logger.warning(f"Error checking name uniqueness: {str(e)}")
            return False

    def save_group(self, group: MoveGroup) -> bool:
        """
        Saves a move group to DynamoDB with error handling.

        Args:
            group: The MoveGroup object to save

        Returns:
            bool: True if save was successful, False otherwise
        """
        if not group or not group.move_group_id:
            logger.error("Cannot save group: Invalid group or missing move_group_id")
            return False

        try:
            item = self.create_move_group_item(group)
            logger.info(f"Saving move group {group.move_group_id} with data: {item}")

            self.db_manager.tables["move_groups"].put_item(
                Item=item, ConditionExpression="attribute_not_exists(move_group_id)"
            )

            logger.info(f"Successfully saved move group {group.move_group_id}")
            return True
        except self.db_manager.tables[
            "move_groups"
        ].meta.client.exceptions.ConditionalCheckFailedException:
            logger.error(f"Move group {group.move_group_id} already exists")
            return False
        except ClientError as e:
            logger.error(
                f"Error saving group {group.move_group_id} to DynamoDB: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error saving group {group.move_group_id}: {str(e)}"
            )
            return False

    def create_move_group_item(self, group: MoveGroup) -> Dict[str, Any]:
        return {
            "move_group_id": group.move_group_id,
            "move_group_name": group.move_group_name,
            "wave_id": group.wave_id or None,
            "wpm_job_id": group.wpm_job_id or None,
            "server_count": group.server_count,
            "total_server_storage": convert_floats_to_decimal(group.total_server_storage),
            "complexity_score": convert_floats_to_decimal(group.complexity_score),
            "app_ids": group.app_ids,
            "server_ids": group.server_ids,
            "database_ids": group.database_ids,
            "_history": group._history,
        }

    def collect_asset_ids(self, assets: Set[Asset]) -> Dict[str, Set[str]]:
        """
        Extracts asset IDs by type from a set of assets.
        
        Converts asset IDs from the format 'type-id' to just 'id' and groups them by type.
        
        Args:
            assets: Set of Asset objects
            
        Returns:
            Dictionary mapping asset type (e.g., 'app_ids') to set of IDs
        """
        metrics = {}

        for asset in assets:
            asset_type_ids = f"{asset.asset_type}_ids"
            if asset_type_ids not in metrics:
                metrics[asset_type_ids] = set()
            metrics[asset_type_ids].add(asset.asset_id.split("-")[1])

        return metrics

    def split_group_by_attribute(
        self, group: Set[Asset], rule: Rule
    ) -> List[Set[Asset]]:
        """
        Splits a group of assets based on a specific attribute value.

        Args:
            group: Set of assets to be split
            rule: Rule containing the split criteria

        Returns:
            List of asset sets, each containing assets with matching attribute values

        Raises:
            ValueError: If rule is invalid
            KeyError: If required attributes are missing
        """
        logger.info(f"Breaking group of size {len(group)} by rule {rule.rule_id}")

        # Validate rule before processing
        if not self._validate_rule(rule):
            logger.info("Rule validation failed, returning original group")
            return [group]

        # Group assets by attribute value
        attribute_groups = self._group_by_attribute(group, rule)

        # If no attributes found or only one attribute value, return original group
        if len(attribute_groups) <= 1:
            logger.info("No attribute diversity found, returning original group")
            return [group]

        # Get relationship data from rule
        relationship = rule.relationships[0]
        asset_key = relationship.get("asset_key")
        asset_type = relationship.get("asset_type")

        # Get all non-typed assets (e.g., apps)
        common_assets = self._get_common_assets(group, asset_type)

        # Create a mapping of common assets to their related typed assets
        common_asset_relations = self._map_asset_relations(
            common_assets, attribute_groups, asset_key
        )

        # Create final groups
        new_groups = self._create_final_groups(
            attribute_groups, common_asset_relations, common_assets, asset_key
        )

        logger.info(
            f"Created {len(new_groups)} groups with sizes: {[len(g) for g in new_groups]}"
        )
        return new_groups

    def _validate_rule(self, rule: Rule) -> bool:
        """
        Validates if a rule is applicable for group breaking.

        Args:
            rule: The rule to validate

        Returns:
            bool: True if rule is valid, False otherwise
        """
        return (
            rule.rule_type == "GROUPING_EXCLUSIVE"
            and rule.relationships
            and len(rule.relationships) > 0
        )

    def _group_by_attribute(
        self, group: Set[Asset], rule: Rule
    ) -> Dict[str, Set[Asset]]:
        """
        Groups assets by the attribute value specified in the rule.

        Args:
            group: Set of assets to group
            rule: Rule containing the grouping criteria

        Returns:
            Dictionary mapping attribute values to sets of assets
        """
        relationship = rule.relationships[0]
        asset_key = relationship.get("asset_key")
        asset_type = relationship.get("asset_type")

        # Create a dictionary to store groups by attribute value
        attribute_groups = {}

        # Find all assets of the specified type
        typed_assets = [asset for asset in group if asset.asset_type == asset_type]

        # Group assets by the attribute value
        for asset in typed_assets:
            if asset_key in asset.attributes:
                attr_value = asset.attributes[asset_key]
                if attr_value not in attribute_groups:
                    attribute_groups[attr_value] = set()
                attribute_groups[attr_value].add(asset)

        return attribute_groups

    def _get_common_assets(self, group: Set[Asset], asset_type: str) -> Set[Asset]:
        """
        Gets all assets that are not of the specified type.

        Args:
            group: Set of all assets
            asset_type: Type of assets to exclude

        Returns:
            Set of common assets
        """
        return set(asset for asset in group if asset.asset_type != asset_type)

    def _map_asset_relations(
        self,
        common_assets: Set[Asset],
        attribute_groups: Dict[str, Set[Asset]],
        asset_key: str,
    ) -> Dict[Asset, Set[Asset]]:
        """
        Maps common assets to their related typed assets.

        Args:
            common_assets: Set of common assets
            attribute_groups: Dictionary of attribute values to typed assets
            asset_key: The attribute key used for grouping

        Returns:
            Dictionary mapping common assets to their related typed assets
        """
        # Flatten all typed assets from attribute groups
        typed_assets = set()
        for assets in attribute_groups.values():
            typed_assets.update(assets)

        # Create a mapping of common assets to their related typed assets
        common_asset_relations = {}

        for common_asset in common_assets:
            # Find all typed assets related to this common asset
            related_typed_assets = set()

            # Check for relationships in both directions
            for typed_asset in typed_assets:
                # Check if common asset has a relationship to typed asset
                for rel_name, rel_ids in common_asset._relationships.items():
                    if typed_asset.asset_id.split("-")[1] in rel_ids:
                        related_typed_assets.add(typed_asset)

                # Check if typed asset has a relationship to common asset
                for rel_name, rel_ids in typed_asset._relationships.items():
                    if common_asset.asset_id.split("-")[1] in rel_ids:
                        related_typed_assets.add(typed_asset)

            common_asset_relations[common_asset] = related_typed_assets

        return common_asset_relations

    def _create_final_groups(
        self,
        attribute_groups: Dict[str, Set[Asset]],
        common_asset_relations: Dict[Asset, Set[Asset]],
        common_assets: Set[Asset],
        asset_key: str,
    ) -> List[Set[Asset]]:
        """
        Creates final groups based on attribute values and relationships.

        Args:
            attribute_groups: Dictionary mapping attribute values to typed assets
            common_asset_relations: Dictionary mapping common assets to related typed assets
            common_assets: Set of all common assets
            asset_key: The attribute key used for grouping

        Returns:
            List of final asset groups
        """
        new_groups = []

        # Create a group for each attribute value
        for attr_value, assets_with_attr in attribute_groups.items():
            # Start with just the typed assets for this attribute value
            new_group = set(assets_with_attr)

            # Add common assets that have related typed assets in this group
            self._add_related_common_assets(
                new_group, assets_with_attr, common_asset_relations, asset_key
            )

            new_groups.append(new_group)

        # Handle common assets that don't have any related typed assets
        self._handle_unrelated_common_assets(
            new_groups, common_assets, common_asset_relations
        )

        return new_groups

    def _add_related_common_assets(
        self,
        new_group: Set[Asset],
        assets_with_attr: Set[Asset],
        common_asset_relations: Dict[Asset, Set[Asset]],
        asset_key: str,
    ) -> None:
        """
        Adds common assets to a group based on their relationships.

        Args:
            new_group: The group being built
            assets_with_attr: Assets with the current attribute value
            common_asset_relations: Dictionary mapping common assets to related typed assets
            asset_key: The attribute key used for grouping
        """
        for common_asset, related_typed_assets in common_asset_relations.items():
            # If any related typed asset is in this group, consider including the common asset
            if any(
                typed_asset in assets_with_attr for typed_asset in related_typed_assets
            ):
                # Only include common assets that have their related assets split across groups
                # or if all their related assets are in this group
                related_attr_values = {
                    typed_asset.attributes.get(asset_key)
                    for typed_asset in related_typed_assets
                    if asset_key in typed_asset.attributes
                }

                # If the common asset has related typed assets with different attribute values
                # or if all its related typed assets are in this group, include it
                if len(related_attr_values) > 1 or all(
                    typed_asset in assets_with_attr
                    for typed_asset in related_typed_assets
                ):
                    new_group.add(common_asset)

    def _handle_unrelated_common_assets(
        self,
        new_groups: List[Set[Asset]],
        common_assets: Set[Asset],
        common_asset_relations: Dict[Asset, Set[Asset]],
    ) -> None:
        """
        Handles common assets that don't have any related typed assets.

        Args:
            new_groups: List of groups being built
            common_assets: Set of all common assets
            common_asset_relations: Dictionary mapping common assets to related typed assets
        """
        if new_groups:
            for common_asset in common_assets:
                if not common_asset_relations.get(common_asset):
                    new_groups[0].add(common_asset)


def validate_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the Lambda event and request body for creating move groups
    
    Args:
        event (dict): The Lambda event
        
    Returns:
        dict: Validation result with 'valid' boolean, 'error' message if invalid, and 'json_body' if valid for API requests
    """
    # Handle DynamoDB stream events
    if "Records" in event:
        return {"valid": True, "event_type": "stream"}
    
    # Handle direct API invocation with body
    if "body" in event:
        
        # Check if body exists and parse JSON
        try:
            json_body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            return {"valid": False, "error": "Invalid JSON format"}
        
        # Check required fields
        required_fields = ["app_ids", "wpm_job_id"]
        missing_fields = [field for field in required_fields if field not in json_body]
        if missing_fields:
            return {"valid": False, "error": "Missing required fields"}
        
        # Validate app_ids
        error = validate_id_list(json_body["app_ids"], "app_ids", MAX_APP_IDS_COUNT)
        if error:
            return {"valid": False, "error": error}
        
        # Validate wpm_job_id
        error = validate_id_string(json_body["wpm_job_id"], "wpm_job_id")
        if error:
            return {"valid": False, "error": error}
        
        return {"valid": True, "event_type": "api", "json_body": json_body}
    
    return {"valid": False, "error": "Invalid event structure"}


def _extract_request_data(record: Dict[str, Any]) -> Optional[Tuple[str, List[str], str, str]]:
    """
    Extracts request data from a DynamoDB stream record.
    
    Args:
        record: The DynamoDB stream record
        
    Returns:
        Tuple of (move_group_request_id, app_ids, wpm_job_id, createdBy) if valid, None otherwise
    """
    if "NewImage" not in record["dynamodb"] or record["eventName"] != "INSERT":
        return None
        
    dynamodb_image = record["dynamodb"]["NewImage"]
    move_group_request_id = dynamodb_image["move_group_request_id"]["S"]
    app_ids = [item["S"] for item in dynamodb_image["app_ids"]["L"]]
    wpm_job_id = dynamodb_image.get("wpm_job_id", {}).get("S")
    
    createdBy = "unknown"
    if "_history" in dynamodb_image and "M" in dynamodb_image["_history"]:
        history_map = dynamodb_image["_history"]["M"]
        if "createdBy" in history_map and "S" in history_map["createdBy"]:
            createdBy = history_map.get("createdBy", {}).get("S", "unknown")
    
    logger.info(
        f"Processing request {move_group_request_id} for apps: {app_ids}, wpm_job_id: {wpm_job_id}"
    )
    
    return move_group_request_id, app_ids, wpm_job_id, createdBy


# Add helper function definitions
def _load_asset_data(
    asset_manager: AssetManager, 
    app_ids: List[str]
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Loads app, server, database data from the database.
    
    Args:
        asset_manager: The asset manager to use for queries
        app_ids: List of app IDs to query
        
    Returns:
        Tuple of (all_apps, all_servers, all_databases)
    """
    # Query specific apps
    logger.info(f"Querying apps data for app_ids: {app_ids}")
    apps = asset_manager.query_apps(app_ids)
    logger.info(f"Found {len(apps)} apps")
    
    # Scan all apps, servers, and databases
    logger.info("Scanning all apps data")
    all_apps = asset_manager.scan("apps")
    logger.info(f"Found {len(all_apps)} all apps")

    logger.info("Scanning all servers data")
    all_servers = asset_manager.scan("servers")
    logger.info(f"Found {len(all_servers)} all servers")
    
    logger.info("Scanning all databases data")
    all_databases = asset_manager.scan("databases")
    logger.info(f"Found {len(all_databases)} all databases")
    
    return all_apps, all_servers, all_databases
    
def _enrich_apps_with_servers(all_apps: List[Dict], all_servers: List[Dict]) -> None:
    """Enriches apps with server relationships."""
    for app in all_apps:
        if "server_ids" not in app:
            app["server_ids"] = []
            app_id = app.get("app_id", "")
            for server in all_servers:
                if ("app_ids" in server and app_id in server.get("app_ids", [])):
                    app["server_ids"].append(server.get("server_id", ""))
            logger.debug(f"Found {len(app['server_ids'])} servers for app {app_id}")

def _enrich_apps_with_databases(all_apps: List[Dict], all_databases: List[Dict]) -> None:
    """Enriches apps with database relationships."""
    for app in all_apps:
        if "database_ids" not in app:
            app["database_ids"] = []
            app_id = app.get("app_id", "")
            for database in all_databases:
                if ("app_ids" in database and app_id in database.get("app_ids", [])):
                    app["database_ids"].append(database.get("database_id", ""))
            logger.debug(f"Found {len(app['database_ids'])} databases for app {app_id}")

def _enrich_servers_with_apps(all_servers: List[Dict], all_apps: List[Dict]) -> None:
    """Enriches servers with app relationships."""
    for server in all_servers:
        if "app_ids" not in server:
            server["app_ids"] = []
            server_id = server.get("server_id", "")
            for app in all_apps:
                if "server_ids" in app and server_id in app.get("server_ids", []):
                    server["app_ids"].append(app.get("app_id", ""))
            logger.debug(f"Found {len(server['app_ids'])} apps for server {server_id}")

def _enrich_databases_with_apps(all_databases: List[Dict], all_apps: List[Dict]) -> None:
    """Enriches databases with app relationships."""
    for database in all_databases:
        if "app_ids" not in database:
            database["app_ids"] = []
            database_id = database.get("database_id", "")
            for app in all_apps:
                if "database_ids" in app and database_id in app.get("database_ids", []):
                    database["app_ids"].append(app.get("app_id", ""))
            logger.debug(f"Found {len(database['app_ids'])} apps for database {database_id}")

def _enrich_relationships(all_apps: List[Dict], all_servers: List[Dict], all_databases: List[Dict], custom_assets: List[Asset]) -> None:
    """
    Enriches app, server, and database data with relationship information.
    
    Args:
        all_apps: List of all apps
        all_servers: List of all servers
        all_databases: List of all databases
        custom_assets: List of custom assets
    """
    _enrich_apps_with_servers(all_apps, all_servers)
    _enrich_apps_with_databases(all_apps, all_databases)
    _enrich_servers_with_apps(all_servers, all_apps)
    _enrich_databases_with_apps(all_databases, all_apps)


def _validate_move_group_conflicts(move_group: 'MoveGroup', assets: Dict[str, Asset]) -> Optional[str]:
    """Check if any servers/databases in the move group already have move group assignments."""
    # Check servers
    for server_id in move_group.server_ids:
        server_asset_id = f"server-{server_id}"
        if server_asset_id in assets:
            server_asset = assets[server_asset_id]
            if server_asset.attributes.get("move_group_id"):
                return f"Server {server_id} already assigned to move group {server_asset.attributes['move_group_id']}"
    
    # Check databases  
    for database_id in move_group.database_ids:
        database_asset_id = f"database-{database_id}"
        if database_asset_id in assets:
            database_asset = assets[database_asset_id]
            if database_asset.attributes.get("move_group_id"):
                return f"Database {database_id} already assigned to move group {database_asset.attributes['move_group_id']}"
    
    return None

# Define helper function for processing move groups
def _process_move_groups(
    move_group_manager: MoveGroupManager,
    db_manager: DynamoDBManager,
    assets: Dict[str, Asset],
    app_ids: List[str],
    move_group_request_id: str,
    wpm_job_id: str,
    createdBy: str,
) -> Tuple[List[str], str]:
    """
    Processes move groups based on initial assets.
    
    Args:
        move_group_manager: The move group manager
        db_manager: The database manager
        assets: Dictionary of all assets
        app_ids: List of app IDs to process
        move_group_request_id: The move group request ID
        wpm_job_id: WPM job ID
        
    Returns:
        Tuple of (created_group_ids, final_status)
    """

    
    # Prepare initial assets
    initial_assets = {
        app_id: assets[f"app-{app_id}"]
        for app_id in app_ids
        if f"app-{app_id}" in assets
    }
    logger.info(f"Initial assets to process: {len(initial_assets)}")

    created_group_ids: List[str] = []
    ungrouped_assets = assets.copy()

    # Process each app
    while initial_assets:
        app_id = next(iter(initial_assets))
        app = initial_assets[app_id]
        logger.info(f"Processing app {app_id} for grouping")
        logger.info(f"Found {len(ungrouped_assets)} ungrouped assets")

        # Create groups for this app
        try:
            move_groups, grouped_assets = move_group_manager.create_move_groups_from_app(
                app, ungrouped_assets, wpm_job_id, createdBy
            )
        except Exception as e:
            logger.error(f"Error creating move group for app {app_id}: {str(e)}")
            raise
        
        # Validate each move group for conflicts before saving
        for group in move_groups:
            conflict = _validate_move_group_conflicts(group, assets)
            if conflict:
                logger.error(f"Move group creation blocked: {conflict}")
                raise ValueError(f"Cannot create move group: {conflict}")

        # Process each move group
        for group in move_groups:
            logger.info(
                f"Created group with {len(group.app_ids)} apps and {len(group.server_ids)} servers"
            )

            group.wpm_job_id = wpm_job_id

            try:
                if move_group_manager.save_group(group):
                    created_group_ids.append(group.move_group_id)
                    logger.info(
                        f"Successfully created move group {group.move_group_id}"
                    )

                    if move_group_request_id:
                        # Update move group request with the new group ID
                        logger.info(
                            f"Updating request {move_group_request_id} with new group ID {group.move_group_id}"
                        )
                        db_manager.update_move_group_request(
                            move_group_request_id,
                            {
                                "move_group_ids": created_group_ids,
                            },
                        )
                    
                    # Update WPM job with the new move group ID if a WPM job ID is provided
                    if wpm_job_id:
                        logger.info(
                            f"Updating WPM job {wpm_job_id} with move group ID {group.move_group_id}"
                        )
                        db_manager.update_wpm_job(wpm_job_id, group.move_group_id)
                    
                    # Update apps, servers, and databases with move group ID and WPM job ID
                    logger.info(
                        f"Updating assets with move group ID {group.move_group_id} and WPM job ID {wpm_job_id}"
                    )
                    db_manager.update_assets_with_move_group(group)

                if len(group.app_ids) == 0:
                    logger.warning(f"Group {group.move_group_id} contains no apps")
            except Exception as e:
                logger.error(f"Error processing move group {group.move_group_id}: {str(e)}")
                raise

        # Remove grouped assets from ungrouped assets
        for grouped_asset in grouped_assets:
            ungrouped_assets.pop(grouped_asset.asset_id, None)

        # Remove processed apps from initial assets
        for group in move_groups:
            for app_id in group.app_ids:
                if app_id in initial_assets:
                    initial_assets.pop(app_id, None)

        logger.info(f"Remaining apps to process: {len(initial_assets)}")

    # Determine final status
    final_status = "COMPLETED" if created_group_ids else "FAILED"
    return created_group_ids, final_status

def _update_move_group_request(
    db_manager: DynamoDBManager,
    move_group_request_id: str,
    final_status: str,
    created_group_ids: List[str]
) -> Dict[str, any]:
    # Update request with final status
    logger.info(
        f"Updating request {move_group_request_id} final status to {final_status} "
        f"with {len(created_group_ids)} groups created"
    )
    db_manager.update_move_group_request(
        move_group_request_id,
        {"status": final_status, "move_group_ids": created_group_ids},
    )
    
    return {
        "move_group_request_id": move_group_request_id,
        "status": final_status,
        "move_group_ids": created_group_ids,
    }

def create_move_groups(
    asset_manager: AssetManager,
    move_group_manager: MoveGroupManager,
    db_manager: DynamoDBManager,
    app_ids: list[str],
    wpm_job_id: str,
    created_by: str,
):
    """
    Main function to create move groups from a list of app IDs.
    
    This function orchestrates the entire move group creation process:
    1. Loads all asset data from DynamoDB
    2. Enriches relationships between assets
    3. Converts raw data to Asset objects
    4. Processes move groups using grouping rules
    5. Saves results to DynamoDB
    
    Args:
        asset_manager: Manages asset data loading and conversion
        move_group_manager: Manages move group creation logic
        db_manager: Manages DynamoDB operations
        app_ids: List of application IDs to create move groups for
        wpm_job_id: WPM job ID to associate with move groups
        created_by: User who created the move groups
        
    Returns:
        Tuple of (list of created move group IDs, final status)
    """

    # Load all assets
    all_apps, all_servers, all_databases = _load_asset_data(asset_manager, app_ids)
    custom_assets = get_custom_assets(move_group_manager.get_custom_asset_types_used_by_rules())
    _enrich_relationships(all_apps, all_servers, all_databases, custom_assets)
    
    # Convert raw data to assets
    assets = asset_manager.convert_to_assets(
        {"apps": all_apps, "servers": all_servers, "databases": all_databases}
    )
    
    # Add custom assets to the assets dictionary
    for custom_asset in custom_assets:
        assets[custom_asset.asset_id] = custom_asset
    
    # Process move groups
    return _process_move_groups(
        move_group_manager,
        db_manager,
        assets,
        app_ids,
        None,
        wpm_job_id,
        created_by,
    )

def lambda_handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function that processes move group creation requests.

    Args:
        event: The Lambda event containing DynamoDB stream records or direct API request
        _: The Lambda context object (unused)

    Returns:
        Dict: Response with status code and processing results

    Raises:
        Exception: If there's an unhandled error during processing
    """
    try:
        event_body = event.get("body", {})
        logger.info(f"Received event with body: {json.dumps(event_body)}")

        # Validate input
        validation_result = validate_event(event)
        if not validation_result["valid"]:
            return {
                "headers": {**default_http_headers},
                "statusCode": 400,
                "body": json.dumps({"error": validation_result["error"]}),
            }

        db_manager = DynamoDBManager()
        asset_manager = AssetManager(db_manager)
        move_group_manager = MoveGroupManager(db_manager)
        
        # Handle direct API invocation
        if validation_result["event_type"] == "api":
            body = validation_result["json_body"]
            app_ids = body["app_ids"]
            wpm_job_id = body["wpm_job_id"]

            auth = MFAuth()
            auth_response = auth.get_user_resource_creation_policy(event, 'move_group')

            if auth_response['action'] != 'allow':
                return {
                    'headers': {**default_http_headers},
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized', 'message': 'You do not have permission to create move groups'})
                }

            created_by = auth_response.get('user', 'unknown')
            
            created_group_ids, final_status = create_move_groups(
                asset_manager,
                move_group_manager,
                db_manager,
                app_ids,
                wpm_job_id,
                created_by,
            )
            
            # Return response for direct API request
            send_anonymous_usage_data('AutoCreateGroupComplete_Direct')
            return {
                "headers": {**default_http_headers},
                "statusCode": 200,
                "body": json.dumps({
                    "status": final_status,
                    "move_group_ids": created_group_ids,
                })
            }

        # Process each record
        for record in event["Records"]:
            # Extract request data
            request_data = _extract_request_data(record)
            if not request_data:
                continue
                
            move_group_request_id, app_ids, wpm_job_id, created_by = request_data

            # Update request status to PROCESSING
            logger.info(f"Updating request {move_group_request_id} status to PROCESSING")
            db_manager.update_move_group_request(
                move_group_request_id, {"status": "PROCESSING"}
            )

            created_group_ids, final_status = create_move_groups(
                asset_manager,
                move_group_manager,
                db_manager,
                app_ids,
                wpm_job_id,
                created_by,
            )
            
            updated_move_group_request = _update_move_group_request(db_manager, move_group_request_id, final_status, created_group_ids)
            send_anonymous_usage_data('AutoCreateGroupComplete_Async')

            return {
                "statusCode": 200,
                "body": json.dumps(updated_move_group_request),
            }

        # If no records were processed
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No valid records to process"})
        }

    except Exception as e:
        error_message = f"Unhandled exception in lambda_handler: {str(e)}"
        logger.error(error_message, exc_info=True)
        
        # Try to update the request status, but handle potential failures
        try:
            if 'move_group_request_id' in locals():
                logger.info(f"Updating request {move_group_request_id} status to FAILED")
                db_manager.update_move_group_request(
                    move_group_request_id, {"status": "FAILED"}
                )
        except Exception as update_error:
            logger.error(f"Failed to update request status: {str(update_error)}", exc_info=True)
            
        return {"statusCode": 500, "body": json.dumps({"error": error_message})}