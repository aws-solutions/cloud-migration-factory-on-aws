#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import json
from time import sleep
from boto3.dynamodb.types import TypeSerializer
import datetime
from policy import MFAuth
import item_validation
from typing import Any

import cmf_boto
from cmf_logger import logger
from cmf_utils import cors, default_http_headers

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)
schema_table = cmf_boto.resource('dynamodb').Table(schema_table_name)
client_ddb = cmf_boto.client('dynamodb')
PREFIX_INVOCATION = 'Invocation:'


def lambda_handler(event, _):
    logging_context = ''

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
            logger.error(msg)
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': msg}

    else:
        logger.error('No schema provided.')
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'No schema provided to function.'}

    data_table_name = '{}-{}-'.format(application, environment) + schema_name + 's'
    data_table = cmf_boto.resource('dynamodb').Table(data_table_name)

    if event['httpMethod'] == 'GET':
        return process_get(data_table, schema_name)
    elif event['httpMethod'] == 'POST':
        return process_post(event, data_table, data_table_name, schema, schema_name, logging_context)


def get_items(items: list, start_indx: int, num_items: int):
    result = []
    max_indx = len(items) - 1
    end_indx = start_indx + num_items
    if end_indx > max_indx:
        # Not enough items to get requested num_items.
        end_indx = max_indx + 1
    for i in range(start_indx, end_indx):
        result.append(items[i])
    return result


def get_vacant_id(existing_items_list: list, schema_name: str):
    ids = []
    for item in existing_items_list:
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


def process_get(data_table: Any, schema_name: str):
    item = item_validation.scan_dynamodb_data_table(data_table)
    new_item = sorted(item, key=lambda i: i[schema_name + '_name'])
    return {'headers': {**default_http_headers},
            'body': json.dumps(new_item)}


def process_post(event: dict, data_table: Any, data_table_name: str, schema, schema_name: str, logging_context: str):
    auth = MFAuth()
    auth_response = auth.get_user_resource_creation_policy(event, schema_name)
    if auth_response['action'] == 'allow':
        try:
            body = json.loads(event['body'])

        except Exception as e:
            logger.error(f'{PREFIX_INVOCATION} {logging_context} {str(e)}')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': json.dumps({'errors': ['malformed json input']})}
        if type(body) is dict:
            # convert to list and process.
            logger.debug(f'{PREFIX_INVOCATION} {logging_context}, DICT provided, converting to single item list.')
            single_item_list = [body]
            body = single_item_list

        logger.info(f'{PREFIX_INVOCATION} {logging_context}, Starting PUT of {str(len(body))}  items.')
        try:
            return process_authorized_post(body, data_table, data_table_name, schema_name, schema,
                                           auth_response, logging_context)
        except Exception as e:
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, Unhandled exception: {str(e)}')
            return {'headers': {**default_http_headers},
                    'statusCode': 500,
                    'body': json.dumps(
                        {'errors': ['Unhandled API Exception: check logs for detailed error message.']})}

    else:
        logger.error(f'{PREFIX_INVOCATION} {logging_context}, Authorisation failed: {json.dumps(auth_response)}')
        return {'headers': {**default_http_headers},
                'statusCode': 401,
                'body': json.dumps({'errors': [auth_response]})}


def process_authorized_post(body: dict, data_table: Any, data_table_name: str, schema_name: str, schema: dict,
                            auth_response: dict, logging_context: str):
    response = validate_records_in_payload(body, schema_name, logging_context)
    if response is not None:
        return response

    # Get Data table content
    existing_items_list = item_validation.scan_dynamodb_data_table(data_table)

    # Create record audit.
    new_audit = {}
    if 'user' in auth_response:
        new_audit['createdBy'] = auth_response['user']
        new_audit['createdTimestamp'] = datetime.datetime.utcnow().isoformat()

    # multiple items processing
    # get related data for validation
    related_data = item_validation.get_relationship_data(body, schema)

    # Get vacant {schema}_id
    item_id = get_vacant_id(existing_items_list, schema_name)

    # Validate records before putRequest.
    _, item_name_duplicates, item_name_exists, items_validation_errors, items_validated = \
        get_validated_items(body, schema_name, schema, related_data, existing_items_list, item_id, new_audit)

    responses = []
    logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Validated items to process: '
                 f'{json.dumps(items_validated)}')
    # if there are valid items then process them only.
    if items_validated:
        save_validated_items(items_validated, data_table_name, responses, logging_context)

    has_errors, return_messages = check_for_errors(items_validation_errors, item_name_duplicates,
                                                   item_name_exists, responses, logging_context)

    if has_errors:
        logger.warning(f'{PREFIX_INVOCATION} {logging_context}, '
                       f'{json.dumps({"newItems": items_validated, "errors": return_messages})}')
        return {'headers': {**default_http_headers},
                'body': json.dumps({'newItems': items_validated, 'errors': return_messages})}
    else:
        logger.info(f'{PREFIX_INVOCATION} {logging_context}, All items successfully put in table.')
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, {json.dumps({"newItems": items_validated})}')
        return {'headers': {**default_http_headers},
                'body': json.dumps({'newItems': items_validated})}


