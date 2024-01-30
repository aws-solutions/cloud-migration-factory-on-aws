#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import simplejson as json
import datetime

import cmf_boto
from cmf_utils import cors, default_http_headers

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)

schema_table = cmf_boto.resource('dynamodb').Table(schema_table_name)

CONST_ATTR_LIST_VALUE_VALIDATION_MSG = "Attribute Name: 'List Value' can not be empty"
CONST_ATTR_NAME_VALIDATION_MSG = "Attribute Name: name is required"

def lambda_handler(event, _):
    if event['pathParameters'] is None or 'schema_name' not in event['pathParameters']:
        if event['httpMethod'] != 'GET':
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'schema name not provided.'}
        else:
            # This is a request for the schema list, return array of schemas.
            schemas = get_schema_list()
            return {'headers': {**default_http_headers},
                    'body': json.dumps(schemas)}

    schema_name = event['pathParameters']['schema_name']

    if schema_name == 'application':
        schema_name = 'app'

    if event['httpMethod'] == 'GET':
        return handle_get(schema_name)
    elif event['httpMethod'] == 'DELETE':
        return handle_delete(schema_name)
    elif event['httpMethod'] == 'POST':
        return handle_post(event)
    elif event['httpMethod'] == 'PUT':
        return handle_put(event, schema_name)


def get_schema_list():
    response = schema_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = schema_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], ConsistentRead=True)
        scan_data.extend(response['Items'])

    schema_list = []
    for schema in scan_data:
        schema_type = 'system'
        if 'schema_type' in schema:
            schema_type = schema['schema_type']

        return_schema = {
            'schema_name': schema['schema_name'],
            'schema_type': schema_type
        }

        if 'friendly_name' in schema:
            return_schema['friendly_name'] = schema['friendly_name']

        schema_list.append(return_schema)
    return schema_list


def handle_get(schema_name: str):
    resp = schema_table.get_item(Key={'schema_name': schema_name})
    if 'Item' in resp:
        item = resp['Item']
        return {'headers': {**default_http_headers},
                'body': json.dumps(item)}
    else:
        return {'headers': {**default_http_headers},
                'body': json.dumps([])}


def handle_delete(schema_name: str):
    resp = schema_table.put_item(
        Item={
            'schema_name': schema_name,
            'schema_type': 'deleted-user',
            'schema_deleted': True,
            'lastModifiedTimestamp': datetime.datetime.utcnow().isoformat()
        }
    )
    if 'Item' in resp:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': schema_name + ' schema does not exists.'}
    else:
        return {'headers': {**default_http_headers},
                'statusCode': 200,
                'body': json.dumps(resp)}


def handle_post(event: dict):
    try:
        body = json.loads(event['body'])
    except Exception as _:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    if 'schema_name' not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'schema_name not provided.'}

    if 'attributes' not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'attributes not provided.'}

    resp = schema_table.get_item(Key={'schema_name': body['schema_name']})
    print(resp)
    if 'Item' in resp:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': body['schema_name'] + ' schema already exists.'}

    resp = schema_table.put_item(
        Item={
            'schema_name': body['schema_name'],
            'schema_type': 'user',
            'attributes': body['attributes'],
            'lastModifiedTimestamp': datetime.datetime.utcnow().isoformat()
        }

    )
    return {'headers': {**default_http_headers},
            'statusCode': 200,
            'body': json.dumps(resp)}


def handle_put(event: dict, schema_name: str):
    try:
        body = json.loads(event['body'])

    except Exception as e:
        print('Exception:', e)
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    if schema_name + '_id' in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400,
                'body': "You cannot create " + schema_name + "_id schema, this is managed by the system"}

    update_schema_response = process_put_update_schema(body, schema_name)
    if update_schema_response is not None:
        return update_schema_response

    attributes = []
    names = []
    resp = schema_table.get_item(Key={'schema_name': schema_name})
    if 'Item' in resp:
        attributes = resp['Item']['attributes']
    for attr in attributes:
        if 'name' in attr:
            names.append(attr['name'])
    if 'event' in body:
        validation_response = validate_put_payload(body, names)
        if validation_response is not None:
            return validation_response
        prepare_put_attributes(body, attributes)
    else:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: event is required"}
    resp = schema_table.put_item(

        Item={
            'schema_name': schema_name,
            'schema_type': 'user',
            'attributes': attributes,
            'lastModifiedTimestamp': datetime.datetime.utcnow().isoformat()
        }
    )
    return {'headers': {**default_http_headers},
            'body': json.dumps(resp)}


