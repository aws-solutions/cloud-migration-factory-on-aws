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

import os
import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy' : "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}
application = os.environ['application']
environment = os.environ['environment']

roles_table_name = '{}-{}-roles'.format(application, environment)
policies_table_name = '{}-{}-policies'.format(application, environment)

roles_table = boto3.resource('dynamodb').Table(roles_table_name)
policy_table = boto3.resource('dynamodb').Table(policies_table_name)


def lambda_handler(event, context):
    if event['httpMethod'] == 'GET':
        logger.info('GET')
        resp = roles_table.scan()
        items = resp['Items']
        logger.info('%s SUCCESSFUL', event['httpMethod'])
        return {'headers': {**default_http_headers},
                'body': json.dumps(items)}
    elif event['httpMethod'] == 'POST':
        logger.info('POST')
        try:
            body = json.loads(event['body'])
        except:
            logger.error('malformed json input')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'malformed json input'}

        logger.info('%s Role Item: %s', event['httpMethod'], body)
        if 'role_name' not in body:
            logger.error('attribute role_name is required')
            return {'statusCode': 400, 'body': 'attribute role_name is required'}
        if 'policies' not in body:
            logger.error('attribute policies is required')
            return {'statusCode': 400, 'body': 'attribute policies is required'}
        for item in body['policies']:
            if 'policy_id' not in item:
                logger.error('attribute policy_id is required')
                return {'statusCode': 400, 'body': 'attribute policy_id is required'}
        if 'groups' not in body:
            logger.error('attribute groups is required')
            return {'statusCode': 400, 'body': 'attribute groups is required'}
        for item in body['groups']:
            if 'group_name' not in item:
                logger.error('attribute group_name is required')
                return {'statusCode': 400, 'body': 'attribute group_name is required'}

        # Check if role already exist
        itemlist = roles_table.scan()
        for item in itemlist['Items']:
            if body['role_name'] in item['role_name']:
                logger.error('role_name already exist: %s', body['role_name'])
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': 'role_name already exist'}

        # Check if policy id exist
        policyids = []
        policies = policy_table.scan()['Items']
        for policy in policies:
            policyids.append(policy['policy_id'])
        check = True
        for item in body['policies']:
            if item['policy_id'] not in policyids:
                check = False
        if check == False:
            logger.error('One or more policy_id in %s does not exist', body['policies'])
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'One or more policy_id in ' + str(body['policies']) + ' does not exist'}
        # Get vacant role_id
        ids = []
        for item in itemlist['Items']:
            ids.append(int(item['role_id']))
        ids.sort()
        role_id = 1
        for id in ids:
            if role_id == id:
                role_id += 1
        resp = roles_table.put_item(
            Item={
                'role_id': str(role_id),
                'role_name': body['role_name'],
                'policies': body['policies'],
                'groups': body['groups']
            }
        )
        logger.info('%s SUCCESSFUL', event['httpMethod'])
        return {'headers': {**default_http_headers},
                'body': json.dumps(resp)}
