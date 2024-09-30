#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import botocore
import botocore.exceptions
import os
import urllib.parse

import cmf_boto
from cmf_logger import logger, log_event_received
from cmf_utils import cors, default_http_headers



def create_groups(body, client):
    errors = []
    for group in body['groups']:
        try:
            if 'group_name' in group:
                logger.info("Created group '%s'." % group['group_name'])
                client.create_group(
                    GroupName=group['group_name'],
                    UserPoolId=os.environ['userpool_id']
                )
                logger.info("Created group '%s'." % group)
            else:
                logger.info("group_name not provided for group object in POST '%s'." % group)
                errors.append("group_name not provided for group object in provided '%s'." % group)
        except botocore.exceptions.ClientError as boto_client_error:
            if boto_client_error.response['Error']['Code'] == 'NotAuthorizedException':
                logger.error("Group update Lambda does not have permission to update groups "
                             "in pool %s. Cancelling update." % os.environ['userpool_id'])
                errors.append("Group update Lambda does not have permission to update groups "
                              "in pool %s. Cancelling update." % os.environ['userpool_id'])
            elif boto_client_error.response['Error']['Code'] == 'GroupExistsException':
                logger.error("A group already exists with the name '%s'." % group['group_name'])
                errors.append("A group already exists with the name '%s'." % group['group_name'])
            else:
                # Error not specific boto client error.
                logger.error(boto_client_error)
                errors.append("Internal error.")
        except Exception as unknown_error:
            logger.error(unknown_error)
            errors.append("Internal error.")
    return errors


def extract_body(event):
    if 'body' in event and event['body']:
        return json.loads(event['body'])
    else:
        return None


def lambda_handler(event, _):
    log_event_received(event)

    client = cmf_boto.client('cognito-idp')
    body = extract_body(event)
    errors = []

    if event['httpMethod'] == 'DELETE' and 'pathParameters' in event and 'group_name' in event['pathParameters']:
        try:
            client.delete_group(
                GroupName=urllib.parse.unquote(event['pathParameters']['group_name']),
                UserPoolId=os.environ['userpool_id']
            )
            logger.info("Deleted group '%s'." % event['pathParameters']['group_name'])
        except botocore.exceptions.ClientError as e:
            if 'Error' in e.response and 'Code' in e.response['Error'] and e.response['Error']['Code'] == 'ResourceNotFoundException':
                return {'headers': {**default_http_headers},
                        'statusCode': 404,
                        'body': json.dumps(e.response['Error']['Message'])
                        }
            else:
                return {'headers': {**default_http_headers},
                        'statusCode': 500,
                        'body': json.dumps([repr(e)])
                        }


    elif 'groups' in body and event['httpMethod'] == 'POST':
        errors = create_groups(body, client)

    if len(errors) > 0:
        return {'headers': {**default_http_headers},
                'statusCode': 400,
                'body': json.dumps(errors)
                }
    else:
        return {'headers': {**default_http_headers},
                'statusCode': 200
                }
