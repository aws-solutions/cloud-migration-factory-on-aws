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

policies_table = boto3.resource('dynamodb').Table(policies_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)

str_policy_id = 'policy Id: '
str_doesnt_exit = ' does not exist'


class PolicyAttrException(Exception):
    pass


def lambda_handler(event, _):
    logger.info(event['httpMethod'])
    if event['httpMethod'] == 'GET':
        return process_get(event)
    elif event['httpMethod'] == 'PUT':
        return process_put(event)
    elif event['httpMethod'] == 'DELETE':
        return process_delete(event)


def extract_policy_name(policies, body, event, policy):
    policy_name = ''
    for s in policies['Items']:
        if 'policy_name' in body:
            if s['policy_name'].lower() == str(body['policy_name']).lower() and s['policy_id'] != str(
                    event['pathParameters']['policy_id']):
                logger.error('%s policy_name: %s already exist', event['httpMethod'],
                             body['policy_name'])
                raise PolicyAttrException('policy_name: ' + body['policy_name'] + ' already exist')
            policy_name = body['policy_name']
        else:
            policy_name = policy['Item']['policy_name']
    return policy_name


def process_matched_schema(event: dict, entity: dict[str, str], schema: dict[str, str], not_found_attr_list: list[str],
                           entity_access: dict[str, Any], create: bool, delete: bool, update: bool, read: bool):
    if 'attributes' in entity and len(entity['attributes']) > 0:
        process_attributes(entity, schema, not_found_attr_list, entity_access, create, delete, update, read)
    elif update:
        message = 'At least one attribute must be provided for ' + entity[
            'schema_name'] + ' schema if allowing update rights.'
        logger.error('%s %s', event['httpMethod'], message)
        return {'headers': {**default_http_headers}, 'statusCode': 400,
                'body': message}
    else:
        entity_access.append(
            {'schema_name': entity['schema_name'], 'create': create, 'delete': delete,
             'update': update, 'read': read})


def process_attributes(entity: dict[str, str], schema: dict[str, str], not_found_attr_list: list[str],
                       entity_access: list[dict[str, str]], create: bool, delete:bool, update: bool, read: bool):
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
        entity_access.append(
            {'schema_name': entity['schema_name'], 'create': create, 'delete': delete,
             'update': update, 'read': read,
             'attributes': editable_attributes})


def process_schema(event: dict, schema: dict[str, str], entity_access: list[dict[str, str]], entity: dict[str, str],
                   not_found_attr_list: list[str], create: bool, delete: bool, update: bool, read: bool):
    if schema['schema_type'] == 'automation':
        entity_access.append(
            {'schema_name': entity['schema_name'], 'create': create})
    else:
        result = process_matched_schema(event, entity, schema, not_found_attr_list,
                                        entity_access, create, delete, update, read)
        if result is not None:
            return result


def compute_flag(flag_name: str, entity: dict[str, str]):
    flag = False
    if flag_name in entity and (type(entity[flag_name]) == bool):
        flag = entity[flag_name]
    return flag


def process_schemas(event: dict, entity: dict[str, str], schemas: list[dict[str: str]],
                    entity_access: list[dict[str, Any]], not_found_attr_list: list[str]):
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
            result = process_schema(event, schema, entity_access, entity, not_found_attr_list,
                                    create, delete, update, read, )
            if result is not None:
                return result

    if not schema_found:
        message = entity[
                      'schema_name'] + ' not a valid schema.'
        logger.error('%s %s', event['httpMethod'], message)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }


