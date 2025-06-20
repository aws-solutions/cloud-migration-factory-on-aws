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
    return NotificationType(
        type = event.get('detail-type', ''),
        uuid = detail.get('uuid', ''),
        dismissible = detail.get('dismissible', True),
        header = detail.get('header', 'Job Update'),
        content = detail.get('content', ''),
        timeStamp = detail.get('timeStamp', datetime.now(timezone.utc).isoformat(sep='T'))
    )  

def lambda_handler(event: NotificationEvent, _):
    # Validate event
    validate_event(event)

    # Create notification object
    notification: NotificationType = create_notification(event)

    if gatewayapi:  # If socket is set then send notifications to users.
        # Implement pagination for scan operation
        scan_kwargs = {}
        done = False
        start_key = None

        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key

            try:
                resp = connectionIds_table.scan(**scan_kwargs)
            except botocore.exceptions.ClientError as err:
                logger.error(
                    f"Could not scan for connections due to: "
                    f"{err.response['Error']['Code']}: "
                    f"{err.response['Error']['Message']}"
                )
                break
            except Exception as e:
                logger.error(f"Unexpected error during scan: {str(e)}")
                break

            # Process items from scan
            for item in resp["Items"]:
                try:
                    # Send to all connections
                    gatewayapi.post_to_connection(ConnectionId=item["connectionId"], Data=json.dumps(notification))
                except botocore.exceptions.ClientError as err:
                    logger.error(
                        f"Error posting to wss connection: "
                        f"{err.response['Error']['Code']}: "
                        f"{err.response['Error']['Message']}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error posting to wss connection {item['connectionId']}: {str(e)}")

            # Check if there are more items to process
            start_key = resp.get("LastEvaluatedKey", None)
            done = start_key is None