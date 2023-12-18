#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
from json import JSONEncoder
import datetime

import cmf_boto
from cmf_utils import cors, default_http_headers


# subclass JSONEncoder
class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()


def get_user_groups(client, username):
    response = client.admin_list_groups_for_user(
        Username=username,
        UserPoolId=os.environ['userpool_id'],
    )

    groups = []
    for group in response['Groups']:
        groups.append({
            'group_name': group['GroupName']

        })

    return groups


def lambda_handler(event, context):
    print(f'lambda_handler with {event}, {context}')
    client = cmf_boto.client('cognito-idp')
    response = client.list_users(
        UserPoolId=os.environ['userpool_id']
    )

    # Create MF formatted response with required data.
    users = []
    for user in response['Users']:
        newuser = {}
        newuser['userRef'] = user['Username']

        # Build MF history object for user.
        history = {
            'createdTimestamp': user['UserCreateDate'],
            'lastModifiedTimestamp': user['UserLastModifiedDate']
        }

        # Add standard Cognito data..
        newuser['_history'] = history
        newuser['enabled'] = user['Enabled']
        newuser['status'] = user['UserStatus']

        newuser['groups'] = get_user_groups(client, user['Username'])

        for attrib in user['Attributes']:
            if attrib['Name'] == 'email':
                newuser['email'] = attrib['Value']

        # TODO: this is no longer supported //NOSONAR
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp/client/list_users.html
        if 'MFAOptions' in user and len(user['MFAOptions']) > 0:
            newuser['mfaEnabled'] = True
        else:
            newuser['mfaEnabled'] = False

        users.append(newuser)
    return {
        'headers': {**default_http_headers},
        'statusCode': 200,
        'body': json.dumps(users, cls=DateTimeEncoder)
    }