def save_validated_items(items_validated: list, data_table_name: str, responses: list, logging_context: str):
    ts = TypeSerializer()
    start_indx = 0
    logger.info(f'{PREFIX_INVOCATION} {logging_context}, Number of valid items to process: '
                f'{str(len(items_validated))}')
    while True:
        item_list = get_items(items_validated, start_indx, 25)
        table_content = []
        for item in item_list:
            put_request = {'PutRequest': {'Item': ts.serialize(item)['M']}}
            table_content.append(put_request)
        resp = client_ddb.batch_write_item(
            RequestItems={data_table_name: table_content}
        )
        resp = retry_unprocessed_items(resp, item_list, logging_context)
        responses.append(resp)
        new_start_indx = start_indx + 25
        max_indx = len(items_validated) - 1
        if max_indx >= new_start_indx:
            start_indx += 25
        else:
            break


def retry_unprocessed_items(resp: dict, item_list: list, logging_context: str):
    if len(resp['UnprocessedItems']) == 0:
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Successfully wrote '
                     f'{str(len(item_list))} items')
    else:
        # Hit the provisioned write limit
        logger.info(f'{PREFIX_INVOCATION} {logging_context}, '
                    f'Hit write limit, backing off then retrying')
        sleep(5)

        # Items left over that haven't been inserted
        unprocessed_items = resp['UnprocessedItems']
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Resubmitting items')
        # Loop until unprocessed items are written
        # TODO //NOSONAR
        # inifinite loop warning if there are unexpected errors from the batch write api
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/client/batch_write_item.html
        # check the comments in the function check_for_errors
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
    return resp


def validate_records_in_payload(body, schema_name, logging_context):
    for record in body:
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Checking {schema_name}_name exists.')
        if schema_name + '_name' not in record:
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, attribute {schema_name}_name is required')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'attribute ' + schema_name + '_name is required'}
        logger.debug(f'{PREFIX_INVOCATION} {logging_context}, Checking {schema_name}_id exists.')
        if schema_name + '_id' in record:
            logger.error(f'{PREFIX_INVOCATION} {logging_context}, You cannot create {schema_name}'
                         f'_id, this is managed by the system')
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': "You cannot create " + schema_name +
                                               "_id, this is managed by the system"}


def get_validated_items(body, schema_name, schema, related_data, existing_item_list, item_id, new_audit) -> \
        (dict, dict, dict, dict):
    item_name_list = []
    item_name_duplicates = []
    item_name_exists = []
    items_validation_errors = []
    items_validated = []
    for item in body:
        is_valid = True
        # Check if the record already exists.
        if item_validation.does_item_exist(schema_name + '_name', item[schema_name + '_name'],
                                           existing_item_list):
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
            item['_history'] = new_audit
            # Add item to be processed.
            items_validated.append(item)

    return item_name_list, item_name_duplicates, item_name_exists, items_validation_errors, items_validated


def check_for_errors(items_validation_errors: list, item_name_duplicates: list, item_name_exists: list, responses: list,
                     logging_context: str) -> (bool, dict):
    return_messages = {}
    has_errors = False
    # If validation errors were found then report the list to calling function.
    if items_validation_errors:
        logger.warning(
            'Invocation: %s, Items with validation errors: ' + json.dumps(items_validation_errors),
            logging_context)
        logger.warning(f'{PREFIX_INVOCATION} {logging_context}, Items with validation errors: '
                       f'{json.dumps(items_validation_errors)}')
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
    # TODO //NOSONAR
    # this is unreachable because the loop while len(unprocessed_items) > 0: doesn't exit
    # until all the items are put
    # it could theoretically be an infinite loop
    # implementing exponential backoff or at least adding max number of re-tries and having this check makes sense
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

    return has_errors, return_messages


