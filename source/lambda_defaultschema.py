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

from schema import *
import json, boto3, logging, os
import requests

log = logging.getLogger()
log.setLevel(logging.INFO)

ROLE_TABLE = os.getenv('RoleDynamoDBTable')
SCHEMA_TABLE = os.getenv('SchemaDynamoDBTable')
STAGE_TABLE = os.getenv('StageDynamoDBTable')

def load_schema():
    client = boto3.client('dynamodb')

    for item in factory.schema:

        response = client.put_item(
            TableName = SCHEMA_TABLE,
            Item = item
        )

    for item in roles.schema:

        response = client.put_item(
            TableName = ROLE_TABLE,
            Item = item
        )

    for item in stages.schema:

        response = client.put_item(
            TableName = STAGE_TABLE,
            Item = item
        )


def lambda_handler(event, context):

    try:
        log.info('Event:\n {}'.format(event))
        log.info('Contex:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            log.info('Create action')
            load_schema()
            status='SUCCESS'
            message='Default schema loaded successfully'

        elif event['RequestType'] == 'Update':
            log.info('Update action')
            status='SUCCESS'
            message='No update required'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')
            status='SUCCESS'
            message='No deletion required'

        else:
            log.info('SUCCESS!')
            status='SUCCESS'
            message='Unexpected event received from CloudFormation'

    except Exception as e:
        log.info('FAILED!')
        log.info(e)
        status='FAILED'
        message='Exception during processing'

    response_data = {'Message' : message}
    response=respond(event, context, status, response_data, None)

    return {
        'Response' :response
    }

def respond(event, context, responseStatus, responseData, physicalResourceId):
    #Build response payload required by CloudFormation
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'Details in: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData

    #Convert json object to string and log it
    json_responseBody = json.dumps(responseBody)
    log.info('Response body: {}'.format(str(json_responseBody)))

    #Set response URL
    responseUrl = event['ResponseURL']

    #Set headers for preparation for a PUT
    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    #Return the response to the signed S3 URL
    try:
        response = requests.put(responseUrl,
        data=json_responseBody,
        headers=headers)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
