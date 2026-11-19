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


# Cognito group that grants administrative access to the Admin API resources.
ADMIN_COGNITO_GROUP = 'admin'


def _extract_cognito_groups(event):
    """
    Extract the caller's Cognito group names from an API Gateway proxy event,
    supporting both authorizer styles used by this solution:

    - CUSTOM (Lambda REQUEST) authorizer: groups are propagated in the
      authorizer context under 'cognito:groups' as a comma-separated string
      (e.g. 'admin,readonly').
    - COGNITO_USER_POOLS authorizer: groups are available in the token claims
      under authorizer['claims']['cognito:groups']. API Gateway renders this
      multi-valued claim as a bracketed, space-separated string
      (e.g. '[admin readonly]'), not a comma-separated one.

    Returns:
        list[str]: The group names, or an empty list if none could be found.
    """
    authorizer = (event.get('requestContext', {}) or {}).get('authorizer', {}) or {}

    # Custom authorizer context (string values only).
    groups = authorizer.get('cognito:groups')

    # Fall back to Cognito user pool authorizer claims.
    if groups is None:
        claims = authorizer.get('claims', {}) or {}
        groups = claims.get('cognito:groups')

    if groups is None:
        return []

    if isinstance(groups, str):
        # Normalize both formats seen in practice: the custom authorizer's
        # comma-separated string, and the Cognito user-pool claim's
        # bracketed, space-separated string.
        normalized = groups.strip().lstrip('[').rstrip(']')
        tokens = normalized.replace(',', ' ').split()
        return [g for g in (t.strip() for t in tokens) if g]

    if isinstance(groups, list):
        return [str(g).strip() for g in groups if str(g).strip()]

    return []


def is_admin_request(event):
    """
    Independently verify that the caller of an Admin API request is a member of
    the administrative Cognito group.

    This is a defense-in-depth check performed inside the Lambda itself, in
    addition to the API Gateway authorizer, so that a realistic authorizer
    misconfiguration (for example wiring an admin route to a plain Cognito
    user-pool authorizer, or weakening the custom authorizer's group check)
    cannot silently expose admin-only functionality: in those cases the caller's
    group membership is still present in the request and is re-checked here.

    A request that arrived through API Gateway but carries no authorizer
    context fails closed. That is precisely the shape of the misconfiguration
    this check exists to contain - a route wired with AuthorizationType: NONE,
    or an authorizer that attaches no context - so allowing it would defeat the
    purpose of the check.

    Direct Lambda-to-Lambda invocations are still permitted, because trusted
    internal callers must not be blocked. These are distinguished by the
    absence of requestContext entirely: API Gateway always populates
    requestContext on a proxy event, whereas an internal caller passes only the
    fields it needs. httpMethod is deliberately NOT used to make this
    distinction, because internal callers synthesise it - lambda_ssm_scripts
    invokes lambda_schema with {'httpMethod': 'PUT', ...} and no
    requestContext, and must keep working.

    Args:
        event: API Gateway proxy event, or an internally synthesised event.

    Returns:
        bool: True if the caller is an admin or is a trusted internal caller;
              False if the request reached API Gateway without authorizer
              context, or has context that lacks admin group membership.
    """
    request_context = event.get('requestContext') or {}
    if not request_context:
        # No requestContext at all: direct Lambda-to-Lambda or other non-HTTP
        # invocation that never traversed API Gateway.
        return True

    if not request_context.get('authorizer'):
        # Came through API Gateway but no authorizer context was attached.
        return False

    return ADMIN_COGNITO_GROUP in _extract_cognito_groups(event)


def create_admin_forbidden_response():
    """
    Standardized HTTP 403 response for Admin API requests made by a caller that
    is not a member of the administrative Cognito group.

    Returns:
        dict: API Gateway proxy response with a 403 status code.
    """
    return {
        'headers': {**default_http_headers},
        'statusCode': 403,
        'body': json.dumps({
            'errors': ['User is not authorized to perform this administrative action.']
        })
    }
