from datetime import datetime, timezone
import simplejson as json
import logging
import os
import re
from typing import List, Dict, Any
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass

from policy import MFAuth
from cmf_utils import update_job_array_field, default_http_headers, convert_floats_to_decimal, send_anonymous_usage_data
from item_validation import validate_id_string, validate_id_list

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Validate environment variables at module load
def validate_environment():
    required_vars = ["WPM_JOBS_TABLE_NAME", "MOVE_GROUPS_TABLE_NAME", "WAVES_TABLE_NAME", 
                     "APPS_TABLE_NAME", "SERVERS_TABLE_NAME", "DATABASES_TABLE_NAME"]
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


# Call at module load
validate_environment()

# DynamoDB table names from environment variables
jobs_table_name = os.environ["WPM_JOBS_TABLE_NAME"]
move_groups_table_name = os.environ["MOVE_GROUPS_TABLE_NAME"]
waves_table_name = os.environ["WAVES_TABLE_NAME"]
apps_table_name = os.environ["APPS_TABLE_NAME"]
servers_table_name = os.environ["SERVERS_TABLE_NAME"]
databases_table_name = os.environ["DATABASES_TABLE_NAME"]

WARNING_EXCEEDS_CAPACITY = "WARNING: Move group {group_id} exceeds wave capacity limits but was assigned as the smallest available group"
MAX_MOVE_GROUPS_COUNT = 100

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
jobs_table = dynamodb.Table(jobs_table_name)
move_groups_table = dynamodb.Table(move_groups_table_name)
waves_table = dynamodb.Table(waves_table_name)


@dataclass
class MoveGroup:
    group_id: str
    server_count: int
    total_server_storage: float
    complexity_score: float
    app_ids: List[str]
    server_ids: List[str]
    database_ids: List[str]


