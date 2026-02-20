#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from cmf_logger import logger

PREFIX_INVOCATION = 'Invocation:'
MAX_SHARD = 10

def fetch_shard_items(data_table, schema_name, shard):
    """Query a single shard with pagination and return all items from that shard"""
    partition_key = f"{schema_name}#{shard}"
    items = []
    last_evaluated_key = None

    while True:
        query_params = {
            "KeyConditionExpression": "#pk = :pk",
            "ExpressionAttributeNames": {"#pk": "asset_type#shard"},
            "ExpressionAttributeValues": {":pk": partition_key}
        }
        if last_evaluated_key:
            query_params["ExclusiveStartKey"] = last_evaluated_key

        response = data_table.query(**query_params)

        if 'Items' in response:
            items.extend(response['Items'])

        if 'LastEvaluatedKey' not in response:
            break

        last_evaluated_key = response['LastEvaluatedKey']
        logger.debug(f'{PREFIX_INVOCATION} Paginating shard {shard}, retrieved {len(response["Items"])} items')

    return items


def query_custom_assets(data_table: Any, schema_name: str) -> List[dict]:
    """Query all shards of a custom asset type in parallel and return combined results"""
    items = []
    
    # Use ThreadPoolExecutor to query shards in parallel
    with ThreadPoolExecutor(max_workers=MAX_SHARD) as executor:
        # Submit all shard queries to the executor with shard index
        future_to_shard = {}
        for shard in range(MAX_SHARD):
            future = executor.submit(fetch_shard_items, data_table, schema_name, shard)
            future_to_shard[future] = shard
        
        # Process results as they complete
        for future in as_completed(future_to_shard):
            shard = future_to_shard[future]
            try:
                shard_items = future.result()
                items.extend(shard_items)
                logger.debug(f'{PREFIX_INVOCATION} Completed shard {shard}, retrieved {len(shard_items)} items')
            except Exception as exc:
                logger.error(f'{PREFIX_INVOCATION} Shard {shard} generated an exception: {exc}')
    
    return items


def adapt_item_to_schema(item: dict, schema_name: str, schema_type: str) -> dict:
    """Convert a single item from DB format to API format"""
    if schema_type != 'custom':
        return item
    
    # Create a new dict for the converted item
    converted_item = {}
    
    # Copy all fields except the ones we need to rename
    for key, value in item.items():
        if key != 'asset_type#shard' and key != 'asset_id' and key != 'asset_name':
            converted_item[key] = value
    
    # Convert asset_id to schema_name_id
    if 'asset_id' in item:
        converted_item[f"{schema_name}_id"] = item['asset_id']
    
    # Convert asset_name to schema_name_name
    if 'asset_name' in item:
        converted_item[f"{schema_name}_name"] = item['asset_name']
    
    return converted_item


def revert_item_from_schema(item: dict, schema_name: str, schema_type: str) -> dict:
    """Convert a single item from API format to DB format"""
    if schema_type != 'custom':
        return item

    # Create a new dict for the converted item
    converted_item = {}
    
    # Convert schema_name_id back to asset_id
    schema_id_key = f"{schema_name}_id"
    if schema_id_key in item:
        converted_item['asset_id'] = item[schema_id_key]
        # Create the partition key asset_type#shard based on schema_name_id
        converted_item['asset_type#shard'] = f"{schema_name}#{get_shard_number(item[schema_id_key])}" 
    
    # Convert schema_name_name back to asset_name
    schema_name_key = f"{schema_name}_name"
    if schema_name_key in item:
        converted_item['asset_name'] = item[schema_name_key]
    
    # Copy all other fields except the ones we've already handled
    for key, value in item.items():
        if key != schema_id_key and key != schema_name_key:
            converted_item[key] = value
    
    return converted_item

def get_shard_number(item_id: str) -> int:
    """
    Hash an item ID to a stable shard number between 0 and MAX_SHARD - 1.
    
    Args:
        item_id: The item ID to hash
        
    Returns:
        int: A shard number between 0 and MAX_SHARD - 1
    """
    # Use MD5 hash for consistent distribution
    hash_object = hashlib.md5(item_id.encode())
    # Take the first 4 bytes of the hash and convert to an integer
    hash_int = int(hash_object.hexdigest()[:8], 16)
    # Modulo MAX_SHARD to get a number between 0 and MAX_SHARD - 1
    return hash_int % MAX_SHARD