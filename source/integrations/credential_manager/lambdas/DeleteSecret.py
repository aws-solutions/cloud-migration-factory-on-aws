#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import cmf_boto
from botocore.exceptions import ClientError
import os

region = os.environ['region']


def delete(event):
    body = json.loads(event['body'])
    secret_name = body['secretName']
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
    deleted = False

    if result['SecretList']:
        for secret in result['SecretList']:
            if secret['Name'] == secret_name:
                # Secret found that is under the control of Credentials Manager, proceed with deletion.
                try:
                    client.delete_secret(
                                                    SecretId=secret_name,
                                                    ForceDeleteWithoutRecovery=True
                                                    )
                    output = "Successfully deleted secret - %s" %secret_name
                    status_code = 200
                    deleted = True

                except ClientError as e:
                    if e.response['Error']['Code'] == 'AccessDeniedException':
                        return {"statusCode": 404, "body": "AccessDenied"}

                return {
                    'statusCode': status_code,
                    'body': output
                }

    return process_not_deleted(deleted, secret_name)


def process_not_deleted(deleted, secret_name):
    if not deleted:
        # Secret not found that matches Credentials Manager signature.
        output = "Secret %s not found, or not under the control of Credentials Manager." % secret_name
        return {"statusCode": 404, "body": output}