def prepare_put_attributes(body: dict, attributes: list):
    if body['event'] == 'DELETE':
        for attr in attributes:
            if attr['name'] == body['name']:
                attributes.remove(attr)
    if body['event'] == 'PUT':
        prepare_put_put_attributes(body, attributes)
    if body['event'] == 'POST':
        attributes.append(body['new'])


def prepare_put_put_attributes(body: dict, attributes: list):
    for attr in attributes:
        if attr['name'] == body['name']:
            if body['update']['type'] != 'list' and body['update']['type'] != 'relationship':
                if 'listvalue' in body['update']:
                    del body['update']['listvalue']
            index = attributes.index(attr)
            attributes.remove(attr)
            attributes.insert(index, body['update'])


def process_put_update_schema(body: dict, schema_name: str):
    if 'update_schema' in body:  # Check if this is a main schema update and not attribute.
        updates, update_expression_values, update_expresssion_set, update_expresssion_remove = \
            get_updates_for_put_update_schema(body)
        if updates:
            try:
                resp = schema_table.update_item(
                    Key={'schema_name': schema_name},
                    UpdateExpression=update_expresssion_set + update_expresssion_remove,
                    ExpressionAttributeValues=update_expression_values,
                    ReturnValues='UPDATED_NEW'
                )
            except Exception as e:
                print(e)
                print(update_expresssion_set + update_expresssion_remove)
                return {'headers': {**default_http_headers},
                        'statusCode': 400,
                        'body': str(e)}

            if 'Attributes' in resp:
                return {'headers': {**default_http_headers},
                        'body': json.dumps(resp)}
            else:
                return {'headers': {**default_http_headers},
                        'statusCode': 400,
                        'body': "Error updating schema."}
        else:
            return {'headers': {**default_http_headers},
                    'body': 'No updates provided.'}

    return None


def get_updates_for_put_update_schema(body: dict):
    updates = False
    update_expression_values = {':dt': datetime.datetime.utcnow().isoformat()}
    update_expresssion_set = 'SET lastModifiedTimestamp =:dt'
    update_expresssion_remove = ''

    if 'friendly_name' in body['update_schema']:
        updates = True
        if body['update_schema']['friendly_name'] == '':
            update_expresssion_remove += ' REMOVE friendly_name'
        else:
            update_expresssion_set += ', friendly_name=:fn'
            update_expression_values[':fn'] = body['update_schema']['friendly_name']

    if 'help_content' in body['update_schema']:
        updates = True
        update_expresssion_set += ', help_content=:hchtml'
        update_expression_values[':hchtml'] = body['update_schema']['help_content']

    return updates, update_expression_values, update_expresssion_set, update_expresssion_remove


def validate_put_payload(body: dict, names: list[str]):
    if body['event'] == 'DELETE' and "name" not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': CONST_ATTR_NAME_VALIDATION_MSG}
    elif body['event'] == 'PUT':
        return validate_put_put_payload(body, names)
    elif body['event'] == 'POST':
        return validate_put_post_payload(body, names)
    return None


def validate_put_put_payload(body: dict, names: list[str]):
    if "update" not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: update is required"}
    if "name" not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': CONST_ATTR_NAME_VALIDATION_MSG}
    if body['update']['type'] == '':
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
    if body['update']['description'] == '':
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
    if body['update']['name'] == '':
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: 'Name' can not be empty"}
    if body['update']['type'] == 'list':
        if 'listvalue' in body['update']:
            if body['update']['listvalue'] == '':
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': CONST_ATTR_LIST_VALUE_VALIDATION_MSG}
        else:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': CONST_ATTR_LIST_VALUE_VALIDATION_MSG}
    if body['update']['name'] in names and body['name'] != body['update']['name']:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Name: " + body['update']['name'] + " already exist"}


def validate_put_post_payload(body: dict, names: list[str]):
    if "new" not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: new is required"}
    if "name" not in body['new']:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': CONST_ATTR_NAME_VALIDATION_MSG}
    if body['new']['name'] in names:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Name: " + body['new']['name'] + " already exists"}
    if body['new']['name'] == "":
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name can not be empty"}
    if 'description' not in body['new'] or body['new']['description'] == '':
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
    if 'type' not in body['new'] or body['new']['type'] == '':
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
    if body['new']['type'] == 'list':
        if 'listvalue' in body['new']:
            if body['new']['listvalue'] == '':
                return {'headers': {**default_http_headers},
                        'statusCode': 400, 'body': CONST_ATTR_LIST_VALUE_VALIDATION_MSG}
        else:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': CONST_ATTR_LIST_VALUE_VALIDATION_MSG}
