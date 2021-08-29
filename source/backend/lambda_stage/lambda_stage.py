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

stages_table_name = '{}-{}-stage'.format(application, environment)
schema_table_name = '{}-{}-schema'.format(application, environment)

stage_table = boto3.resource('dynamodb').Table(stages_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)

def lambda_handler(event, context):
    print(event)
    if event['httpMethod'] == 'GET':
        resp = stage_table.scan()
        item = resp['Items']
        newitem = sorted(item, key = lambda i: i['stage_id'])
        return {
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(newitem)
        }

    elif event['httpMethod'] == 'POST':
        try:
            body = json.loads(event['body'])
            if 'stage_name' not in body:
               return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'attribute stage_name is required'}
        except:
            return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'malformed json input'}

        attributes = []
        if 'attributes' in body:
            attributes = body['attributes']
        itemlist = stage_table.scan()
        for item in itemlist['Items']:
            if body['stage_name'] in item['stage_name']:
                return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'stage_name: ' + body['stage_name'] + ' already exist'}
        # Get vacant stage_id
        ids = []
        for item in itemlist['Items']:
            ids.append(int(item['stage_id']))
        ids.sort()
        stage_id = 1
        for id in ids:
           if stage_id == id:
               stage_id += 1

        # Check if attribute exist in schema
        if 'attributes' in body:
            # Get schema defination
            server_attributes = []
            app_attributes = []
            wave_attributes = []
            for schema in schema_table.scan()['Items']:
                    if schema['schema_name'] == "app":
                        for attribute in schema['attributes']:
                            app_attributes.append(attribute['name'])
                    elif schema['schema_name'] == "server":
                        for attribute in schema['attributes']:
                            server_attributes.append(attribute['name'])
                    elif schema['schema_name'] == "wave":
                        for attribute in schema['attributes']:
                            wave_attributes.append(attribute['name'])
            print("*** Server Attributes: ***")
            print(server_attributes)
            print("*** App Attributes: ***")
            print(app_attributes)
            print("*** Wave Attributes: ***")
            print(wave_attributes)

            # Check if attribute is in schema
            attrs = []
            for item in body['attributes']:
                if item['attr_name'] in app_attributes:
                    item['attr_type'] = "app"
                elif item['attr_name'] in server_attributes:
                    item['attr_type'] = "server"
                elif item['attr_name'] in wave_attributes:
                    item['attr_type'] = "wave"
                else:
                    message = 'Attribute Name: ' + item['attr_name'] + " is not defined in schema"
                    return {'headers': {'Access-Control-Allow-Origin': '*'},'statusCode': 400, 'body': message}
                attrs.append(item['attr_name'])

        # Update stage item
        if len(attributes) == 0:
            resp = stage_table.put_item(
                Item={
                    'stage_name': body['stage_name'],
                    'stage_id': str(stage_id)
                }
            )
        else:
            resp = stage_table.put_item(
                Item={
                    'stage_name': body['stage_name'],
                    'stage_id': str(stage_id),
                    'attributes': attributes
                }
            )

        resp =  stage_table.get_item(Key={'stage_id': str(stage_id)})
        if 'Item' in resp:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(resp['Item'])}