def process_delete(event: dict):
    if str(event['pathParameters']['policy_id']) == '1' or str(event['pathParameters']['policy_id']) == '2':
        # Cannot delete default policies.
        message = 'Default policies Administrator and ReadOnly cannot be deleted.'
        logger.error('%s %s', event['httpMethod'], message)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }

    policy_id = ""
    policies = policies_table.scan()
    for policy in policies['Items']:
        if str(policy['policy_id']) == str(event['pathParameters']['policy_id']):
            policy_id = policy['policy_id']
    if policy_id != "":
        delete_resp = policies_table.delete_item(Key={'policy_id': policy_id})
        if delete_resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info('%s policy_id: %s  was successfully deleted', event['httpMethod'], policy_id)
            return {
                'headers': {**default_http_headers},
                'statusCode': 200,
                'body': "policy: " + policy_id + " was successfully deleted"
            }
        else:
            logger.error('%s %s', event['httpMethod'], delete_resp)
            return {
                'headers': {**default_http_headers},
                'statusCode': delete_resp['ResponseMetadata']['HTTPStatusCode'],
                'body': json.dumps(delete_resp)
            }
    else:
        logger.error('%s policy_id: %s%s', event['httpMethod'], event['pathParameters']['policy_id'], str_doesnt_exit)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': str_policy_id + str(event['pathParameters']['policy_id']) + str_doesnt_exit
        }


def process_get(event: dict):
    resp = policies_table.get_item(Key={'policy_id': event['pathParameters']['policy_id']})
    if 'Item' in resp:
        logger.info('%s SUCCESSFUL', event['httpMethod'])
        return {
            'headers': {**default_http_headers},
            'body': json.dumps(resp['Item'])
        }
    else:
        logger.error('%s%s%s', str_policy_id, event['pathParameters']['policy_id'], str_doesnt_exit)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': str_policy_id + str(event['pathParameters']['policy_id']) + str_doesnt_exit
        }


def process_put(event: dict):
    policy_id = event['pathParameters']['policy_id']
    policy_name = ""

    try:
        body = json.loads(event['body'])
    except Exception as e:
        logger.error('%s malformed json input - %s', event['httpMethod'], e)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'malformed json input'
        }

    logger.info('%s Item: %s', event['httpMethod'], body)

    if 'entity_access' not in body:
        logger.error('%s The attribute entity_access is required', event['httpMethod'])
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': 'The attribute entity_access is required'
        }

    entity_access = []
    not_found_attr_list = []
    if 'entity_access' in body:
        # check if policy_id exist in policy_table
        policy = policies_table.get_item(Key={'policy_id': event['pathParameters']['policy_id']})
        if 'Item' not in policy:
            logger.error('%s %s%s%s', event['httpMethod'], str_policy_id,
                         event['pathParameters']['policy_id'], str_doesnt_exit)
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': str_policy_id + str(event['pathParameters']['policy_id']) + str_doesnt_exit
            }

        # Check if there is a duplicate policy_name
        policies = policies_table.scan()
        try:
            policy_name = extract_policy_name(policies, body, event, policy)
        except PolicyAttrException as e:
            return {
                'headers': {**default_http_headers},
                'statusCode': 400,
                'body': str(e)
            }

        schemas = schema_table.scan()['Items']
        for entity in body['entity_access']:
            result = process_entity(event, entity, schemas, entity_access, not_found_attr_list)
            if result is not None:
                return result

    if len(not_found_attr_list) > 0:
        message = 'The following attributes: ' + ",".join(not_found_attr_list) + " are not defined in schema."
        logger.error('%s %s', event['httpMethod'], message)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }

    resp = policies_table.put_item(
        Item={
            'policy_id': policy_id,
            'policy_name': policy_name,
            'entity_access': entity_access
        }
    )

    logger.info('%s SUCCESSFUL', event['httpMethod'])
    return {
        'headers': {**default_http_headers},
        'statusCode': 200,
        'body': json.dumps(resp)
    }


def process_entity(event: dict, entity: dict[str, str], schemas: list[dict[str: str]],
                    entity_access: list[dict[str, Any]], not_found_attr_list: list[str]):
    if 'schema_name' in entity:
        result = process_schemas(event, entity, schemas, entity_access, not_found_attr_list)
        if result is not None:
            return result

    else:  # No schema_name provided.
        message = 'Schema name key not found.'
        logger.error('%s %s', event['httpMethod'], message)
        return {
            'headers': {**default_http_headers},
            'statusCode': 400,
            'body': message
        }
