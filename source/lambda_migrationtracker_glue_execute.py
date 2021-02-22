#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################

import json
import boto3
import logging
import os
import datetime
import time
import requests
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

application = os.environ['application']
environment = os.environ['environment']
glue_app_crawler_name = '{}-{}-app-crawler'.format(application,environment)
glue_server_crawler_name = '{}-{}-server-crawler'.format(application, environment)
glue_app_job_name = '{}-{}-app-extract'.format(application, environment)
glue_server_job_name = '{}-{}-server-extract'.format(application, environment)

def lambda_handler(event, context):
    
    """Process a CloudFormation custom resource request.

    Returns: HTTP PUT request to s3-presigned URL
    """
    log.info('Function Starting')
    log.info(f'Incoming Event:\n{json.dumps(event,indent=2)}')
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
            status='SUCCESS'

    except Exception as E:
        response_reason = f'Exception: {str(E)}'
        log.exception(response_reason)
        response_status = 'FAILED'
        if event.get('PhysicalResourceId'):
            resource_id = event.get('PhysicalResourceId')
        else:
            resource_id = event.get('LogicalResourceId')

    response = send_response(event, context, response_status,response_reason, response_data)
    return {
        'Response' :response
    }
    
def run_glue_crawler_job():
    """Run the glue crawler and the glue."""
    
    glue_client = boto3.client('glue')
    response = glue_client.start_crawler(
        Name= glue_app_crawler_name
        )
    response = glue_client.start_crawler(
        Name= glue_server_crawler_name
        )
    time.sleep(150)
    response = glue_client.start_job_run(
        JobName= glue_app_job_name
        )
    response = glue_client.start_job_run(
        JobName= glue_server_job_name
        )
        

    return response


def send_response(event, context, response_status, response_reason, response_data):
    """Send response to CloudFormation via S3 presigned URL."""
    log.info('Sending response to CloudFormation')
    response_url = event['ResponseURL']
    log.info(f'Response URL: {response_url}')

    responseBody = {}

    responseBody['Status'] = response_status
    responseBody['PhysicalResourceId'] = context.aws_request_id
    responseBody['Reason'] = response_reason
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    if response_data:
        responseBody['Data'] = response_data

    json_responseBody = json.dumps(responseBody)

    log.info("Response body:\n" + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    try:
        response = requests.put(response_url,
                                data=json_responseBody,
                                headers=headers,
                                timeout=5)
        log.info(f'HTTP PUT Response status code: {response.reason}')
    except Exception as E:
        log.error(f'CloudFormation Response API call failed:\n{E}')
