#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import boto3
import json
import logging
import os

import requests

log = logging.getLogger()
log.setLevel(logging.INFO)

ROLE_TABLE = os.getenv('RoleDynamoDBTable')
SCHEMA_TABLE = os.getenv('SchemaDynamoDBTable')
POLICY_TABLE = os.getenv('PolicyDynamoDBTable')

# Load default schema from json.
with open('default_schema.json') as json_schema_file:
    default_schema = json.load(json_schema_file)

# Load default policies from json.
with open('default_policies.json') as json_policies_file:
    default_policies = json.load(json_policies_file)

# Load default roles from json.
with open('default_roles.json') as json_roles_file:
    default_roles = json.load(json_roles_file)


def load_schema():
    client = boto3.client('dynamodb')

    for item in default_schema:
        client.put_item(
            TableName=SCHEMA_TABLE,
            Item=item
        )

    for item in default_roles:
        client.put_item(
            TableName=ROLE_TABLE,
            Item=item
        )

    for item in default_policies:
        client.put_item(
            TableName=POLICY_TABLE,
            Item=item
        )


def lambda_handler(event, context):
    try:
        log.info('Event:\n {}'.format(event))
        log.info('Context:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            log.info('Create action')
            load_schema()
            status = 'SUCCESS'
            message = 'Default schema loaded successfully'

        elif event['RequestType'] == 'Update':
            log.info('Update action')
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')
            status = 'SUCCESS'
            message = 'No deletion required'

        else:
            log.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        log.info('FAILED!')
        log.info(e)
        status = 'FAILED'
        message = 'Exception during processing'

    response_data = {'Message': message}
    response = respond(event, context, status, response_data)

    return {
        'Response': response
    }


def respond(event, context, response_status, response_data):
    # Build response payload required by CloudFormation
    response_body = {}
    response_body['Status'] = response_status
    response_body['Reason'] = 'Details in: ' + context.log_stream_name
    response_body['PhysicalResourceId'] = context.log_stream_name
    response_body['StackId'] = event['StackId']
    response_body['RequestId'] = event['RequestId']
    response_body['LogicalResourceId'] = event['LogicalResourceId']
    response_body['Data'] = response_data

    # Convert json object to string and log it
    json_response_body = json.dumps(response_body)
    log.info('Response body: {}'.format(str(json_response_body)))

    # Set response URL
    response_url = event['ResponseURL']

    # Set headers for preparation for a PUT
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    # Return the response to the signed S3 URL
    try:
        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers,
                                timeout=30)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
