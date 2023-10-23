#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json
import boto3
import datetime
from boto3.dynamodb.conditions import Key, Attr
from policy import MFAuth
import item_validation
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

schema_table_name = '{}-{}-schema'.format(application, environment)

schema_table = boto3.resource('dynamodb').Table(schema_table_name)


def lambda_handler(event, context):
    logging_context = 'unknown'

    if 'schema' in event['pathParameters']:
        schema_name = event['pathParameters']['schema']
        logging_context = schema_name + ':' + event['httpMethod']
        logger.debug('Invocation: %s', logging_context)

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
            logger.error('Invocation: %s, ' + msg, logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

    data_table_name = '{}-{}-'.format(application, environment) + schema_name + 's'
    data_table = boto3.resource('dynamodb').Table(data_table_name)

    if event['httpMethod'] == 'GET':
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
                logger.error('Invocation: %s, ' + msg, logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
        elif 'id' in event['pathParameters']:
            resp = data_table.get_item(Key={schema_name + '_id': event['pathParameters']['id']})
            if 'Item' in resp:
                return {'headers': {**default_http_headers},
                        'body': json.dumps(resp['Item'])}
            else:
                msg = schema_name + ' Id ' + str(event['pathParameters']['id']) + ' does not exist'
                logger.error('Invocation: %s, ' + msg, logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

    elif event['httpMethod'] == 'PUT':
        auth = MFAuth()
        authResponse = auth.getUserAttributePolicy(event, schema_name)
        if authResponse['action'] == 'allow':
            try:
                body = json.loads(event['body'])
                if schema_name + "_id" in body:
                    msg = 'You cannot modify ' + schema_name + '_id, it is managed by the system'
                    logger.error('Invocation: %s, ' + msg, logging_context)
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
            except Exception as e:
                logger.error('Invocation: %s, ' + str(e), logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': ['malformed json input']})}
            # check if item id exist
            existing_attr = data_table.get_item(Key={schema_name + '_id': event['pathParameters']['id']})
            print(existing_attr)
            if 'Item' not in existing_attr:
                msg = schema_name + ' Id: ' + str(event['pathParameters']['id']) + ' does not exist'
                logger.error('Invocation: %s, ' + msg, logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

            # Check if there is a duplicate [schema]_name
            existing_data = item_validation.scan_dynamodb_data_table(data_table)
            for existing_item in existing_data:
                if schema_name + '_name' in body:
                    if existing_item[schema_name + '_name'].lower() == str(body[schema_name + '_name']).lower() and \
                        existing_item[schema_name + '_id'] != str(event['pathParameters']['id']):
                        msg = schema_name + '_name: ' + body[schema_name + '_name'] + ' already exist'
                        logger.error('Invocation: %s, ' + msg, logging_context)
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': json.dumps({'errors': [msg]})}

            # Get schema object
            schema = {}
            for table_schema in schema_table.scan()['Items']:
                if table_schema['schema_name'] == schema_name:
                    schema = table_schema

            # Merge new attributes with existing one
            for key in body.keys():
                existing_attr['Item'][key] = body[key]
            new_attr = existing_attr
            keys = list(new_attr['Item'].keys())

            # Delete empty keys
            for key in keys:
                if new_attr['Item'][key] == '':
                    del new_attr['Item'][key]
                    continue
                if isinstance(new_attr['Item'][key], list):
                    if len(new_attr['Item'][key]) == 1 and new_attr['Item'][key][0] == '':
                        del new_attr['Item'][key]

            # Validate item against schema attribute requirements
            item_validation_result = item_validation.check_valid_item_create(new_attr['Item'], schema)
            if item_validation_result is not None:
                logger.error('Invocation: %s, Item validation failed: ' + json.dumps(item_validation_result),
                             logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [item_validation_result]})}

            # Update record audit.
            newAudit = {}
            if 'user' in authResponse:
                newAudit['lastModifiedBy'] = authResponse['user']
                newAudit['lastModifiedTimestamp'] = datetime.datetime.utcnow().isoformat()

            if '_history' in new_attr['Item']:
                oldAudit = new_attr['Item']['_history']
                if 'createdTimestamp' in oldAudit:
                    newAudit['createdTimestamp'] = oldAudit['createdTimestamp']
                if 'createdBy' in oldAudit:
                    newAudit['createdBy'] = oldAudit['createdBy']

            new_attr['Item']['_history'] = newAudit
            resp = data_table.put_item(
                Item=new_attr['Item']
            )
            return {'headers': {**default_http_headers},
                    'body': json.dumps(resp)}
        else:
            logger.warning('Invocation: %s, Authorisation failed: ' + json.dumps(authResponse), logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 401,
                    'body': json.dumps({'errors': [authResponse]})}

    elif event['httpMethod'] == 'DELETE':
        auth = MFAuth()
        authResponse = auth.getUserResourceCreationPolicy(event, schema_name)
        if authResponse['action'] == 'allow':
            resp = data_table.get_item(Key={schema_name + '_id': event['pathParameters']['id']})
            if 'Item' in resp:
                respdel = data_table.delete_item(Key={schema_name + '_id': event['pathParameters']['id']})
                if respdel['ResponseMetadata']['HTTPStatusCode'] == 200:
                    logger.info('Invocation: %s, All items successfully deleted.', logging_context)
                    return {'headers': {**default_http_headers},
                            'statusCode': 200, 'body': "Item was successfully deleted."}
                else:
                    logger.error('Invocation: %s, ' + json.dumps(respdel), logging_context)
                    return {'headers': {**default_http_headers},
                            'statusCode': respdel['ResponseMetadata']['HTTPStatusCode'],
                            'body': json.dumps({'errors': [respdel]})}
            else:
                msg = schema_name + ' Id: ' + str(event['pathParameters']['id']) + ' does not exist'
                logger.error('Invocation: %s, ' + msg, logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': [msg]})}
        else:
            logger.error('Invocation: %s, Authorisation failed: ' + json.dumps(authResponse), logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 401,
                    'body': json.dumps({'errors': [authResponse]})}
