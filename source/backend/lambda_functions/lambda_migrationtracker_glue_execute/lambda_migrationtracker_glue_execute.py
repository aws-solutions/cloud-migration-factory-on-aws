#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import time
#import requests
from botocore.vendored import requests
import cmf_boto
from cmf_logger import logger

application = os.environ['application']
environment = os.environ['environment']
SCHEMAS = ["app", "wave", "database", "server"]


def lambda_handler(event, context):
    """Process a CloudFormation custom resource request.

    Returns: HTTP PUT request to s3-presigned URL
    """
    logger.info('Function Starting')
    logger.info(f'Incoming Event:\n{json.dumps(event, indent=2)}')
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
            logger.info('SUCCESS!')
            response_status = 'SUCCESS'
            response_reason = 'Unknown request type'
            response_data = None

    except Exception as E:
        response_reason = f'Exception: {str(E)}'
        logger.exception(response_reason)
        response_status = 'FAILED'

    response = send_response(event, context, response_status, response_reason, response_data)
    return {
        'Response': response
    }


def run_glue_crawler_job():
    """Run the glue crawler and the glue for each schema / dynamodb table"""

    glue_client = cmf_boto.client('glue')
    for schema in SCHEMAS:
        glue_client.start_crawler(
            Name=f"{application}-{environment}-{schema}-crawler"
        )

    time.sleep(150)

    response = None

    for schema in SCHEMAS:
        response = glue_client.start_job_run(
            JobName=f"{application}-{environment}-{schema}-extract"
        )

    return response


def send_response(event, context, response_status, response_reason, response_data):
    """Send response to CloudFormation via S3 presigned URL."""
    logger.info('Sending response to CloudFormation')
    response_url = event['ResponseURL']
    logger.info(f'Response URL: {response_url}')

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

    logger.info("Response body:\n" + json_response_body)

    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    try:
        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers,
                                timeout=5)
        logger.info(f'HTTP PUT Response status code: {response.reason}')
    except Exception as E:
        logger.error(f'CloudFormation Response API call failed:\n{E}')
