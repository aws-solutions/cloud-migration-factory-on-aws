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

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)

schema_table = boto3.resource('dynamodb').Table(schema_table_name)

def lambda_handler(event, context):
    print(event)
    if event['httpMethod'] == 'GET':
        resp = schema_table.get_item(Key={'schema_name' : 'server'})
        if 'Item' in resp:
            item = resp['Item']
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(item)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps([])}
    elif event['httpMethod'] == 'POST':
        try:
            body = json.loads(event['body'])
        except:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'malformed json input'}

        resp = schema_table.put_item(

            Item={
                'schema_name': 'server',
                'attributes' : body
            }

        )
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(resp)}

    elif event['httpMethod'] == 'PUT':
        try:
            body = json.loads(event['body'])
            if "server_id" in body:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': "You cannot create server_id schema, this is managed by the system"}
        except:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'malformed json input'}

        attributes = []
        names = []
        resp = schema_table.get_item(Key={'schema_name' : 'server'})
        if 'Item' in resp:
            attributes = resp['Item']['attributes']
        for attr in attributes:
            if 'name' in attr:
                names.append(attr['name'])
        if 'event' in body:
            if body['event'] == 'DELETE':
               if "name" not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: name is required"}
               for attr in attributes:
                   if attr['name'] == body['name']:
                       attributes.remove(attr)
            if body['event'] == 'PUT':
                if "update" not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: update is required"}
                if "name" not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: name is required"}
                if body['update']['type'] is '':
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
                if body['update']['description'] is '':
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
                if body['update']['name'] is '':
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: 'Name' can not be empty"}
                if body['update']['type'] == 'list':
                    if 'listvalue' in body['update']:
                        if body['update']['listvalue'] is '':
                            return {'headers': {'Access-Control-Allow-Origin': '*'},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                    else:
                            return {'headers': {'Access-Control-Allow-Origin': '*'},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                if body['update']['name'] in names and body['name'] != body['update']['name']:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Name: " + body['update']['name'] + " already exist"}
                for attr in attributes:
                   if attr['name'] == body['name']:
                       if body['update']['type'] != 'list':
                          if 'listvalue' in body['update']:
                              del body['update']['listvalue']
                       index = attributes.index(attr)
                       attributes.remove(attr)
                       attributes.insert(index,body['update'])
            if body['event'] == 'POST':
                if "new" not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: new is required"}
                if "name" not in body['new']:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: name is required"}
                if body['new']['name'] in names:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Name: " + body['new']['name'] + " already exist"}
                if body['new']['name'] == "":
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name can not be empty"}
                if 'description' not in body['new']:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
                else:
                    if body['new']['description'] is '':
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': "Attribute Name: 'Description' cannot be empty"}
                if 'type' not in body['new']:
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
                else:
                    if body['new']['type'] is '':
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': "Attribute Name: 'Type' cannot be empty"}
                if body['new']['type'] == 'list':
                    if 'listvalue' in body['new']:
                        if body['new']['listvalue'] is '':
                            return {'headers': {'Access-Control-Allow-Origin': '*'},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                    else:
                            return {'headers': {'Access-Control-Allow-Origin': '*'},
                                    'statusCode': 400, 'body': "Attribute Name: 'List Value' can not be empty"}
                attributes.append(body['new'])
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': "Attribute Name: event is required"}
        resp = schema_table.put_item(

            Item={
                'schema_name': 'server',
                'attributes' : attributes
            }
        )
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(resp)}
