#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import cmf_boto
from botocore.exceptions import ClientError
import base64
import os

region = os.environ['region']


def get(event):
    secret_name = event['queryStringParameters']['Name']
    client = cmf_boto.client('secretsmanager', region_name=region)

    extra_args = {'Filters': [
        {
            'Key': 'tag-key',
            'Values': ['CMFUse']
        },
        {
            'Key': 'tag-value',
            'Values': ['CMF Automation Credential Manager']
        },
        {
            'Key': 'name',
            'Values': [secret_name]
        }
    ]}

    result = client.list_secrets(**extra_args)
    found = False

    if result['SecretList']:
        for secret in result['SecretList']:
            if secret['Name'] == secret_name:
                try:
                    status_code = 200
                    found = True
                    items = client.get_secret_value(SecretId=secret_name)
                    output = items['SecretString']
                    data = sanitize_secret(output)
                except ClientError as e:
                    return process_api_exception(e, secret_name)

                return {
                    'isBase64Encoded': 'false',
                    'statusCode': status_code,
                    'body': json.dumps(data)
                }
    if not found:
        # Secret not found that matches Credentials Manager signature.
        output = "Secret %s not found, or not under the control of Credentials Manager." % secret_name
        return {"statusCode": 404, "body": output}


def sanitize_secret(output):
    data = json.loads(output)
    if data['SECRET_TYPE'] == 'OS':
        data['PASSWORD'] = "*********"  # NOSONAR This is a password replacement text, not a real password.
        # data sanitization
        data['USERNAME'] = data['USERNAME'].replace('\t', '\\t')
        data['USERNAME'] = data['USERNAME'].replace('\n', '\\n')
        data['USERNAME'] = data['USERNAME'].replace('\r', '\\r')
    elif data['SECRET_TYPE'] == 'keyValue':
        data['SECRET_VALUE'] = "*********"
        # data sanitization
        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\t', '\\t')
        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\n', '\\n')
        data['SECRET_KEY'] = data['SECRET_KEY'].replace('\r', '\\r')
    elif data['SECRET_TYPE'] == 'plainText':
        data['SECRET_STRING'] = "*********"
    else:
        data['PASSWORD'] = "*********"  # NOSONAR This is a password replacement text, not a real password.
        data['APIKEY'] = "*********"
    return data


def process_api_exception(e, secret_name):
    if e.response['Error']['Code'] == 'ResourceNotFoundException':
        data = 'User {} not found in secret manager'.format(secret_name)
        return {
            'isBase64Encoded': 'false',
            'statusCode': 404,
            'body': json.dumps(data)
        }
    elif e.response['Error']['Code'] == 'AccessDeniedException':
        return {"statusCode": 404, "body": "AccessDenied"}
    elif e.response['Error']['Code'] == 'InvalidRequestException':
        return {"statusCode": 404, "body": "Possible this secret was recently deleted"}
