#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json
from time import sleep
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
            logger.error(msg)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msg}

    else:
        logger.error('No schema provided.')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'No schema provided to function.'}

    data_table_name = '{}-{}-'.format(application, environment) + schema_name + 's'
    data_table = boto3.resource('dynamodb').Table(data_table_name)

    if event['httpMethod'] == 'GET':
        item = item_validation.scan_dynamodb_data_table(data_table)
        newitem = sorted(item, key=lambda i: i[schema_name + '_name'])
        return {'headers': {**default_http_headers},
                'body': json.dumps(newitem)}

    elif event['httpMethod'] == 'POST':
        auth = MFAuth()
        authResponse = auth.getUserResourceCreationPolicy(event, schema_name)
        if authResponse['action'] == 'allow':
            try:
                body = json.loads(event['body'])

            except Exception as e:
                logger.error('Invocation: %s, ' + json.dumps(e))
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': json.dumps({'errors': ['malformed json input']})}
            if type(body) is dict:
                # convert to list and process.
                logger.debug('Invocation: %s, DICT provided, converting to single item list.', logging_context)
                single_item_list = []
                single_item_list.append(body)
                body = single_item_list

            logger.info('Invocation: %s, Starting PUT of ' + str(len(body)) + ' items.', logging_context)
            try:
                for record in body:
                    logger.debug('Invocation: %s, Checking ' + schema_name + '_name exists.', logging_context)
                    if schema_name + '_name' not in record:
                        logger.error('Invocation: %s, attribute ' + schema_name + '_name is required', logging_context)
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': 'attribute ' + schema_name + '_name is required'}
                    logger.debug('Invocation: %s, Checking ' + schema_name + '_id does not exist.', logging_context)
                    if schema_name + '_id' in record:
                        logger.error('Invocation: %s, You cannot create ' + schema_name +
                                     '_id, this is managed by the system', logging_context)
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': "You cannot create " + schema_name +
                                                           "_id, this is managed by the system"}

                # Get Data table content
                existing_itemlist = item_validation.scan_dynamodb_data_table(data_table)

                # Create record audit.
                newAudit = {}
                if 'user' in authResponse:
                    newAudit['createdBy'] = authResponse['user']
                    newAudit['createdTimestamp'] = datetime.datetime.utcnow().isoformat()

                # multiple items processing
                client_ddb = boto3.client('dynamodb')
                # get related data for validation
                related_data = item_validation.get_relationship_data(body, schema)

                # Get vacant {schema}_id
                item_id = get_vacant_id(existing_itemlist, schema_name)
                item_name_list = []
                item_name_duplicates = []
                item_name_exists = []

                items_validation_errors = []
                items_validated = []
                # Validate records before putRequest.
                for item in body:
                    is_valid = True
                    # Check if the record already exists.
                    if item_validation.does_item_exist(schema_name + '_name', item[schema_name + '_name'],
                                                       existing_itemlist):
                        item_name_exists.append(item[schema_name + '_name'])
                        is_valid = False

                    # Validate record
                    item_validation_result = item_validation.check_valid_item_create(item, schema, related_data)
                    if item_validation_result is not None:
                        items_validation_errors.append({item[schema_name + '_name']: item_validation_result})
                        is_valid = False

                    # Check if _name is duplicated in the list passed.
                    if item[schema_name + '_name'] not in item_name_list:
                        item_name_list.append(item[schema_name + '_name'])
                    else:
                        item_name_duplicates.append(item[schema_name + '_name'])
                        is_valid = False

                    if is_valid:
                        item[schema_name + '_id'] = str(item_id)
                        item_id += 1
                        # Add audit data to new item.
                        item['_history'] = newAudit
                        # Add item to be processed.
                        items_validated.append(item)

                # Update DynamoDB
                from boto3.dynamodb.types import TypeSerializer
                ts = TypeSerializer()
                responses = []

                logger.debug('Invocation: %s, Validated items to process: ' + json.dumps(items_validated),
                             logging_context)

                # if there are valid items then process them only.
                if items_validated:
                    start_indx = 0

                    logger.info('Invocation: %s, Number of valid items to process: ' + str(len(items_validated)),
                                logging_context)
                    while True:
                        itemlist = get_items(items_validated, start_indx, 25)
                        table_content = []
                        for item in itemlist:
                            putrequest = {}
                            putrequest['PutRequest'] = {'Item': ts.serialize(item)['M']}
                            table_content.append(putrequest)
                        resp = client_ddb.batch_write_item(
                            RequestItems={data_table_name: table_content}
                        )
                        if len(resp['UnprocessedItems']) == 0:
                            logger.debug('Invocation: %s, Successfully wrote ' + str(len(itemlist)) + ' items',
                                         logging_context)
                        else:
                            # Hit the provisioned write limit
                            logger.info('Invocation: %s, Hit write limit, backing off then retrying', logging_context)
                            sleep(5)

                            # Items left over that haven't been inserted
                            unprocessed_items = resp['UnprocessedItems']
                            logger.debug('Invocation: %s, Resubmitting items', logging_context)
                            # Loop until unprocessed items are written
                            while len(unprocessed_items) > 0:
                                resp = client_ddb.batch_write_item(
                                    RequestItems=unprocessed_items
                                )
                                # If any items are still left over, add them to the
                                # list to be written
                                unprocessed_items = resp['UnprocessedItems']

                                # If there are items left over, we could do with
                                # sleeping some more
                                if len(unprocessed_items) > 0:
                                    sleep(5)
                            break

                        responses.append(resp)
                        new_start_indx = start_indx + 25
                        max_indx = len(items_validated) - 1
                        if (max_indx >= new_start_indx):
                            start_indx += 25
                        else:
                            break

                return_messages = {}
                has_errors = False
                # If validation errors were found then report the list to calling function.
                if items_validation_errors:
                    logger.warning(
                        'Invocation: %s, Items with validation errors: ' + json.dumps(items_validation_errors),
                        logging_context)
                    return_messages['validation_errors'] = items_validation_errors
                    has_errors = True

                # If duplicate names were found report the list
                if item_name_duplicates:
                    return_messages['duplicate_name'] = item_name_duplicates
                    has_errors = True

                if item_name_exists:
                    return_messages['existing_name'] = item_name_exists
                    has_errors = True

                # Check responses for all chunks
                unprocessed_items = []
                for response in responses:
                    if (response['ResponseMetadata']['HTTPStatusCode'] != 200):
                        if 'UnprocessedItems' in response:
                            if 'PutRequest' in response['UnprocessedItems']:
                                unprocessed_items.append(response['UnprocessedItems']['PutRequest'])
                                has_errors = True

                # add unprocessed items to return messages.
                if unprocessed_items:
                    return_messages['unprocessed_items'] = unprocessed_items

                if has_errors:
                    logger.warning(
                        'Invocation: %s, ' + json.dumps({'newItems': items_validated, 'errors': return_messages}),
                        logging_context)
                    return {'headers': {**default_http_headers},
                            'body': json.dumps({'newItems': items_validated, 'errors': return_messages})}
                else:
                    logger.info('Invocation: %s, All items successfully put in table.', logging_context)
                    logger.debug('Invocation: %s, ' + json.dumps({'newItems': items_validated}), logging_context)
                    return {'headers': {**default_http_headers},
                            'body': json.dumps({'newItems': items_validated})}
            except Exception as e:
                logger.error('Invocation: %s, Unhandled exception: ' + str(e), logging_context)
                return {'headers': {**default_http_headers},
                        'statusCode': 500,
                        'body': json.dumps(
                            {'errors': ['Unhandled API Exception: check logs for detailed error message.']})}

        else:
            logger.error('Invocation: %s, Authorisation failed: ' + json.dumps(authResponse), logging_context)
            return {'headers': {**default_http_headers},
                    'statusCode': 401,
                    'body': json.dumps({'errors': [authResponse]})}


def get_items(items, start_indx, num_items):
    result = []
    max_indx = len(items) - 1
    end_indx = start_indx + num_items
    if end_indx > max_indx:
        # Not enough items to get requested num_items.
        end_indx = max_indx + 1
    for i in range(start_indx, end_indx):
        result.append(items[i])
    return result


def get_vacant_id(existing_itemlist, schema_name):
    ids = []
    for item in existing_itemlist:
        ids.append(int(item[schema_name + '_id']))
    ids.sort()
    if ids:
        # Get highest id from existing records
        item_id = ids[-1]
        # Increment by 1
        item_id += 1
    else:
        # No existing record id allocated, start at 1
        item_id = 1
    return item_id
