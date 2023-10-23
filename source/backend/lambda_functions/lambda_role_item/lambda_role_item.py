#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


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
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}
application = os.environ['application']
environment = os.environ['environment']

roles_table_name = '{}-{}-roles'.format(application, environment)
policy_table_name = '{}-{}-policies'.format(application, environment)

role_table = boto3.resource('dynamodb').Table(roles_table_name)
policy_table = boto3.resource('dynamodb').Table(policy_table_name)

CONST_ROLE_ID = 'role Id:'


def process_get(event):
    resp = role_table.get_item(Key={'role_id': event['pathParameters']['role_id']})
    if 'Item' in resp:
        logger.info('%s SUCCESSFUL', event['httpMethod'])
        return {
            'headers': {**default_http_headers},
            'body': json.dumps(resp['Item'])
        }
    else:
        logger.error(f'{CONST_ROLE_ID} %s does not exist', event['pathParameters']['role_id'])
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': f'{CONST_ROLE_ID} {str(event["pathParameters"]["role_id"])} does not exist'
        }


def validate_input(body):
    if "role_id" in body:
        logger.error('You cannot modify role_id, this is managed by the system')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': "You cannot modify role_id, this is managed by the system"
        }
    if 'policies' not in body:
        logger.error('attribute policies is required')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'attribute policies is required'
        }
    for item in body['policies']:
        if 'policy_id' not in item:
            logger.error('attribute policy_id is required')
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': 'attribute policy_id is required'
            }
    if 'role_name' not in body:
        logger.error('attribute role_name is required')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'attribute role_name is required'
        }
    if 'groups' not in body:
        logger.error('attribute groups is required')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'attribute groups is required'
        }
    for item in body['groups']:
        if 'group_name' not in item:
            logger.error('attribute group_name is required')
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': 'attribute group_name is required'
            }


def process_put(event):
    try:
        body = json.loads(event['body'])
    except BaseException as e:  # //NOSONAR
        logger.error(f'malformed json input {e}')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'malformed json input'
        }

    logger.info('PUT Role Item: %s', body)

    response = validate_input(body)
    if response is not None:
        return response

    # Check if role id exist
    resp = role_table.get_item(Key={'role_id': event['pathParameters']['role_id']})
    if 'Item' not in resp:
        logger.error('role_id: %s does not exist', event['pathParameters']['role_id'])
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': f'{CONST_ROLE_ID} {str(event["pathParameters"]["role_id"])} does not exist'
        }

    # Check if policy id exist
    policyids = []
    policies = policy_table.scan()['Items']
    for policy in policies:
        policyids.append(policy['policy_id'])
    check = True
    for item in body['policies']:
        if item['policy_id'] not in policyids:
            check = False
    if check is False:
        logger.error('One or more policy_id in %s does not exist', body['policies'])
        return {
            'headers': {**default_http_headers},
            'statusCode': 400, 'body': 'One or more policy_id in ' + str(body['policies']) + ' does not exist'
        }

    # Check if there is a duplicate role_name
    roles = role_table.scan()
    for role in roles['Items']:
        if 'role_name' in body and  role['role_name'].lower() == str(body['role_name']).lower() and \
                role['role_id'] != str(event['pathParameters']['role_id']):
            logger.error('role_name: %s already exist', body['role_name'])
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': 'role_name: ' + body['role_name'] + ' already exist'
            }

    # Updating existing role
    resp = role_table.put_item(
        Item={
            'role_id': event['pathParameters']['role_id'],
            'role_name': body['role_name'],
            'policies': body['policies'],
            'groups': body['groups']
        }
    )
    logger.info('%s SUCCESSFUL', event['httpMethod'])
    return {
        'headers': {**default_http_headers},
        'body': json.dumps(resp)
    }


def process_delete(event):
    logger.info('%s role_id: %s', event['httpMethod'], event['pathParameters']['role_id'])
    resp = role_table.get_item(Key={'role_id': event['pathParameters']['role_id']})
    if 'Item' in resp:
        respdel = role_table.delete_item(Key={'role_id': event['pathParameters']['role_id']})
        if respdel['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info('%s SUCCESSFUL', event['httpMethod'])
            return {
                'headers': {**default_http_headers},
                'statusCode': 200,
                'body': "Role " + str(resp['Item']) + " was successfully deleted"
            }
        else:
            logger.error('%s FAILED', respdel)
            return {
                'headers': {**default_http_headers},
                'statusCode': respdel['ResponseMetadata']['HTTPStatusCode'],
                'body': json.dumps(respdel)
            }
    else:
        logger.error(f'{CONST_ROLE_ID} %s does not exist', event['pathParameters']['role_id'])
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': f'{CONST_ROLE_ID} {str(event["pathParameters"]["role_id"])} does not exist'
        }


def lambda_handler(event, _):
    logger.info(event['httpMethod'])
    if event['httpMethod'] == 'GET':
        return process_get(event)
    elif event['httpMethod'] == 'PUT':
        return process_put(event)
    elif event['httpMethod'] == 'DELETE':
        return process_delete(event)
