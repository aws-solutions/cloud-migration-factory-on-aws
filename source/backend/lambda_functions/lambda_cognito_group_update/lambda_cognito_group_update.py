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

import json
import boto3
import botocore
import os
import logging
import urllib.parse

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}


def lambda_handler(event, context):
    client = boto3.client('cognito-idp')
    if 'body' in event and event['body']:
        body = json.loads(event['body'])
    else:
        body = None
    errors = []

    if event['httpMethod'] == 'DELETE' and 'pathParameters' in event and 'group_name' in event['pathParameters']:
        response = client.delete_group(
            GroupName=urllib.parse.unquote(event['pathParameters']['group_name']),
            UserPoolId=os.environ['userpool_id']
        )
        logger.info("Deleted group '%s'." % event['pathParameters']['group_name'])
    elif 'groups' in body and event['httpMethod'] == 'POST':
        for group in body['groups']:
            try:
                if event['httpMethod'] == 'POST':
                    if 'group_name' in group:
                        logger.info("Created group '%s'." % group['group_name'])
                        response = client.create_group(
                            GroupName=group['group_name'],
                            UserPoolId=os.environ['userpool_id']
                        )
                        logger.info("Created group '%s'." % group)
                    else:
                        logger.info("group_name not provided for group object in POST '%s'." % group)
                        errors.append("group_name not provided for group object in provided '%s'." % group)
            except client.exceptions.GroupExistsException as boto_client_error_groupexists:
                logger.error("A group already exists with the name '%s'." % group['group_name'])
                errors.append("A group already exists with the name '%s'." % group['group_name'])
            except client.exceptions.NotAuthorizedException as boto_client_error_permissions:
                logger.error("Group update Lambda does not have permission to update groups "
                             "in pool %s. Cancelling update." % os.environ['userpool_id'])
                errors.append("Group update Lambda does not have permission to update groups "
                              "in pool %s. Cancelling update." % os.environ['userpool_id'])
                raise
            except botocore.exceptions.ClientError as boto_client_error:
                # Error not specific boto client error.
                logger.error(boto_client_error)
                errors.append("Internal error.")
                pass
            except Exception as unknown_error:
                logger.error(unknown_error)
                errors.append("Internal error.")
                pass

    if len(errors) > 0:
        return {'headers': {**default_http_headers},
                'statusCode': 400,
                'body': json.dumps(errors)
                }
    else:
        return {'headers': {**default_http_headers},
                'statusCode': 200
                }