def update_job_wave_ids(wpm_job_id: str, wave_id: str) -> bool:
    """
    Updates a WPM job by adding a wave_id to its wave_ids array.
    
    Args:
        wpm_job_id: The ID of the WPM job to update
        wave_id: The wave ID to add to the WPM job
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    
    # Use the shared utility function to update the wave_ids field
    return update_job_array_field(
        table=jobs_table,
        wpm_job_id=wpm_job_id,
        item_id=wave_id,
        field_name="wave_ids"
    )


def store_wave(wave: dict) -> None:
    """
    Stores a wave in the DynamoDB waves table

    Args:
        wave (dict): Wave data to store
    """
    try:
        wave["total_server_storage"] = convert_floats_to_decimal(wave["total_server_storage"])
        wave["complexity_score"] = convert_floats_to_decimal(wave["complexity_score"])

        waves_table.put_item(
            Item=wave, ConditionExpression="attribute_not_exists(wave_id)"
        )
        logger.info(f"Stored wave {wave['wave_id']} in DynamoDB")
        
        # Update the WPM job with the new wave ID
        if "wpm_job_id" in wave and wave["wpm_job_id"]:
            update_job_wave_ids(wave["wpm_job_id"], wave["wave_id"])
            
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.error(f"Wave {wave['wave_id']} already exists")
            raise ValueError(f"Wave {wave['wave_id']} already exists")
        logger.error(f"Error storing wave in DynamoDB: {str(e)}")
        raise


def update_assets_with_wave_id(wave_id: str, app_ids: List[str], server_ids: List[str], database_ids: List[str]) -> bool:
    """
    Updates apps, servers, and databases with wave ID.
    
    Args:
        wave_id: The wave ID to assign
        app_ids: List of app IDs to update
        server_ids: List of server IDs to update
        database_ids: List of database IDs to update
        
    Returns:
        bool: True if all updates were successful, False otherwise
    """
    if not wave_id:
        logger.warning("Cannot update assets: Missing wave_id")
        return False
    
    # Update each asset type with consistent error handling
    app_success = _update_apps_with_wave_id(wave_id, app_ids)
    server_success = _update_servers_with_wave_id(wave_id, server_ids)
    database_success = _update_databases_with_wave_id(wave_id, database_ids)
    
    return app_success and server_success and database_success


def _update_apps_with_wave_id(wave_id: str, app_ids: List[str]) -> bool:
    """
    Updates apps with wave ID using SET operation for wave_ids list.
    
    Args:
        wave_id: The wave ID to assign
        app_ids: List of app IDs to update
        
    Returns:
        bool: True if all updates were successful
    """
    if not app_ids:
        return True
        
    apps_table = dynamodb.Table(os.environ["APPS_TABLE_NAME"])
    success = True
    
    for app_id in app_ids:
        try:
            apps_table.update_item(
                Key={"app_id": app_id},
                UpdateExpression="SET wave_ids = list_append(if_not_exists(wave_ids, :empty_list), :wave_id_list)",
                ExpressionAttributeValues={
                    ":wave_id_list": [wave_id],
                    ":empty_list": []
                }
            )
            logger.info(f"Updated app {app_id} with wave_id {wave_id} appended")
        except ClientError as e:
            logger.error(f"Error updating app {app_id}: {str(e)}")
            success = False
    
    return success


def _update_servers_with_wave_id(wave_id: str, server_ids: List[str]) -> bool:
    """
    Updates servers with wave ID.
    
    Args:
        wave_id: The wave ID to assign
        server_ids: List of server IDs to update
        
    Returns:
        bool: True if all updates were successful
    """
    if not server_ids:
        return True
        
    servers_table = dynamodb.Table(os.environ["SERVERS_TABLE_NAME"])
    success = True
    
    for server_id in server_ids:
        try:
            servers_table.update_item(
                Key={"server_id": server_id},
                UpdateExpression="SET wave_id = :wave_id",
                ExpressionAttributeValues={":wave_id": wave_id}
            )
            logger.info(f"Updated server {server_id} with wave_id {wave_id}")
        except ClientError as e:
            logger.error(f"Error updating server {server_id}: {str(e)}")
            success = False
    
    return success


def _update_databases_with_wave_id(wave_id: str, database_ids: List[str]) -> bool:
    """
    Updates databases with wave ID.
    
    Args:
        wave_id: The wave ID to assign
        database_ids: List of database IDs to update
        
    Returns:
        bool: True if all updates were successful
    """
    if not database_ids:
        return True
        
    databases_table = dynamodb.Table(os.environ["DATABASES_TABLE_NAME"])
    success = True
    
    for database_id in database_ids:
        try:
            databases_table.update_item(
                Key={"database_id": database_id},
                UpdateExpression="SET wave_id = :wave_id",
                ExpressionAttributeValues={":wave_id": wave_id}
            )
            logger.info(f"Updated database {database_id} with wave_id {wave_id}")
        except ClientError as e:
            logger.error(f"Error updating database {database_id}: {str(e)}")
            success = False
    
    return success

def update_move_groups_wave_assignment(wave_id: str, move_group_ids: List[str]) -> None:
    """
    Updates move groups with their wave assignment using update_item to preserve existing attributes

    Args:
        wave_id (str): The wave ID to assign
        move_group_ids (List[str]): List of move group IDs to update
    """
    try:
        for group_id in move_group_ids:
            move_groups_table.update_item(
                Key={"move_group_id": group_id},
                UpdateExpression="SET wave_id = :wave_id",
                ExpressionAttributeValues={
                    ":wave_id": wave_id,
                },
            )
        logger.info(f"Updated wave assignment for {len(move_group_ids)} move groups")
    except ClientError as e:
        logger.error(f"Error updating move groups wave assignment: {str(e)}")
        raise


def get_job_config(wpm_job_id: str) -> dict:
    """
    Gets job configuration from DynamoDB including wave capacity settings

    Args:
        wpm_job_id (str): The job ID

    Returns:
        dict: Job configuration containing wave capacity settings including:
              - wave_server_capacity: Maximum server capacity per wave
              - wave_storage_capacity: Maximum storage capacity per wave
              - starting_wave_server_capacity: Initial server capacity for the first wave
              - wave_server_capacity_increase: Increment of server capacity for each subsequent wave
    """
    try:
        response = jobs_table.get_item(Key={"wpm_job_id": wpm_job_id})
        if "Item" not in response:
            raise ValueError(f"Job {wpm_job_id} not found")

        return response["Item"]
    except ClientError as e:
        logger.error(f"Error getting job config: {str(e)}")
        raise


def safe_float_convert(value, default=0.0):
    """
    Safely converts a value to float, returning a default if conversion fails

    Args:
        value: Value to convert to float
        default (float): Default value to return if conversion fails

    Returns:
        float: Converted value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_move_groups(move_group_ids: list[str], wpm_job_id: str) -> list[MoveGroup]:
    """
    Gets move group details from DynamoDB for the provided IDs

    Args:
        move_group_ids (list[str]): List of move group IDs

    Returns:
        list[MoveGroup]: List of move group details with their properties
    """
    move_groups = []

    try:
        # Use batch_get_item for efficient retrieval
        # DynamoDB limits batch get to 100 items, so we chunk if needed
        for i in range(0, len(move_group_ids), 100):
            chunk = move_group_ids[i : i + 100]
            response = dynamodb.batch_get_item(
                RequestItems={
                    move_groups_table_name: {
                        "Keys": [{"move_group_id": group_id} for group_id in chunk]
                    }
                }
            )

            for item in response["Responses"][move_groups_table_name]:
                if item.get('wpm_job_id') != wpm_job_id:
                    continue

                move_groups.append(
                    MoveGroup(
                        group_id=item["move_group_id"],
                        server_count=item.get("server_count", 0),
                        total_server_storage=safe_float_convert(item.get("total_server_storage", 0)),
                        complexity_score=safe_float_convert(
                            item.get("complexity_score", 0)
                        ),
                        app_ids=item.get("app_ids", []),
                        server_ids=item.get("server_ids", []),
                        database_ids=item.get("database_ids", []),
                    )
                )

        return move_groups
    except ClientError as e:
        logger.error(f"Error getting move groups: {str(e)}")
        raise


