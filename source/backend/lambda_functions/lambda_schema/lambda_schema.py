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
import simplejson as json
import boto3
import datetime
from boto3.dynamodb.conditions import Key, Attr

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

schema_table_name = '{}-{}-schema'.format(application, environment)

schema_table = boto3.resource('dynamodb').Table(schema_table_name)

def lambda_handler(event, context):
    if event['pathParameters'] is None or 'schema_name' not in event['pathParameters']:
        if event['httpMethod'] != 'GET':
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'schema name not provided.'}
        else:
            #This is a request for the schema list, return array of schemas.
            schemas = get_schema_list()
            return {'headers': {**default_http_headers},
                    'body': json.dumps(schemas)}

    schema_name = event['pathParameters']['schema_name']

    if schema_name == 'application':
        schema_name = 'app'

    if event['httpMethod'] == 'GET':
        resp = schema_table.get_item(Key={'schema_name' : schema_name})
        if 'Item' in resp:
            item = resp['Item']
            return {'headers': {**default_http_headers},
                    'body': json.dumps(item)}
        else:
            return {'headers': {**default_http_headers},
                    'body': json.dumps([])}
    elif event['httpMethod'] == 'DELETE':
        resp = schema_table.update_item(
            Item={
              'schema_name': schema_name,
              'schema_type': 'deleted-user',
              'schema_deleted': True,
              'lastModifiedTimestamp': datetime.datetime.utcnow().isoformat()
            }
        )
        if 'Item' in resp:
            item = resp['Item']
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': schema_name + ' schema does not exists.'}

    elif event['httpMethod'] == 'POST':
        try:
            body = json.loads(event['body'])
        except:
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'malformed json input'}

        resp = schema_table.get_item(Key={'schema_name': schema_name})
        if 'Item' in resp:
            item = resp['Item']
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': schema_name + ' schema already exists.'}

        if 'schema_name' not in body:
            return {'headers': {**default_http_headers},
                  'statusCode': 400, 'body': 'schema_name not provided.'}

        if 'attributes' not in body:
            return {'headers': {**default_http_headers},
                  'statusCode': 400, 'body': 'attributes not provided.'}

        resp = schema_table.put_item(

            Item={
                'schema_name': body.schema_name,
                'schema_type': 'user',
                'attributes' : body.attributes,
                'lastModifiedTimestamp': datetime.datetime.utcnow().isoformat()
            }

        )
        return {'headers': {**default_http_headers},
                'body': json.dumps(resp)}

    elif event['httpMethod'] == 'PUT':
        try:
            body = json.loads(event['body'])

        except:
            print(event['body'])
            return {'headers': {**default_http_headers},
                    'statusCode': 400, 'body': 'malformed json input'}

        if 'update_schema' in body: # Check if this is a main schema update and not attribute.
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

            if updates:
                try:
                  resp = schema_table.update_item(
                      Key={'schema_name': schema_name },
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

        if schema_name + '_id' in body:
          return {'headers': {**default_http_headers},
                  'statusCode': 400,
                  'body': "You cannot create " + schema_name + "_id schema, this is managed by the system"}

        attributes = []
        names = []
        resp = schema_table.get_item(Key={'schema_name' : schema_name})
        if 'Item' in resp:
            attributes = resp['Item']['attributes']
        for attr in attributes:
            if 'name' in attr:
                names.append(attr['name'])
        if 'event' in body:
            if body['event'] == 'DELETE':
               if "name" not in body:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name: name is required"}
               for attr in attributes:
                   if attr['name'] == body['name']:
                       attributes.remove(attr)
            if body['event'] == 'PUT':
                if "update" not in body:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name: update is required"}
                if "name" not in body:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name: name is required"}
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
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                    else:
                            return {'headers': {**default_http_headers},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                if body['update']['name'] in names and body['name'] != body['update']['name']:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Name: " + body['update']['name'] + " already exist"}
                for attr in attributes:
                    if attr['name'] == body['name']:
                        if body['update']['type'] != 'list' and body['update']['type'] != 'relationship':
                            if 'listvalue' in body['update']:
                                del body['update']['listvalue']
                        index = attributes.index(attr)
                        attributes.remove(attr)
                        attributes.insert(index, body['update'])
            if body['event'] == 'POST':
                if "new" not in body:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name: new is required"}
                if "name" not in body['new']:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name: name is required"}
                if body['new']['name'] in names:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Name: " + body['new']['name'] + " already exists"}
                if body['new']['name'] == "":
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name can not be empty"}
                if 'description' not in body['new']:
                    return {'headers': {**default_http_headers},
                            'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
                else:
                    if body['new']['description'] == '':
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
                if 'type' not in body['new']:
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
                else:
                    if body['new']['type'] == '':
                        return {'headers': {**default_http_headers},
                                'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
                if body['new']['type'] == 'list':
                    if 'listvalue' in body['new']:
                        if body['new']['listvalue'] == '':
                            return {'headers': {**default_http_headers},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                    else:
                            return {'headers': {**default_http_headers},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                attributes.append(body['new'])
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

def get_schema_list():
    response = schema_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = schema_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])

    schema_list = []
    for schema in scan_data:
        schema_type = 'system'
        if 'schema_type' in schema:
            schema_type = schema['schema_type']
        else:
            schema_type = 'system'

        returnSchema = {
            'schema_name': schema['schema_name'],
            'schema_type': schema_type
        }

        if'friendly_name' in schema:
          returnSchema['friendly_name'] = schema['friendly_name']

        schema_list.append(returnSchema)

    return(schema_list)