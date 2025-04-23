#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
#import requests
from botocore.vendored import requests
import cmf_boto
from cmf_logger import logger

ServiceAccountEmail = os.environ['ServiceAccountEmail']
PoolId = os.environ['UserPoolId']
CognitoGroup = os.environ['CognitoGroupName']


def lambda_handler(event, context):
    try:
        logger.info('Event:\n {}'.format(event))
        logger.info('Contex:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            logger.info('Create action')
            create_service_account()
            status = 'SUCCESS'
            message = 'Migration Factory Service Account created successfully'

        elif event['RequestType'] == 'Update':
            logger.info('Update action')
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            logger.info('Delete action')
            delete_service_account()
            status = 'SUCCESS'
            message = 'Migration Factory Service Account deleted successfully'

        else:
            logger.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        logger.info('FAILED!')
        logger.info(e)
        status = 'FAILED'
        message = 'Exception during processing'

    response_data = {'Message': message}
    response = respond(event, context, status, response_data)

    return {
        'Response': response
    }


def create_service_account():
    client = cmf_boto.client('cognito-idp')
    secrets_manager_client = cmf_boto.client('secretsmanager')

    # Generate random password for service account
    pwd = secrets_manager_client.get_random_password(
        PasswordLength=24
        )

    # Create an Service account
    create_user_response = client.admin_create_user(
        UserPoolId=PoolId,
        Username=ServiceAccountEmail,
        MessageAction='SUPPRESS',
        UserAttributes=[
            {
                'Name': 'email',
                'Value': ServiceAccountEmail
            },
        ],
        TemporaryPassword=pwd['RandomPassword']
    )

    # Add service account to admin group
    client.admin_add_user_to_group(
        UserPoolId=PoolId,
        Username=create_user_response['User']['Username'],
        GroupName=CognitoGroup
    )

    # Set service account password
    client.admin_set_user_password(
        UserPoolId=PoolId,
        Username=create_user_response['User']['Username'],
        Password=pwd['RandomPassword'],
        Permanent=True
    )

    # Save password in secrets manager
    secret_name = 'MFServiceAccount-' + PoolId
    secrets_manager_client.create_secret(
        Name=secret_name,
        Description=ServiceAccountEmail,
        SecretString=json.dumps({"username": ServiceAccountEmail, "password": pwd['RandomPassword']})
    )


def delete_service_account():
    secrets_manager_client = cmf_boto.client('secretsmanager')

    secret_name = 'MFServiceAccount-' + PoolId
    try:
        secrets_manager_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )
    except Exception:
        logger.error(f"Service account deletion failed to delete secret '{secret_name}' manual remove maybe required.")

def respond(event, context, response_status, response_data):
    # Build response payload required by CloudFormation
    response_body = {
        'Status': response_status,
        'Reason': 'Details in: ' + context.log_stream_name,
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }

    # Convert json object to string and log it
    json_response_body = json.dumps(response_body)
    logger.info('Response body: {}'.format(str(json_response_body)))

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
        logger.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        logger.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
