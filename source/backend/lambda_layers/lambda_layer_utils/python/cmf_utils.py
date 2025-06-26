#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timezone
import os
import requests
import json
import botocore

from cmf_types import NotificationType
from cmf_logger import logger
import boto3

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