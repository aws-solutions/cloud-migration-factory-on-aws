#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from policy import MFAuth
import item_validation
from typing import Any
from decimal import Decimal

from cmf_logger import logger, log_event_received
import cmf_boto
from cmf_utils import cors, default_http_headers

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)

schema_table = cmf_boto.resource('dynamodb').Table(schema_table_name)

PREFIX_INVOCATION = 'Invocation:'
SUFFIX_DOESNT_EXIST = 'does not exist'


def lambda_handler(event: Any, _):
    logging_context = 'unknown'
    log_event_received(event)

    if 'schema' in event['pathParameters']:
        schema_name = event['pathParameters']['schema']
        logging_context = schema_name + ':' + event['httpMethod']
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}')

        #  Get schema object.
        schema = {}
        schema_found = False
        for data_schema in schema_table.scan()['Items']:
            if data_schema['schema_name'] == schema_name:
                schema = data_schema
                schema_found = True
                break
        if not schema_found:
            msg = 'Invalid schema provided :' + schema_name
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

    data_table_name = '{}-{}-'.format(application, environment) + schema_name + 's'
    data_table = cmf_boto.resource('dynamodb').Table(data_table_name)

    if event['httpMethod'] == 'GET':
        return process_get(event, data_table, schema_name, logging_context)
    elif event['httpMethod'] == 'PUT':
        return process_put(event, data_table, schema_name, schema, logging_context)
    elif event['httpMethod'] == 'DELETE':
        return process_delete(event, data_table, schema_name, logging_context)


def process_get(event: Any, data_table: Any, schema_name: str, logging_context: str):
    if 'appid' in event['pathParameters']:
        resp = data_table.query(
            IndexName='app_id-index',
            KeyConditionExpression=Key('app_id').eq(event['pathParameters']['appid'])
        )
        if 'ResponseMetadata' in resp and resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {'headers': {**default_http_headers},
                    'body': json.dumps(resp['Items'])}
        else:
            msg = 'Error getting data from table for appid: ' + str(event['pathParameters']['appid'])
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
    elif 'id' in event['pathParameters']:
        resp = data_table.get_item(Key={schema_name + '_id': event['pathParameters']['id']})
        if 'Item' in resp:
            return {'headers': {**default_http_headers},
                    'body': json.dumps(resp['Item'], cls = JsonEncoder)}
        else:
            msg = f'{schema_name} Id {str(event["pathParameters"]["id"])} {SUFFIX_DOESNT_EXIST}'
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': [msg]})}


def process_put(event: Any, data_table: Any, schema_name: str, schema: Any, logging_context: str):
    auth = MFAuth()
    auth_response = auth.get_user_attribute_policy(event, schema_name)
    if auth_response['action'] == 'allow':
        return process_put_validated(event, data_table, schema_name, schema, auth_response, logging_context)
    else:
        logger.warning(f'{PREFIX_INVOCATION} {logging_context}, Authorisation failed: {json.dumps(auth_response)}')
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': json.dumps({'errors': [auth_response]})}


def process_put_validated(event: Any, data_table: Any, schema_name: str, schema: Any, auth_response: dict,
                          logging_context: str):
    try:
        body = json.loads(event['body'])
        if schema_name + "_id" in body:
            msg = 'You cannot modify ' + schema_name + '_id, it is managed by the system'
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
    except Exception as e:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {str(e)}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': ['malformed json input']})}

    existing_item = data_table.get_item(Key={schema_name + '_id': event['pathParameters']['id']})
    print(existing_item)
    response = check_item_exists(existing_item, data_table, event, schema_name, body, logging_context)
    if response is not None:
        return response

    new_item = cleanup_keys(body, existing_item)

    # Validate item against schema attribute requirements
    item_validation_result = item_validation.check_valid_item_create(new_item['Item'], schema)
    if item_validation_result is not None:
        logger.error('Invocation: %s, Item validation failed: ' + json.dumps(item_validation_result),
                     logging_context)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [item_validation_result]})}

    # Update record audit.
    new_audit = {}
    if 'user' in auth_response:
        new_audit['lastModifiedBy'] = auth_response['user']
        new_audit['lastModifiedTimestamp'] = datetime.now(timezone.utc).isoformat()

    if '_history' in new_item['Item']:
        old_audit = new_item['Item']['_history']
        if 'createdTimestamp' in old_audit:
            new_audit['createdTimestamp'] = old_audit['createdTimestamp']
        if 'createdBy' in old_audit:
            new_audit['createdBy'] = old_audit['createdBy']

    new_item['Item']['_history'] = new_audit
    resp = data_table.put_item(
        Item=new_item['Item']
    )
    return {'headers': {**default_http_headers},
            'body': json.dumps(resp)}


def check_item_exists(existing_item: Any, data_table: Any, event: Any, schema_name: str, body: Any,
                                    logging_context: str):
    if 'Item' not in existing_item:
        msg = f'{schema_name} Id: {str(event["pathParameters"]["id"])} {SUFFIX_DOESNT_EXIST}'
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

    # Check if there is an existing [schema]_name
    existing_data = item_validation.scan_dynamodb_data_table(data_table)
    for existing_item in existing_data:
        if schema_name + '_name' in body:
            if existing_item[schema_name + '_name'].lower() == str(body[schema_name + '_name']).lower() and \
                    existing_item[schema_name + '_id'] != str(event['pathParameters']['id']):
                msg = schema_name + '_name: ' + body[schema_name + '_name'] + ' already exist'
                logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}


def cleanup_keys(body: Any, existing_item: Any):
    # Merge new attributes with existing one
    for key in body.keys():
        existing_item['Item'][key] = body[key]
    new_item = existing_item
    keys = list(new_item['Item'].keys())

    # Delete empty keys
    for key in keys:
        if new_item['Item'][key] == '':
            del new_item['Item'][key]
            continue
        if isinstance(new_item['Item'][key], list):
            if len(new_item['Item'][key]) == 1 and new_item['Item'][key][0] == '':
                del new_item['Item'][key]

    return new_item


def get_delete_response(logging_context, respdel):
    if respdel['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info(f'{PREFIX_INVOCATION} {logging_context}, All items successfully deleted.')
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': "Item was successfully deleted."}
    else:
        logger.error(f'{PREFIX_INVOCATION}: {logging_context}, {json.dumps(respdel)}')
        return {'headers': {**default_http_headers},
                'statusCode': respdel['ResponseMetadata']['HTTPStatusCode'],
                'body': json.dumps({'errors': [respdel]})}


def process_delete(event: Any, data_table: Any, schema_name: str, logging_context: str):
    auth = MFAuth()
    auth_response = auth.get_user_resource_creation_policy(event, schema_name)
    if auth_response['action'] == 'allow':
        resp = data_table.get_item(Key={schema_name + '_id': event['pathParameters']['id']})
        if 'Item' in resp:
            try:
                respdel = data_table.delete_item(
                    Key={schema_name + '_id': event['pathParameters']['id']},
                    ConditionExpression=Attr('deletion_protection').ne(True),
                )
            except ClientError as e:
                logger.error(f'{PREFIX_INVOCATION} {logging_context}, {e}')
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    msg = 'Record has deletion protection flag enabled, and cannot be deleted.'
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

            return get_delete_response(logging_context, respdel)

        else:
            msg = f'{schema_name} Id: {str(event["pathParameters"]["id"])} {SUFFIX_DOESNT_EXIST}'
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, {msg}')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
    else:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Authorisation failed: {json.dumps(auth_response)}')
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': json.dumps({'errors': [auth_response]})}

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)