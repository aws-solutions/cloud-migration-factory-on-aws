#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json
from typing import Any

import boto3
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

policies_table_name = '{}-{}-policies'.format(application, environment)
schema_table_name = '{}-{}-schema'.format(application, environment)

policy_table = boto3.resource('dynamodb').Table(policies_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)


def lambda_handler(event, _):
    logger.info(event['httpMethod'])
    message_prefix = f'Invocation {event["httpMethod"]}'
    if event['httpMethod'] == 'GET':
        resp = policy_table.scan()
        item = resp['Items']
        new_item = sorted(item, key=lambda i: i['policy_id'])
        logger.info(f'{message_prefix} - SUCCESSFUL')
        return {
            'headers': {**default_http_headers},
            'body': json.dumps(new_item)
        }
    elif event['httpMethod'] == 'POST':
        result = validate_post(event, message_prefix)
        if result is not None:
            return result

        body = json.loads(event['body'])
        logger.info('%s item: %s', event['httpMethod'], body)

        # Default to no access to any entity, no read/write/edit/delete.
        entity_access = []
        not_found_attr_list = []
        result = process_entry_access(body, entity_access, not_found_attr_list, message_prefix)
        if result is not None:
            return result

        if len(not_found_attr_list) > 0:
            message = 'The following attributes: ' + ",".join(not_found_attr_list) + " are not defined in schema."
            logger.error(f'{message_prefix} - {message}')
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': message
            }

        item_list = policy_table.scan()['Items']
        for item in item_list:
            if body['policy_name'] in item['policy_name']:
                logger.error(f'{message_prefix} - policy_name: {body["policy_name"]} already exist.')
                return {
                    'headers': {**default_http_headers},
                    'statusCode': 400,
                    'body': 'policy_name: ' + body['policy_name'] + ' already exist.'
                }
        
        result = update_policy(item_list, body, entity_access)
        if result is not None:
            return result


def update_policy(item_list: list, body: dict, entity_access: list[dict[str, Any]]):
    # Get vacant policy_id
    ids = []
    for item in item_list:
        ids.append(int(item['policy_id']))
    ids.sort()
    policy_id = get_next_id(ids)

    # Update policy item
    policy_table.put_item(
        Item={
            'policy_name': body['policy_name'],
            'policy_id': str(policy_id),
            'entity_access': entity_access
        }
    )

    resp = policy_table.get_item(Key={'policy_id': str(policy_id)})
    if 'Item' in resp:
        logger.info('POST SUCCESSFUL')
        return {
            'headers': {**default_http_headers},
            'body': json.dumps(resp['Item'])
        }


def process_entry_access(body: dict, entity_access: list[dict[str, Any]], not_found_attr_list: list[str],
                         message_prefix: str):
    if 'entity_access' in body:
        schemas = schema_table.scan()['Items']
        result = process_entities(body, schemas, entity_access, not_found_attr_list, message_prefix)
        if result is not None:
            return result
    else:
        # Empty policy object provided.
        message = 'Empty policy, aborting save.'
        logger.error(f'{message_prefix} - {message} ')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }


def process_entities(body: dict, schemas: dict, entity_access: list[dict[str, Any]], not_found_attr_list: list[str],
                     message_prefix: str):
    for entity in body['entity_access']:
        if 'schema_name' in entity:
            result = process_schemas(entity, schemas, entity_access, not_found_attr_list, message_prefix)
            if result is not None:
                return result
        else:  # No schema_name provided.
            message = 'Schema name key not found.'
            logger.error(f'{message_prefix} - {message} ')
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': message
            }


def get_next_id(ids: list[int]):
    next_id = 1
    for curr_id in ids:
        if next_id == curr_id:
            next_id += 1
    return next_id


def process_attributes(entity: dict[str,  str], schema: dict[str,  str], not_found_attr_list: list[str],
                       entity_access: list[dict[str, Any]], create: bool, delete: bool, update: bool, read: bool):
    all_found = True
    for attr in entity['attributes']:
        found = False
        for schema_attr in schema['attributes']:
            if schema_attr['name'] == attr['attr_name']:
                found = True
                break
        if not found:
            not_found_attr_list.append(entity['schema_name'] + ' : ' + attr['attr_name'])
            all_found = False
    if all_found:  # No missing attributes.
        editable_attributes = entity['attributes']
        entity_access.append({
            'schema_name': entity['schema_name'],
            'create': create,
            'delete': delete,
            'update': update,
            'read': read,
            'attributes': editable_attributes
        })


def process_matched_schema(entity: dict[str,  str], schema: dict[str,  str], not_found_attr_list: list[str],
                           entity_access: list[dict[str, Any]], create: bool, delete: bool, update: bool,
                           read: bool, message_prefix: str):
    if 'attributes' in entity and len(entity['attributes']) > 0:
        process_attributes(entity, schema, not_found_attr_list, entity_access, create, delete, update, read)
    elif update:
        message = 'At least one attribute must be provided for ' + entity[
            'schema_name'] + ' schema if allowing update rights.'
        logger.error(f'{message_prefix} - {message} ')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }
    else:
        entity_access.append({
            'schema_name': entity['schema_name'],
            'create': create,
            'delete': delete,
            'update': update,
            'read': read
        })


def compute_flag(flag_name: str, entity: dict[str, str]):
    flag = False
    if flag_name in entity and (type(entity[flag_name]) == bool):
        flag = entity[flag_name]
    return flag


def process_schemas(entity: dict[str, str], schemas: list[dict[str: str]], entity_access: list[dict[str, Any]],
                    not_found_attr_list: list[str], message_prefix: str):
    create = compute_flag('create', entity)
    read = compute_flag('read', entity)
    delete = compute_flag('delete', entity)
    update = compute_flag('update', entity)

    schema_name = entity['schema_name']
    if schema_name == 'application':
        schema_name = 'app'

    # Get schema definition.
    schema_found = False
    for schema in schemas:
        if schema['schema_name'] == schema_name:  # Found schema match.
            schema_found = True
            result = process_schema(schema, entity_access, entity, not_found_attr_list, create, delete, update, read,
                                    message_prefix)
            if result is not None:
                return result

    if not schema_found:
        message = entity['schema_name'] + ' not a valid schema.'
        logger.error(f'{message_prefix} - {message} ')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }


def process_schema(schema: dict[str, str], entity_access: list[dict[str, Any]], entity: dict[str, str],
                   not_found_attr_list: list[str], create: bool, delete: bool, update: bool,
                   read: bool, message_prefix: str):
    if schema['schema_type'] == 'automation':
        entity_access.append(
            {'schema_name': entity['schema_name'], 'create': create})
    else:
        result = process_matched_schema(entity, schema, not_found_attr_list, entity_access,
                                        create, delete, update, read, message_prefix)
        if result is not None:
            return result


def validate_post(event: dict[str, str], message_prefix: str):
    try:
        body = json.loads(event['body'])
        if 'policy_name' not in body:
            logger.error(f'{message_prefix} - attribute policy_name is required')
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': 'attribute policy_name is required'
            }
    except Exception as e:
        logger.error(f'{message_prefix} - malformed json input: {e}')
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'malformed json input'
        }
