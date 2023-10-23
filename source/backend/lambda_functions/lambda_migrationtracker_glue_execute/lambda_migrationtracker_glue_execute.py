#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import boto3
import logging
import os
import datetime
import time
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

application = os.environ['application']
environment = os.environ['environment']
glue_app_crawler_name = '{}-{}-app-crawler'.format(application, environment)
glue_server_crawler_name = '{}-{}-server-crawler'.format(application, environment)
glue_app_job_name = '{}-{}-app-extract'.format(application, environment)
glue_server_job_name = '{}-{}-server-extract'.format(application, environment)


def lambda_handler(event, context):
    """Process a CloudFormation custom resource request.

    Returns: HTTP PUT request to s3-presigned URL
    """
    log.info('Function Starting')
    log.info(f'Incoming Event:\n{json.dumps(event, indent=2)}')
    response_data = ''
    try:
        if (event['RequestType'] == 'Create') or (event['RequestType'] == 'Update'):
            response_data = run_glue_crawler_job()
            response_reason = 'Running the glue crawler and job'
            response_status = 'SUCCESS'

        elif event['RequestType'] == 'Delete':
            response_status = 'SUCCESS'
            response_reason = 'No cleanup is required for this function'
            response_data = None

        else:
            log.info('SUCCESS!')
            response_status = 'SUCCESS'
            response_reason = 'Unknown request type'
            response_data = None

    except Exception as E:
        response_reason = f'Exception: {str(E)}'
        log.exception(response_reason)
        response_status = 'FAILED'

    response = send_response(event, context, response_status, response_reason, response_data)
    return {
        'Response': response
    }


def run_glue_crawler_job():
    """Run the glue crawler and the glue."""

    glue_client = boto3.client('glue')
    glue_client.start_crawler(
        Name=glue_app_crawler_name
    )
    glue_client.start_crawler(
        Name=glue_server_crawler_name
    )
    time.sleep(150)
    glue_client.start_job_run(
        JobName=glue_app_job_name
    )
    response = glue_client.start_job_run(
        JobName=glue_server_job_name
    )

    return response


def send_response(event, context, response_status, response_reason, response_data):
    """Send response to CloudFormation via S3 presigned URL."""
    log.info('Sending response to CloudFormation')
    response_url = event['ResponseURL']
    log.info(f'Response URL: {response_url}')

    response_body = {'Status': response_status,
                     'PhysicalResourceId': context.aws_request_id,
                     'Reason': response_reason,
                     'StackId': event['StackId'],
                     'RequestId': event['RequestId'],
                     'LogicalResourceId': event['LogicalResourceId']
                     }

    if response_data:
        response_body['Data'] = response_data

    json_response_body = json.dumps(response_body)

    log.info("Response body:\n" + json_response_body)

    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    try:
        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers,
                                timeout=5)
        log.info(f'HTTP PUT Response status code: {response.reason}')
    except Exception as E:
        log.error(f'CloudFormation Response API call failed:\n{E}')
