#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import simplejson as json
from datetime import datetime, timezone

import cmf_boto
from cmf_utils import cors, default_http_headers
from cmf_logger import logger, log_event_received

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)
policies_table_name = '{}-{}-policies'.format(application, environment)

schema_table = cmf_boto.resource('dynamodb').Table(schema_table_name)
policy_table = cmf_boto.resource('dynamodb').Table(policies_table_name)

CONST_ATTR_LIST_VALUE_VALIDATION_MSG = "Attribute Name: 'List Value' can not be empty"
CONST_ATTR_NAME_VALIDATION_MSG = "Attribute Name: name is required"
CONST_ALLOWED_SCHEMA_TYPES = ["user", "custom"]


def update_administrator_policy(schema_name: str, attributes: list):
    """Add new schema to Administrator policy with full CRUD permissions.
    
    Automatically grants the Administrator policy (policy_id '1') full access to a newly
    created schema. This ensures administrators can manage all schemas without manual
    policy configuration.
    
    Args:
        schema_name (str): Name of the schema to grant access to
        attributes (list): List of schema attributes, each with 'name' field
        
    Note:
        Uses atomic DynamoDB list_append to prevent race conditions when multiple
        schemas are created simultaneously. Fails silently if Administrator policy
        doesn't exist.
    """
    
    # Create new entity access entry
    new_entity = {
        'schema_name': schema_name,
        'create': True,
        'read': True,
        'update': True,
        'delete': True
    }
    
    # Add attributes if schema has them
    if attributes:
        new_entity['attributes'] = [
            {'attr_name': attr['name'], 'attr_type': schema_name}
            for attr in attributes
        ]
    
    # Atomically append to entity_access list
    policy_table.update_item(
        Key={'policy_id': '1'},
        UpdateExpression='SET entity_access = list_append(entity_access, :new_entity)',
        ExpressionAttributeValues={':new_entity': [new_entity]},
        ConditionExpression='attribute_exists(policy_id)'
    )


def update_administrator_policy_attribute(schema_name: str, attr_name: str):
    """Add new attribute to existing schema in Administrator policy.
    
    When attributes are added to existing schemas via PUT requests, this function
    ensures the Administrator policy is updated to include permissions for the
    new attribute.
    
    Args:
        schema_name (str): Name of the schema the attribute belongs to
        attr_name (str): Name of the new attribute to add
        
    Note:
        Uses atomic DynamoDB operations with indexed UpdateExpression to prevent
        race conditions. Handles both cases where attributes list exists or needs
        to be created. Returns silently if schema not found in Administrator policy.
    """
    
    # Convert back to original name for policy lookup
    policy_schema_name = 'application' if schema_name == 'app' else schema_name
    
    # Get current policy to find the schema index
    admin_policy = policy_table.get_item(Key={'policy_id': '1'})
    if 'Item' not in admin_policy:
        return
    
    entity_access = admin_policy['Item']['entity_access']
    
    # Find the schema entry index
    for i, entity in enumerate(entity_access):
        if entity['schema_name'] == policy_schema_name:
            new_attr = {
                'attr_name': attr_name,
                'attr_type': policy_schema_name
            }
            
            # Use atomic list_append to add attribute to the specific schema's attributes
            if 'attributes' in entity:
                # Append to existing attributes list
                policy_table.update_item(
                    Key={'policy_id': '1'},
                    UpdateExpression=f'SET entity_access[{i}].attributes = list_append(entity_access[{i}].attributes, :new_attr)',
                    ExpressionAttributeValues={':new_attr': [new_attr]}
                )
            else:
                # Create new attributes list
                policy_table.update_item(
                    Key={'policy_id': '1'},
                    UpdateExpression=f'SET entity_access[{i}].attributes = :new_attr',
                    ExpressionAttributeValues={':new_attr': [new_attr]}
                )
            break

def lambda_handler(event, _):
    log_event_received(event)

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
            'lastModifiedTimestamp': datetime.now(timezone.utc).isoformat()
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
    # 'schema_name' path parameter must exist otherwise API gateway won't invoke the lambda
    schema_name = event['pathParameters']['schema_name']

    try:
        body = json.loads(event['body'])
    except Exception as _:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'malformed json input'}

    if 'schema_name' in body and body['schema_name'] != schema_name:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'schema_name in body does not match path parameter.'}

    if 'attributes' not in body:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': 'attributes not provided.'}

    schema_type = body.get('schema_type', 'user')
    if schema_type not in CONST_ALLOWED_SCHEMA_TYPES:
        return {'headers': {**default_http_headers},
            'statusCode': 400, 'body': f"Invalid schema_type: {schema_type}. Must be one of {', '.join(CONST_ALLOWED_SCHEMA_TYPES)}"}

    resp = schema_table.get_item(Key={'schema_name': schema_name})
    print(resp)
    if 'Item' in resp:
        return {'headers': {**default_http_headers},
                'statusCode': 400, 'body': schema_name + ' schema already exists.'}

    resp = schema_table.put_item(
        Item={
            'schema_name': schema_name,
            'schema_type': schema_type,
            'friendly_name': body.get('friendly_name'),
            # For all new schema we use ulid
            'key_type': 'ulid',
            'attributes': body['attributes'],
            'lastModifiedTimestamp': datetime.now(timezone.utc).isoformat()
        }

    )
    
    # Auto-grant Administrator permissions for new schema
    try:
        update_administrator_policy(schema_name, body['attributes'])
    except Exception as e:
        logger.warning(f'Failed to update Administrator policy for schema {schema_name}: {e}')
    
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

    schema_type = 'user'
    key_type = None
    friendly_name = None
    attributes = []
    names = []
    resp = schema_table.get_item(Key={'schema_name': schema_name})
    
    if 'Item' in resp:
        attributes = resp['Item']['attributes']
        schema_type = resp['Item']['schema_type']
        if 'key_type' in resp['Item']:
            key_type = resp['Item']['key_type']
        if 'friendly_name' in resp['Item']:
            friendly_name = resp['Item']['friendly_name']

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
    
    item = {
            'schema_name': schema_name,
            'schema_type': schema_type,
            'attributes': attributes,
            'lastModifiedTimestamp': datetime.now(timezone.utc).isoformat()
        }
    if key_type is not None:
        item['key_type'] = key_type
    if friendly_name is not None:
        item['friendly_name'] = friendly_name

    resp = schema_table.put_item(Item=item)
    
    # Update Administrator policy if adding new attribute
    if 'event' in body and body['event'] == 'POST' and 'new' in body:
        try:
            update_administrator_policy_attribute(schema_name, body['new']['name'])
        except Exception as e:
            logger.warning(f'Failed to update Administrator policy for attribute {body["new"]["name"]} in schema {schema_name}: {e}')

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
    update_expression_values = {':dt': datetime.now(timezone.utc).isoformat()}
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
