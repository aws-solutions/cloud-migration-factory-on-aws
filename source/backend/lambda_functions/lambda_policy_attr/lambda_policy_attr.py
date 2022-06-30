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

policies_table_name = '{}-{}-policies'.format(application, environment)
schema_table_name = '{}-{}-schema'.format(application, environment)

policies_table = boto3.resource('dynamodb').Table(policies_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)


def lambda_handler(event, context):
    logger.info(event['httpMethod'])
    if event['httpMethod'] == 'GET':
        resp = policies_table.get_item(Key={'policy_id': event['pathParameters']['policy_id']})
        if 'Item' in resp:
            logger.info('% SUCCESSFUL', event['httpMethod'])
            return {'headers': {**default_http_headers},
                    'body': json.dumps(resp['Item'])}
        else:
            logger.error('policy Id: %s does not exist', event['pathParameters']['policy_id'])
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': 'policy Id: ' + str(event['pathParameters']['policy_id']) + ' does not exist'}

    elif event['httpMethod'] == 'PUT':

        policy_id = event['pathParameters']['policy_id']
        policy_name = ""

        try:
            body = json.loads(event['body'])
        except:
            logger.error('%s malformed json input', event['httpMethod'])
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': 'malformed json input'}

        logger.info('%s Item: %s', event['httpMethod'], body)

        if 'entity_access' not in body:
            logger.error('%s The attribute entity_access is required', event['httpMethod'])
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': 'The attribute entity_access is required'}

        entity_access = []
        notfoundAttrList = []
        if 'entity_access' in body:
            # check if policy_id exist in policy_table
            policy = policies_table.get_item(Key={'policy_id': event['pathParameters']['policy_id']})
            if 'Item' not in policy:
                logger.error('%s policy Id: %s does not exist', event['httpMethod'],
                             event['pathParameters']['policy_id'])
                return {'headers': {**default_http_headers}, 'statusCode': 400,
                        'body': 'policy Id: ' + str(event['pathParameters']['policy_id']) + ' does not exist'}

            # Check if there is a duplicate policy_name
            policies = policies_table.scan()
            for s in policies['Items']:
                if 'policy_name' in body:
                    if s['policy_name'].lower() == str(body['policy_name']).lower() and s['policy_id'] != str(
                        event['pathParameters']['policy_id']):
                        logger.error('%s policy_name: %s already exist', event['httpMethod'],
                                     body['policy_name'])
                        return {'headers': {**default_http_headers}, 'statusCode': 400,
                                'body': 'policy_name: ' + body['policy_name'] + ' already exist'}
                    policy_name = body['policy_name']
                else:
                    policy_name = policy['Item']['policy_name']

            schemas = schema_table.scan()['Items']
            for entity in body['entity_access']:

                if 'schema_name' in entity:
                    create = False
                    read = False
                    delete = False
                    update = False
                    editable_attributes = []
                    if 'create' in entity and type(entity['create']) == bool:
                        create = entity['create']
                    if 'delete' in entity and type(entity['delete']) == bool:
                        delete = entity['delete']
                    if 'update' in entity and type(entity['update']) == bool:
                        update = entity['update']
                    if 'read' in entity and type(entity['read']) == bool:
                        read = entity['read']

                    schema_name = entity['schema_name']
                    if schema_name == 'application':
                        schema_name = 'app'

                    # Get schema definition.
                    schema_found = False
                    for schema in schemas:
                        if schema['schema_name'] == schema_name:  # Found schema match.
                            schema_found = True
                            all_found = True
                            if schema['schema_type'] == 'automation':
                                entity_access.append(
                                    {'schema_name': entity['schema_name'], 'create': create})
                            else:
                                if 'attributes' in entity and len(entity['attributes']) > 0:
                                    for attr in entity['attributes']:
                                        found = False
                                        for schema_attr in schema['attributes']:
                                            if schema_attr['name'] == attr['attr_name']:
                                                found = True
                                                break
                                        if not found:
                                            notfoundAttrList.append(entity['schema_name'] + ' : ' + attr['attr_name'])
                                            all_found = False
                                    if all_found:  # No missing attributes.
                                        editable_attributes = entity['attributes']
                                        entity_access.append(
                                            {'schema_name': entity['schema_name'], 'create': create, 'delete': delete,
                                             'update': update, 'read': read,
                                             'attributes': editable_attributes})
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

                    if not schema_found:
                        message = entity[
                                      'schema_name'] + ' not a valid schema.'
                        logger.error('%s %s', event['httpMethod'], message)
                        return {'headers': {**default_http_headers}, 'statusCode': 400,
                                'body': message}

                else:  # No schema_name provided.
                    message = 'Schema name key not found.'
                    logger.error('%s %s', event['httpMethod'], message)
                    return {'headers': {**default_http_headers}, 'statusCode': 400,
                            'body': message}
        else:
            # Empty policy object provided.
            message = 'Empty policy, aborting save.'
            logger.error('%s %s', event['httpMethod'], message)
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': message}

        if len(notfoundAttrList) > 0:
            message = 'The following attributes: ' + ",".join(notfoundAttrList) + " are not defined in schema."
            logger.error('%s %s', event['httpMethod'], message)
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': message}

        resp = policies_table.put_item(

            Item={
                'policy_id': policy_id,
                'policy_name': policy_name,
                'entity_access': entity_access
            }

        )

        logger.info('%s SUCCESSFUL', event['httpMethod'])
        return {'headers': {**default_http_headers},
                'statusCode': 200, 'body': json.dumps(resp)}

    elif event['httpMethod'] == 'DELETE':
        if str(event['pathParameters']['policy_id']) == '1' or str(event['pathParameters']['policy_id']) == '2':
            # Cannot delete default policies.
            message = 'Default policies Administrator and ReadOnly cannot be deleted.'
            logger.error('%s %s', event['httpMethod'], message)
            return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': message}

        policy_id = ""
        policies = policies_table.scan()
        for policy in policies['Items']:
            if str(policy['policy_id']) == str(event['pathParameters']['policy_id']):
                policy_id = policy['policy_id']
        if policy_id != "":
            delete_resp = policies_table.delete_item(Key={'policy_id': policy_id})
            if delete_resp['ResponseMetadata']['HTTPStatusCode'] == 200:
                logger.info('%s policy_id: %s  was successfully deleted', event['httpMethod'], policy_id)
                return {'headers': {**default_http_headers},
                        'statusCode': 200, 'body': "policy: " + policy_id + " was successfully deleted"}
            else:
                logger.error('%s %s', event['httpMethod'], delete_resp)
                return {'headers': {**default_http_headers}, 'statusCode': delete_resp['ResponseMetadata']['HTTPStatusCode'],
                        'body': json.dumps(delete_resp)}
        else:
            logger.error('%s policy_id: %s does not exist', event['httpMethod'], event['pathParameters']['policy_id'])
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': 'policy Id: ' + str(event['pathParameters']['policy_id']) + ' does not exist'}
