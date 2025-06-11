#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os

import cmf_boto

logger = logging.getLogger()
logger.setLevel(logging.INFO)

application = os.environ['application']
environment = os.environ['environment']
apps_table_name = '{}-{}-apps'.format(application, environment)
apps_table = cmf_boto.resource('dynamodb').Table(apps_table_name)

def scan_app_table():
    response = apps_table.scan(ConsistentRead=True)
    scan_data = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response.get('Items', []))
    return scan_data


def get_ads_app_id(app_name, home_region):
    ads_client = cmf_boto.client('discovery', region_name=home_region)
    paginator = ads_client.get_paginator('list_configurations')

    application_filter={'name': 'application.name', 'condition': 'EQUALS', 'values': [app_name]}
    page_iterator = paginator.paginate(configurationType="APPLICATION", filters=[application_filter])
    logger.info(f"Paginating through ADS applications associated with application {app_name}")

    for page in page_iterator:
        for app in page['configurations']:
            if app['application.name'] == app_name:
                return app['application.configurationId']

    return None


def update_mgh_app_status(app_name, mgh_status, home_region):
    mgh_client = cmf_boto.client('mgh', region_name=home_region)
    app_id = get_ads_app_id(app_name, home_region)
    if app_id is not None:
        logger.info(f"Updating MGH status to {mgh_status} for app ID {app_id}")
        mgh_client.notify_application_state(ApplicationId=app_id, Status=mgh_status)


def update_mgh_application_status(home_region, dynamodb_record):
    cmf_to_mgh_status = {
        "Not started": "NOT_STARTED",
        "In progress": "IN_PROGRESS",
        "Completed": "COMPLETED"
    }

    if 'NewImage' in dynamodb_record:
        logger.info("New image found")

        new_image = dynamodb_record['NewImage']
        if 'wave_status' in new_image:
            # This is based on the current default CMF status enum - Not started,Planning,In progress,Completed,Blocked
            wave_status = new_image['wave_status']['S']
            if not cmf_to_mgh_status.get(wave_status, None):
                logger.info(f"No MGH status update required for wave status: {wave_status}")
                return

            wave_id = new_image['wave_id']['S']
            apps = scan_app_table()

            logger.info("Found %d apps" % len(apps))
            for app in apps:
                if 'wave_id' in app and app['wave_id'] == wave_id:
                    update_mgh_app_status(app['app_name'], cmf_to_mgh_status.get(wave_status, wave_status), home_region)


def lambda_handler(event, _):
    # Any MGH region can be used as an endpoint to obtain the home region. Utilizing PDX as a static endpoint to simplify logic.
    mh_config_client = cmf_boto.client('migrationhub-config', region_name='us-west-2')
    home_region = mh_config_client.get_home_region().get('HomeRegion')
    if home_region is None:
        logger.info("No home region set, not updating status")
        return

    for record in event ['Records']:
        update_mgh_application_status(home_region, record['dynamodb'])
