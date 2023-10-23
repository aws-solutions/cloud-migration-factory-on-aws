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
local_bucket = os.environ['local_bucket']
remote_bucket = os.environ['remote_bucket']
key_prefix = os.environ['key_prefix']


def lambda_handler(event, context):

    """Process a CloudFormation custom resource request.

    Returns: HTTP PUT request to s3-presigned URL
    """
    log.info('Function Starting')
    log.info(f'Incoming Event:\n{json.dumps(event,indent=2)}')
    log.info(f'Context Object:\n{vars(context)}')
    try:
        if (event['RequestType'] == 'Create') or (event['RequestType'] == 'Update'):
            response_data = copy_glue_script_to_local()
            response_reason = 'Copy Glue Script to local bucket on CFN creation'
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
        response_data = None

    response = send_response(event, context, response_status,response_reason, response_data)
    return {
        'Response': response
    }


def copy_glue_script_to_local():
    """Copy Glue script from remote bucket to local S3"""

    s3 = boto3.resource('s3')
    app_key = key_prefix + "/Migration_Tracker_App_Extract_Script.py"
    server_key = key_prefix + "/Migration_Tracker_Server_Extract_Script.py"
    copy_source = {
        'Bucket': remote_bucket,
        'Key': app_key
    }
    print("This is local bucket: " + local_bucket + " This is remote bucket: " +
          remote_bucket + " and this is the copy source")
    response = s3.meta.client.copy(copy_source, local_bucket,
                                   'GlueScript/Migration_Tracker_App_Extract_Script.py')
    print("**** App Script Copy ****")
    print(response)
    copy_source = {
        'Bucket': remote_bucket,
        'Key': server_key
    }
    response = s3.meta.client.copy(copy_source, local_bucket,
                                   'GlueScript/Migration_Tracker_Server_Extract_Script.py')
    print("**** Server Script Copy ****")
    print(response)
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
