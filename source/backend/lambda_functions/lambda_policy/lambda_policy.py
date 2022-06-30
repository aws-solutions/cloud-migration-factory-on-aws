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

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level = logging.INFO)
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

policy_table = boto3.resource('dynamodb').Table(policies_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)

def lambda_handler(event, context):
    logger.info(event['httpMethod'])
    if event['httpMethod'] == 'GET':
        resp = policy_table.scan()
        item = resp['Items']
        newitem = sorted(item, key = lambda i: i['policy_id'])
        newitem = sorted(item, key = lambda i: i['policy_id'])
        logger.info('Invocation: GET - SUCCESSFUL')
        return {
            'headers': {**default_http_headers},
            'body': json.dumps(newitem)
        }

    elif event['httpMethod'] == 'POST':
        try:
            body = json.loads(event['body'])
            if 'policy_name' not in body:
                logger.error('Invocation: POST - attribute policy_name is required')
                return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'attribute policy_name is required'}
        except:
            logger.error('Invocation: POST - malformed json input')
            return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'malformed json input'}

        logger.info('%s item: %s', event['httpMethod'], body)

        # Default to no access to any entity, no read/write/edit/delete.
        entity_access = []
        notfoundAttrList = []
        if 'entity_access' in body:
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
                                            notfoundAttrList.append( entity['schema_name'] + ' : ' + attr['attr_name'])
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
                                    logger.error('Invocation: POST - ' + message)
                                    return {'headers': {**default_http_headers}, 'statusCode': 400,
                                            'body': message}
                                else:
                                    entity_access.append(
                                        {'schema_name': entity['schema_name'], 'create': create, 'delete': delete,
                                         'update': update, 'read': read})

                    if not schema_found:
                        message = entity[
                            'schema_name'] + ' not a valid schema.'
                        logger.error('Invocation: POST - ' + message)
                        return {'headers': {**default_http_headers}, 'statusCode': 400,
                                'body': message}

                else:  # No schema_name provided.
                    message = 'Schema name key not found.'
                    logger.error('Invocation: POST - ' + message)
                    return {'headers': {**default_http_headers}, 'statusCode': 400,
                            'body': message}
        else:
            # Empty policy object provided.
            message = 'Empty policy, aborting save.'
            logger.error('Invocation: POST - ' + message)
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': message}

        if len(notfoundAttrList) > 0:
            message = 'The following attributes: ' + ",".join(notfoundAttrList) + " are not defined in schema."
            logger.error('POST - ' + message)
            return {'headers': {**default_http_headers}, 'statusCode': 400,
                    'body': message}

        itemlist = policy_table.scan()
        for item in itemlist['Items']:
            if body['policy_name'] in item['policy_name']:
                logger.error('Invocation: POST - policy_name: ' + body['policy_name'] + ' already exist.')
                return {'headers': {**default_http_headers}, 'statusCode': 400, 'body': 'policy_name: ' + body['policy_name'] + ' already exist.'}
        # Get vacant policy_id
        ids = []
        for item in itemlist['Items']:
            ids.append(int(item['policy_id']))
        ids.sort()
        policy_id = 1
        for id in ids:
           if policy_id == id:
               policy_id += 1

        # Update policy item
        resp = policy_table.put_item(
            Item={
                'policy_name': body['policy_name'],
                'policy_id': str(policy_id),
                'entity_access': entity_access
            }
        )

        resp =  policy_table.get_item(Key={'policy_id': str(policy_id)})
        if 'Item' in resp:
            logger.info('POST SUCCESSFUL')
            return {'headers': {**default_http_headers},
                    'body': json.dumps(resp['Item'])}
