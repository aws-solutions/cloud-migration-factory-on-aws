#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import uuid

from urllib import request
from cmf_logger import logger


# Send response function
def send_response(event, context, response_status, response_data):
    try:
        response_body = json.dumps({
            "Status": response_status,
            "PhysicalResourceId": context.log_stream_name,
            "StackId": event['StackId'],
            "RequestId": event['RequestId'],
            "LogicalResourceId": event['LogicalResourceId'],
            "Data": response_data
        })

        logger.info('Response URL: {}'.format(event['ResponseURL']))
        logger.info('Response Body: {}'.format(response_body))

        data = response_body.encode('utf-8')
        req = request.Request(event['ResponseURL'], data=data, method='PUT')
        req.add_header('Content-Type', '')
        req.add_header('Content-Length', len(response_body))
        response = request.urlopen(req)  # nosec B310 URL is provided by CloudFormation

        logger.info('Status code: {}'.format(response.getcode()))
        logger.info('Status message: {}'.format(response.msg))
    except Exception as e:
        logger.error('Custom resource send_response error: {}'.format(e))


def lambda_handler(event, context):
    logger.info('Received event: {}'.format(json.dumps(event)))
    response_data = {
        "Message": "Return UUID"
    }

    try:
        if event['RequestType'] == 'Create':
            response_data = {
                "UUID": str(uuid.uuid4())
            }

        send_response(event, context, 'SUCCESS', response_data)
    except Exception as e:
        logger.error('Error: {}'.format(e))
        response_data = {
            'Error': e
        }
        send_response(event, context, 'FAILED', response_data)