def sort_groups(move_groups: list[MoveGroup]) -> list[MoveGroup]:
    """
    Sorts move groups by server count and complexity score

    Args:
        move_groups (list[MoveGroup]): List of move groups to sort

    Returns:
        list[MoveGroup]: Sorted list of move groups
    """
    return sorted(
        move_groups,
        key=lambda x: (
            x.server_count,
            x.complexity_score,
        ),
        reverse=False,
    )


def create_new_wave(wpm_job_id: str, wave_number: int, createdBy: str) -> dict:
    """
    Creates a new wave dictionary with default values

    Args:
        wpm_job_id (str): The job ID
        wave_number (int): The wave number

    Returns:
        dict: New wave dictionary with default values
    """
    wave = {
        "wave_id": str(wave_number),
        "wave_name": f"Wave {wave_number}",
        "wave_description": f"Wave {wave_number} for job {wpm_job_id}",
        "wave_status": "Not started",
        "server_count": 0,
        "total_server_storage": 0.0,
        "complexity_score": 0,
        "wpm_job_id": wpm_job_id,
        "move_group_ids": [],
        "app_ids": [],
        "server_ids": [],
        "database_ids": [],
        "_history": {
            "createdBy": createdBy,
            "createdTimestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    return wave


def add_group_to_wave(wave: dict, group: MoveGroup) -> None:
    """
    Adds a move group to a wave, updating all relevant fields

    Args:
        wave (dict): Wave to update
        group (MoveGroup): Move group to add to the wave
    """
    wave["server_count"] += group.server_count
    wave["total_server_storage"] += group.total_server_storage
    wave["complexity_score"] += group.complexity_score
    wave["move_group_ids"].append(group.group_id)
    wave["app_ids"].extend(group.app_ids)
    wave["server_ids"].extend(group.server_ids)
    wave["database_ids"].extend(group.database_ids)


def get_wave_server_capacity(
    relative_wave_number,
    starting_wave_server_capacity,
    max_wave_server_capacity,
    wave_server_capacity_increase,
):
    if (
        starting_wave_server_capacity >= max_wave_server_capacity
        or wave_server_capacity_increase <= 0
    ):
        return max_wave_server_capacity

    capacity = (
        starting_wave_server_capacity
        + (relative_wave_number - 1) * wave_server_capacity_increase
    )
    return min(capacity, max_wave_server_capacity)


def finalize_current_wave_and_create_new(
    current_wave,
    waves,
    wpm_job_id,
    current_wave_number,
    starting_wave_server_capacity,
    max_wave_server_capacity,
    wave_server_capacity_increase,
    wave_id_offset,
    createdBy,
):
    """Finalize the current wave and create a new one with updated capacity.

    Args:
        current_wave (dict): The current wave to finalize
        waves (list): List of waves to append the current wave to
        wpm_job_id (str): The job ID
        current_wave_number (int): The current wave number
        starting_wave_server_capacity (int): Initial server capacity for the first wave
        max_wave_server_capacity (int): Maximum server capacity per wave
        wave_server_capacity_increase (int): Increment of server capacity for each wave
        wave_id_offset (int): The offset between database wave IDs and the relative wave numbers used for capacity calculations

    Returns:
        tuple: (new_wave, new_wave_number, new_wave_server_capacity)
    """
    # Store current wave with error handling
    try:
        store_wave(current_wave)
        update_move_groups_wave_assignment(
            current_wave["wave_id"], current_wave["move_group_ids"]
        )
        # Update apps, servers, and databases with wave ID
        update_assets_with_wave_id(
            current_wave["wave_id"], 
            current_wave["app_ids"], 
            current_wave["server_ids"], 
            current_wave["database_ids"]
        )
        waves.append(current_wave)
    except Exception as e:
        logger.error(f"Error finalizing wave {current_wave['wave_id']}: {str(e)}")
        raise

    # Create new wave with updated capacity
    new_wave_number = current_wave_number + 1
    new_wave = create_new_wave(wpm_job_id, new_wave_number, createdBy)
    new_wave_server_capacity = get_wave_server_capacity(
        new_wave_number - wave_id_offset,
        starting_wave_server_capacity,
        max_wave_server_capacity,
        wave_server_capacity_increase,
    )

    return new_wave, new_wave_number, new_wave_server_capacity


def get_next_wave_id() -> int:
    try:
        logger.info("Fetching next wave ID from waves table")
        items = []
        last_evaluated_key = None
        
        # Use pagination to handle large tables
        while True:
            if last_evaluated_key:
                response = waves_table.scan(ExclusiveStartKey=last_evaluated_key)
            else:
                response = waves_table.scan()
                
            items.extend(response['Items'])
            
            # Check if we need to paginate
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

        # Filter out wave_ids that are not digits
        numeric_ids = []
        for item in items:
            wave_id = item.get("wave_id", "")
            if wave_id.isdigit():
                numeric_ids.append(int(wave_id))
            else:
                logger.warning(f"Skipping non-numeric wave_id: {wave_id}")

        next_id = max(numeric_ids, default=0) + 1
        logger.info(f"Next wave ID will be: {next_id}")
        return next_id
    except ClientError as e:
        logger.error(f"Error getting next wave ID: {str(e)}")
        raise


def create_waves(wpm_job_id: str, move_group_ids: list[str], createdBy: str) -> list[dict]:
    """
    Creates waves based on move groups and stores them in DynamoDB

    Args:
        wpm_job_id (str): The job ID
        move_group_ids (list[str]): List of move group IDs to organize into waves

    Returns:
        list[dict]: List of created waves with their properties
    """
    # Ensure move_group_ids are unique
    unique_move_group_ids = list(dict.fromkeys(move_group_ids))  # preserves order
    if len(unique_move_group_ids) != len(move_group_ids):
        logger.warning(
            f"Duplicate move group IDs found and removed. Original: {len(move_group_ids)}, Unique: {len(unique_move_group_ids)}"
        )
        move_group_ids = unique_move_group_ids

    job_config = get_job_config(wpm_job_id)
    max_wave_server_capacity = job_config["wave_server_capacity"]
    wave_storage_capacity = job_config["wave_storage_capacity"]

    # Get the new wave capacity ramping parameters if they exist
    starting_wave_server_capacity = job_config.get(
        "starting_wave_server_capacity", max_wave_server_capacity
    ) or max_wave_server_capacity
    wave_server_capacity_increase = job_config.get("wave_server_capacity_increase", 0) or 0

    move_groups = get_move_groups(move_group_ids, wpm_job_id)
    sorted_groups = sort_groups(move_groups)

    waves = []
    current_wave_number = get_next_wave_id()
    current_wave = create_new_wave(wpm_job_id, current_wave_number, createdBy)

    # Store the offset between absolute wave IDs in the database and relative wave numbers for this job
    # For example, if the next available wave ID is 5, we store 4 as the offset so the first wave in this job is treated as wave #1 for capacity calculations
    wave_id_offset = current_wave_number - 1

    current_wave_server_capacity = get_wave_server_capacity(
        1,
        starting_wave_server_capacity,
        max_wave_server_capacity,
        wave_server_capacity_increase,
    )

    for group in sorted_groups:
        # Check if adding this group would exceed the current wave's capacity
        capacity_exceeded = (
            current_wave["server_count"] + group.server_count
            > current_wave_server_capacity
            or current_wave["total_server_storage"] + group.total_server_storage
            > wave_storage_capacity
        )

        if capacity_exceeded:
            # If no groups have been assigned to this wave yet, but the smallest group still exceeds capacity,
            # we need to add it anyway with a warning
            if not current_wave["move_group_ids"]:
                add_group_to_wave(current_wave, group)

                # Add warning message to the wave
                current_wave["warnings"] = [WARNING_EXCEEDS_CAPACITY]

                # Store current wave and create a new one
                current_wave, current_wave_number, current_wave_server_capacity = (
                    finalize_current_wave_and_create_new(
                        current_wave,
                        waves,
                        wpm_job_id,
                        current_wave_number,
                        starting_wave_server_capacity,
                        max_wave_server_capacity,
                        wave_server_capacity_increase,
                        wave_id_offset,
                        createdBy,
                    )
                )
            else:
                # Store current wave and create a new one with updated capacity
                current_wave, current_wave_number, current_wave_server_capacity = (
                    finalize_current_wave_and_create_new(
                        current_wave,
                        waves,
                        wpm_job_id,
                        current_wave_number,
                        starting_wave_server_capacity,
                        max_wave_server_capacity,
                        wave_server_capacity_increase,
                        wave_id_offset,
                        createdBy,
                    )
                )

                # Now try to add the group to the new wave
                if (
                    group.server_count > current_wave_server_capacity
                    or group.total_server_storage > wave_storage_capacity
                ):
                    # If it still exceeds capacity, add it with a warning
                    add_group_to_wave(current_wave, group)

                    # Add warning message to the wave
                    current_wave["warnings"] = [WARNING_EXCEEDS_CAPACITY]

                    # Store current wave and create a new one
                    current_wave, current_wave_number, current_wave_server_capacity = (
                        finalize_current_wave_and_create_new(
                            current_wave,
                            waves,
                            wpm_job_id,
                            current_wave_number,
                            starting_wave_server_capacity,
                            max_wave_server_capacity,
                            wave_server_capacity_increase,
                            wave_id_offset,
                            createdBy,
                        )
                    )
                else:
                    # Add the group to the new wave
                    add_group_to_wave(current_wave, group)
        else:
            # Add the group to the current wave
            add_group_to_wave(current_wave, group)

    # Store final wave if it contains any groups
    if current_wave["move_group_ids"]:
        try:
            store_wave(current_wave)
            update_move_groups_wave_assignment(
                current_wave["wave_id"], current_wave["move_group_ids"]
            )
            # Update apps, servers, and databases with wave ID
            update_assets_with_wave_id(
                current_wave["wave_id"], 
                current_wave["app_ids"], 
                current_wave["server_ids"], 
                current_wave["database_ids"]
            )
            waves.append(current_wave)
        except Exception as e:
            logger.error(f"Error finalizing final wave {current_wave['wave_id']}: {str(e)}")
            raise

    return waves


def validate_request_body(event: dict) -> dict:
    """
    Validates the request body for creating waves
    
    Args:
        event (dict): The Lambda event
        
    Returns:
        dict: Validation result with 'valid' boolean, 'error' message if invalid, and 'json_body' if valid
    """
    
    # Check if body exists
    if "body" not in event:
        return {"valid": False, "error": "Missing request body"}
    
    # Parse JSON body
    try:
        json_body = json.loads(event["body"])
    except json.JSONDecodeError:
        return {"valid": False, "error": "Invalid JSON format"}
    
    # Check required fields
    required_fields = ["wpm_job_id", "move_group_ids"]
    missing_fields = [field for field in required_fields if field not in json_body]
    if missing_fields:
        return {"valid": False, "error": "Missing required fields"}
    
    # Validate wpm_job_id
    error = validate_id_string(json_body["wpm_job_id"], "wpm_job_id")
    if error:
        return {"valid": False, "error": error}
    
    # Validate move_group_ids
    error = validate_id_list(json_body["move_group_ids"], "move_group_ids", MAX_MOVE_GROUPS_COUNT)
    if error:
        return {"valid": False, "error": error}
    
    return {"valid": True, "json_body": json_body}


def lambda_handler(event, _):
    """
    Lambda function handler for creating waves

    Args:
        event: Lambda event
        _: Lambda context (unused)

    Returns:
        dict: API Gateway response
    """

    auth = MFAuth()
    auth_response = auth.get_user_resource_creation_policy(event, 'wave')

    if auth_response['action'] != 'allow':
        return {
            'headers': {**default_http_headers},
            'statusCode': 401,
            'body': json.dumps({'error': 'Unauthorized', 'message': 'You do not have permission to create waves'})
        }

    createdBy = auth_response.get('user', 'unknown')

    try:
        # Validate request body
        validation_result = validate_request_body(event)
        if not validation_result["valid"]:
            return {
                "headers": {**default_http_headers},
                "statusCode": 400,
                "body": json.dumps({"error": validation_result["error"]}),
            }
        
        json_body = validation_result["json_body"]

        # Validate job exists
        try:
            response = jobs_table.get_item(Key={"wpm_job_id": json_body["wpm_job_id"]})
            if "Item" not in response:
                return {
                    "headers": {**default_http_headers},
                    "statusCode": 404,
                    "body": json.dumps({"error": "Job not found"}),
                }
        except ClientError as e:
            logger.error(f"Error validating job: {str(e)}", exc_info=True)
            return {
                "headers": {**default_http_headers},
                "statusCode": 500,
                "body": json.dumps({"error": "Error validating job"}),
            }

        waves = create_waves(json_body["wpm_job_id"], json_body["move_group_ids"], createdBy)
        send_anonymous_usage_data('AutoCreateWaveComplete')
        return {"headers": {**default_http_headers}, "statusCode": 200, "body": json.dumps(waves, use_decimal=True)}
    except ClientError as e:
        logger.error("AWS service error", exc_info=True)
        return {
            "headers": {**default_http_headers},
            "statusCode": 500,
            "body": json.dumps({"error": "Internal service error"}),
        }
    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        return {
            "headers": {**default_http_headers},
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
