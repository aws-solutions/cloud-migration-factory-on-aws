#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from botocore.exceptions import ClientError
import logging
import sys
import time

import cmf_boto

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CMF_PROGRESS_UPDATE_STREAM_NAME = "CloudMigrationFactory"

def does_server_exist_in_ads(server_name, home_region):
    ads_client = cmf_boto.client('discovery', region_name=home_region)
    logger.info(f"Checking if server {server_name} exists in ADS")

    try:
        ads_client.describe_configurations(configurationIds=[server_name])
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidParameterValueException":
            logger.info(f"Server {server_name} does not exists in ADS")
            return False
    return True


def update_mgh_tracking(server_name, migration_status, home_region):
    logger.info(f"Updating MGH tracking information for server {server_name}")
    mgh_client = cmf_boto.client('mgh', region_name=home_region)
    mgh_client.create_progress_update_stream(ProgressUpdateStreamName=CMF_PROGRESS_UPDATE_STREAM_NAME)
    # Using the verbatim migration status as the task. This can be variable depending on the job being performed.
    # An example migration status is "Agent Install - Success". This does not directly correlate to the typical usage of a MGH MigrationTask.
    # For now, we have made the decision to share this status as a completed migration task. We will not send multiple updates for the same task.
    # We will evaluate in the future if we need to adjust this definition.
    mgh_client.import_migration_task(ProgressUpdateStream=CMF_PROGRESS_UPDATE_STREAM_NAME, MigrationTaskName=migration_status)
    mgh_client.associate_discovered_resource(
        ProgressUpdateStream=CMF_PROGRESS_UPDATE_STREAM_NAME,
        MigrationTaskName=migration_status,
        DiscoveredResource={'ConfigurationId': server_name})

    task_status = "FAILED" if 'failed' in migration_status.lower() else "COMPLETED"
    mgh_client.notify_migration_task_state(
        ProgressUpdateStream=CMF_PROGRESS_UPDATE_STREAM_NAME,
        MigrationTaskName=migration_status,
        NextUpdateSeconds=sys.maxsize,
        UpdateDateTime=int(time.time()),
        Task={'Status': task_status})


def lambda_handler(event, _):
    # Any MGH region can be used as an endpoint to obtain the home region. Utilizing PDX as a static endpoint to simplify logic.
    mh_config_client = cmf_boto.client('migrationhub-config', region_name='us-west-2')
    home_region = mh_config_client.get_home_region().get('HomeRegion')
    if home_region is None:
        logger.info("No home region set, not updating status")
        return

    for record in event ['Records']:
        dynamodb_record = record['dynamodb']

        if 'NewImage' in dynamodb_record:
            logger.info("New image found")

            new_image = dynamodb_record['NewImage']
            if 'migration_status' in new_image:
                server_name = new_image['server_name']['S']
                migration_status = new_image['migration_status']['S']

                # Currently not sending information back to MGH for servers that don't exist in ADS
                if does_server_exist_in_ads(server_name, home_region):
                    update_mgh_tracking(server_name, migration_status, home_region)