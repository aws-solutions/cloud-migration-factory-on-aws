#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json

import cmf_boto
from cmf_logger import logger, log_event_received
from cmf_utils import cors, default_http_headers

application = os.environ['application']
environment = os.environ['environment']

roles_table_name = '{}-{}-roles'.format(application, environment)
policies_table_name = '{}-{}-policies'.format(application, environment)

roles_table = cmf_boto.resource('dynamodb').Table(roles_table_name)
policy_table = cmf_boto.resource('dynamodb').Table(policies_table_name)


def process_get(event):
    resp = roles_table.scan()
    items = resp['Items']
    logger.info('%s SUCCESSFUL', event['httpMethod'])
    return {'headers': {**default_http_headers},
            'body': json.dumps(items)}


def process_post(event):
    try:
        body = json.loads(event['body'])
    except BaseException as e:  # //NOSONAR
        logger.error(f'malformed json input {e}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    logger.info('%s Role Item: %s', event['httpMethod'], body)
    response = validate_input(body)
    if response is not None:
        return response

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
    if check is False:
        logger.error('One or more policy_id in %s does not exist', body['policies'])
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'One or more policy_id in ' + str(body['policies']) + ' does not exist'}
    # Get vacant role_id
    ids = []
    for item in itemlist['Items']:
        ids.append(int(item['role_id']))
    ids.sort()
    role_id = get_next_id(ids)

    resp = roles_table.put_item(
        Item={
            'role_id': str(role_id),
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


def validate_input(body):
    if 'role_name' not in body:
        logger.error('attribute role_name is required')
        return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'attribute role_name is required'}
    if 'policies' not in body:
        logger.error('attribute policies is required')
        return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'attribute policies is required'}
    for item in body['policies']:
        if 'policy_id' not in item:
            logger.error('attribute policy_id is required')
            return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'attribute policy_id is required'}
    if 'groups' not in body:
        logger.error('attribute groups is required')
        return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'attribute groups is required'}
    for item in body['groups']:
        if 'group_name' not in item:
            logger.error('attribute group_name is required')
            return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'attribute group_name is required'}


def get_next_id(ids: list[int]):
    next_id = 1
    for curr_id in ids:
        if next_id == curr_id:
            next_id += 1
    return next_id


def lambda_handler(event, _):
    log_event_received(event)

    if event['httpMethod'] == 'GET':
        logger.info('GET')
        return process_get(event)
    elif event['httpMethod'] == 'POST':
        logger.info('POST')
        return process_post(event)
