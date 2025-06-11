#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import cmf_boto
from botocore.exceptions import ClientError
import os

region = os.environ['region']


def create(event):
    body = json.loads(event['body'])
    request_user = body['user'].replace('\\', '\\\\')
    password = body['password'].replace('\\', '\\\\')
    secret_name = body['secretName']
    os_type = body['osType']
    secret_type = body['secretType']
    description = body['description']

    if 'isSSHKey' in body and body['isSSHKey']:
        iskey = body['isSSHKey']
    else:
        iskey = False

    client = cmf_boto.client('secretsmanager', region_name=region)
    try:
        data = "{\"USERNAME\": \"%s\", \"PASSWORD\": \"%s\", \"SECRET_TYPE\": \"%s\", \"OS_TYPE\": \"%s\", \"IS_SSH_KEY\": \"%s\"}" % (
            request_user, password, secret_type, os_type, iskey)
        client.create_secret(Name=secret_name,
                             Description=description,
                             SecretString=data,
                             Tags=[{"Key": "CMFUse", "Value": "CMF Automation Credential Manager"}]
                             )

        return {"statusCode": 200, "body": "Successfully created Secret - " + secret_name}
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceExistsException':
            msg = "Secret " + secret_name + " already exists"
            print(msg)
            return {"statusCode": 202, "body": msg}
        elif e.response['Error']['Code'] == 'AccessDeniedException':
            msg = "AccessDenied"
            print(msg)
            return {"statusCode": 404, "body": msg}
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            msg = "Possible a credential with the same name was recently deleted, please attempt this again later."
            print(msg)
            return {"statusCode": 405, "body": msg}
        elif e.response['Error']['Code'] == 'ValidationException':
            msg = "Invalid secret name. Must be a valid name containing alphanumeric characters, or any of the following: -/_+=.@!"
            print(msg)
            return {"statusCode": 405, "body": msg}
        else:
            msg = str(e)
            print(msg)
            return {"statusCode": 403, "body": msg}
