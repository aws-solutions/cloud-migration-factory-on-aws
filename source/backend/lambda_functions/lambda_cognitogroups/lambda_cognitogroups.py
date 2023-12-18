#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os

import cmf_boto
from cmf_logger import logger
from cmf_utils import cors

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


def lambda_handler(event, context):
    logger.debug(f'event: {event}, context: {context}')
    client = cmf_boto.client('cognito-idp')
    response = client.list_groups(
        UserPoolId=os.environ['userpool_id']
    )
    groups = []
    for group in response['Groups']:
        groups.append(group['GroupName'])
    return {'headers': {**default_http_headers},
        'statusCode': 200,
        'body': json.dumps(groups)
    }