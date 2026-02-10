#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import time

from boto3.dynamodb.types import TypeDeserializer
import cmf_boto

logger = logging.getLogger()
logger.setLevel(logging.INFO)

deserializer = TypeDeserializer()

application = os.environ['application']
environment = os.environ['environment']
apps_table_name = '{}-{}-apps'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)
dynamodb = cmf_boto.resource('dynamodb')
waves_table = dynamodb.Table(waves_table_name)

def deserialize_dynamodb_item(raw_item):
    return {k: deserializer.deserialize(v) for k, v in raw_item.items()}

def scan_wave_table():
    response = waves_table.scan(ConsistentRead=True)
    scan_data = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = waves_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response.get('Items', []))
    return scan_data

def batch_get_apps(app_ids):
    if not app_ids:
        return []

    apps = []
    # Process in chunks of 100 (DynamoDB limit)
    for i in range(0, len(app_ids), 100):
        chunk = app_ids[i:i+100]
        keys = [{'app_id': app_id} for app_id in chunk]
        request_items = {apps_table_name: {'Keys': keys}}

        # Implement retry with backoff
        max_retries = 3
        base_delay = 0.1  # 100ms
        for attempt in range(max_retries + 1):
            response = dynamodb.batch_get_item(RequestItems=request_items)
            apps.extend(response.get('Responses', {}).get(apps_table_name, []))

            # Check for unprocessed keys
            unprocessed = response.get('UnprocessedKeys', {})
            if not unprocessed:
                break

            # Retry remaining items with backoff
            if attempt < max_retries:
                request_items = unprocessed
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying {len(unprocessed.get(apps_table_name, {}).get('Keys', []))} unprocessed keys, attempt {attempt+1}/{max_retries}")
                time.sleep(delay)
            else:
                logger.warning(f"Max retries reached. Ignoring unprocessed app_ids: {unprocessed}")
    return apps

def get_waves_by_ids(wave_ids, waves):
    return [wave for wave in waves if wave.get('wave_id') in wave_ids]

def calculate_mgh_status(waves):
    if not waves:
        return None
    
    statuses = [wave.get('wave_status') for wave in waves if wave.get('wave_status')]

    # Based on CMF status enum: Not started, Planning, In progress, Completed, Blocked
    if any(status == 'In progress' for status in statuses):
        return 'IN_PROGRESS'
    elif all(status == 'Completed' for status in statuses):
        return 'COMPLETED'
    elif all(status == 'Not started' for status in statuses):
        return 'NOT_STARTED'
    
    return None


def log_wave_status_change(dynamodb_stream_record, all_waves):
    # Deserialize DynamoDB item
    updated_wave = deserialize_dynamodb_item(dynamodb_stream_record.get('NewImage', {}))
    old_wave = deserialize_dynamodb_item(dynamodb_stream_record.get('OldImage', {}))
    
    if not updated_wave or 'wave_status' not in updated_wave:
        logger.info("No NewImage or wave_status found, skipping logging")
        return
    
    wave_id = updated_wave['wave_id']
    wave_app_ids = updated_wave.get("app_ids")
    old_status = old_wave.get('wave_status')
    new_status = updated_wave.get("wave_status")

    if new_status == old_status:
        logger.info(f"Wave {wave_id} status unchanged ({new_status})")
        return
    
    if not wave_app_ids:
        logger.info(f"Wave {wave_id} has no app_ids")
        return

    logger.info(f"Wave {wave_id} status changed from {old_status} to {new_status}")
    
    # Batch get apps associated with this wave
    wave_apps = batch_get_apps(wave_app_ids)
    
    for app in wave_apps:
        # Get all waves the app associates with
        app_wave_ids = app.get('wave_ids', [])
        app_name = app.get("app_name", "")
        logger.info(f"App {app_name} with wave_ids {app_wave_ids}")
        app_waves = get_waves_by_ids(app_wave_ids, all_waves)
        # Calculate status based on statuses of app's waves (for logging only)
        app_status = calculate_mgh_status(app_waves)
        logger.info(f"App {app_name} calculated status: {app_status} (MGH tracking disabled)")


def lambda_handler(event, _):
    try:
        logger.info("MGH and ADS integration has been deprecated and removed from CMF")
        logger.info("Wave status changes will be logged but not tracked in MGH")

        # Load all waves for logging purposes
        all_waves = scan_wave_table()
        logger.info(f"Found {len(all_waves)} waves")

        for record in event['Records']:
            log_wave_status_change(record['dynamodb'], all_waves)
    except Exception as e:
        logger.error(f"Error processing records: {str(e)}")
        raise
