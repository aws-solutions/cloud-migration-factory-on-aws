import cmf_boto
from boto3.dynamodb.conditions import Key, Attr
import botocore
from datetime import datetime, timezone
from cmf_logger import logger
from cmf_constants import SECURE_SOCKET_PROTOCOL
from cmf_types import NotificationType, NotificationEvent
import os
import json
from typing import Dict, Any

environment = os.environ["environment"]
application = os.environ["application"]
dynamodb = cmf_boto.resource("dynamodb")
connectionIds_table_name = f'{application}-{environment}-ssm-connectionIds'
connectionIds_table = dynamodb.Table(connectionIds_table_name)
socket_url = os.environ["socket_url"]
# map types in notifications to flashbar notification types.
task_types = {
    "TaskFailed": "error",
    "TaskSuccess": "success",
    "TaskPending": "pending",
    "TaskTimedOut": "error",
    "TaskManualApprovalNeeded": "success"
}

if SECURE_SOCKET_PROTOCOL not in socket_url:
    gatewayapi = None
else:
    gatewayapi = cmf_boto.client("apigatewaymanagementapi", endpoint_url=socket_url)

def validate_event(event: Dict[str, Any]) -> None:
    """
    Validate required properties in the event.

    Args:
        event (Dict[str, Any]): The event to validate.

    Returns: None

    Raises:
        ValueError: If the event is invalid.
    """
    if event is None:
        raise ValueError("Event cannot be None")

    if 'detail' not in event or not isinstance(event['detail'], dict):
        raise ValueError("Missing or invalid 'detail' in event")

    detail = event['detail']

    required_fields = {
        'uuid': str,
        'dismissible': bool,
        'header': str,
        'content': str,
        'timeStamp': str
    }

    for field, expected_type in required_fields.items():
        if field not in detail:
            raise ValueError(f"Missing required field: {field}")

        if not isinstance(detail[field], expected_type):
            raise ValueError(f"'{field}' must be a {expected_type.__name__}")

def create_notification(event: NotificationEvent):
    """Create a notification object from validated event"""
    detail = event['detail']
    task_type = task_types.get(event.get('detail-type', ''),event.get('detail-type', ''))

    return NotificationType(
        type = task_type,
        uuid = detail.get('uuid', ''),
        dismissible = detail.get('dismissible', True),
        header = detail.get('header', 'Job Update'),
        content = detail.get('content', ''),
        timeStamp = detail.get('timeStamp', datetime.now(timezone.utc).isoformat(sep='T'))
    )

def scan_connections_table(scan_kwargs):
    """
    Scan the connections table and handle errors.
    
    Args:
        scan_kwargs: Scan parameters for DynamoDB
        
    Returns:
        tuple: (response, success) where success is True if scan succeeded
    """
    try:
        resp = connectionIds_table.scan(**scan_kwargs)
        return resp, True
    except botocore.exceptions.ClientError as err:
        logger.error(
            f"Could not scan for connections due to: "
            f"{err.response['Error']['Code']}: "
            f"{err.response['Error']['Message']}"
        )
        return None, False
    except Exception as e:
        logger.error(f"Unexpected error during scan: {str(e)}")
        return None, False

def send_notification_to_connection(connection_id, notification_data):
    """
    Send notification to a single connection and handle errors.
    
    Args:
        connection_id: The WebSocket connection ID
        notification_data: JSON string of notification data
    """
    try:
        gatewayapi.post_to_connection(ConnectionId=connection_id, Data=notification_data)
    except botocore.exceptions.ClientError as err:
        logger.error(
            f"Error posting to wss connection: "
            f"{err.response['Error']['Code']}: "
            f"{err.response['Error']['Message']}"
        )
    except Exception as e:
        logger.error(f"Unexpected error posting to wss connection {connection_id}: {str(e)}")

def process_connections_batch(items, notification_data):
    """
    Process a batch of connections and send notifications.
    
    Args:
        items: List of connection items from DynamoDB scan
        notification_data: JSON string of notification data
    """
    for item in items:
        send_notification_to_connection(item["connectionId"], notification_data)

def lambda_handler(event: NotificationEvent, _):
    # Validate event
    validate_event(event)

    # Create notification object
    notification: NotificationType = create_notification(event)

    if gatewayapi:  # If socket is set then send notifications to users.
        notification_data = json.dumps(notification)
        # Implement pagination for scan operation
        scan_kwargs = {}
        done = False
        start_key = None

        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key

            resp, success = scan_connections_table(scan_kwargs)
            if not success:
                break

            # Process items from scan
            process_connections_batch(resp["Items"], notification_data)

            # Check if there are more items to process
            start_key = resp.get("LastEvaluatedKey", None)
            done = start_key is None