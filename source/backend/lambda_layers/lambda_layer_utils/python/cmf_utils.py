#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timezone
from decimal import Decimal
import os
import requests
import json
import botocore
from cmf_types import NotificationType
from cmf_logger import logger
import boto3
from botocore.exceptions import ClientError

# System-wide data format for logging and notifications.
CONST_DT_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
CONST_DT_FORMAT_V3 = '%Y-%m-%dT%H:%M:%S.%f'

REQUESTS_DEFAULT_TIMEOUT = 60

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

# anonymous_usage_data settings.
anonymous_usage_data = os.environ.get('AnonymousUsageData', 'Yes')
s_uuid = os.environ.get('solutionUUID', '')
region = os.environ.get('region','unknown')
if region == 'unknown':
    region = os.environ.get('REGION', 'unknown')
anonymous_usage_data_url = 'https://metrics.awssolutionsbuilder.com/generic'
solution_id = os.getenv('SOLUTION_ID', 'SO0097')

def send_anonymous_usage_data(status):
    if anonymous_usage_data == "Yes":
        usage_data = {"Solution": solution_id,
                      "UUID": s_uuid,
                      "Status": status,
                      "TimeStamp": str(datetime.now()),
                      "Region": region
                      }
        requests.post(anonymous_usage_data_url,
                      data=json.dumps(usage_data),
                      headers={'content-type': 'application/json'},
                      timeout=REQUESTS_DEFAULT_TIMEOUT)


def get_date_from_string(str_date):
    try:
        created_timestamp = datetime.strptime(str_date, CONST_DT_FORMAT)
    except Exception as _:
        # try old pre v4 format for backward compatibility.
        created_timestamp = datetime.strptime(str_date, CONST_DT_FORMAT_V3)

    created_timestamp = created_timestamp.replace(tzinfo=timezone.utc)

    return created_timestamp

def update_job_array_field(table, wpm_job_id: str, item_id: str, field_name: str) -> bool:
    """
    Updates a WPM job by adding an item ID to a specified array field.
    
    Args:
        table: The DynamoDB table object for jobs
        wpm_job_id (str): The ID of the WPM job to update
        item_id (str): The ID to add to the array field
        field_name (str): The name of the array field to update (e.g., 'move_group_ids', 'wave_ids')
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if not wpm_job_id or not item_id:
        logger.warning(f"Cannot update WPM job: Missing wpm_job_id or {field_name} item_id")
        return False
        
    try:
        # First, get the current WPM job to check if the field exists
        response = table.get_item(
            Key={"wpm_job_id": wpm_job_id},
            ConsistentRead=True
        )
        
        if "Item" not in response:
            logger.warning(f"WPM job {wpm_job_id} not found")
            return False
            
        wpm_job = response["Item"]
        current_ids = wpm_job.get(field_name, []) or []
        
        # Check if the item_id is already in the list
        if item_id in current_ids:
            logger.info(f"Item {item_id} already exists in WPM job {wpm_job_id} {field_name}")
            return True
            
        # Add the new item_id to the list
        current_ids.append(item_id)
        
        # Update the WPM job
        table.update_item(
            Key={"wpm_job_id": wpm_job_id},
            UpdateExpression=f"SET {field_name} = :{field_name}",
            ExpressionAttributeValues={
                f":{field_name}": current_ids
            }
        )
        
        logger.info(f"Successfully updated WPM job {wpm_job_id} with {field_name} item {item_id}")
        return True
        
    except ClientError as e:
        logger.error(f"Error updating WPM job {wpm_job_id}: {str(e)}")
        return False


def convert_floats_to_decimal(obj, precision=2):
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.
    
    Args:
        obj: Object to convert (dict, list, or primitive)
        precision (int): Number of decimal places to round to (default: 2)
        
    Returns:
        Object with floats converted to Decimal and rounded
    """
    if isinstance(obj, float):
        # Convert float to string first to avoid precision issues, then round
        return round(Decimal(str(obj)), precision)
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v, precision) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item, precision) for item in obj]
    return obj

def publish_event(notification: NotificationType, events_client: boto3.client, event_source: str, event_bus_name: str) -> None:
    """
    Publishes job status notification to EventBridge.
    
    Args:
        notification: Notification object to be published
        events_client: EventBridge client
        event_source: source of event
        event_bus_name: name of the eventbus
        
    Returns:
        None
        
    Raises:
        ClientError: If EventBridge publish fails
    """
    try:
        logger.info(f"Publishing {str(notification)} to {event_bus_name}")

        event_entry = {
            'Source': event_source,  #f'{application}-{environment}-task-orchestrator',
            'DetailType': notification['type'],
            'Detail': json.dumps(notification),
            'EventBusName': event_bus_name,
            'Time': datetime.now(timezone.utc)
        }

        # Write notification to event bus
        response = events_client.put_events(
            Entries=[event_entry]
        )

        if response.get('FailedEntryCount')> 0:
            logger.error(
                f"Failed to publish event to EventBridge: "
                f"ErrorCode={response['Entries'][0]['ErrorCode']}, "
                f"ErrorMessage={response['Entries'][0].get('ErrorMessage', 'No message')}, "
                f"EventId={response['Entries'][0].get('EventId', 'No ID')}"
            )

    except botocore.exceptions.ClientError as e:
        logger.error(f"EventBridge error occurred while publishing event: {str(e)}")
