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

stages_table = boto3.resource('dynamodb').Table(stages_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)

def lambda_handler(event, context):
    print(event)
    if event['httpMethod'] == 'GET':
        resp =  stages_table.get_item(Key={'stage_id': event['pathParameters']['stage_id']})
        if 'Item' in resp:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(resp['Item'])}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'stage Id: ' + str(event['pathParameters']['stage_id']) + ' does not exist'}

    elif event['httpMethod'] == 'PUT':
        stage_id = event['pathParameters']['stage_id']
        stage_name = ""
        # check if stage_id exist in stage_table
        stage = stages_table.get_item(Key={'stage_id': event['pathParameters']['stage_id']})
        if 'Item' not in stage:
            return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'stage Id: ' + str(event['pathParameters']['stage_id']) + ' does not exist'}
        try:
            body = json.loads(event['body'])
            if 'attributes' not in body:
                 return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'attribute attributes is required'}
            for item in body['attributes']:
              if 'attr_name' not in item:
                 return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'attribute attr_name is required'}
        except:
            return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'malformed json input'}

        # Check if there is a duplicate stage_name
        stages = stages_table.scan()
        for s in stages['Items']:
            if 'stage_name' in body:
                if s['stage_name'].lower() == str(body['stage_name']).lower() and s['stage_id'] != str(event['pathParameters']['stage_id']):
                    return {'headers': {'Access-Control-Allow-Origin': '*'}, 'statusCode': 400, 'body': 'stage_name: ' +  body['stage_name'] + ' already exist'}
                stage_name = body['stage_name']
            else:
                stage_name = stage['Item']['stage_name']

        # Get schema defination
        server_attributes = []
        app_attributes = []
        for schema in schema_table.scan()['Items']:
                if schema['schema_name'] == "app":
                    for attribute in schema['attributes']:
                        app_attributes.append(attribute['name'])
                elif schema['schema_name'] == "server":
                    for attribute in schema['attributes']:
                        server_attributes.append(attribute['name'])
        print(server_attributes)
        print(app_attributes)

        # Get attribute name in request body
        attributes = []
        for item in body['attributes']:
            if item['attr_name'] in app_attributes:
               item['attr_type'] = "app"
            elif item['attr_name'] in server_attributes:
               item['attr_type'] = "server"
            else:
               message = 'Attribute Name: ' + item['attr_name'] + " is not defined in schema"
               return {'headers': {'Access-Control-Allow-Origin': '*'},'statusCode': 400, 'body': message}
            attributes.append(item['attr_name'])

        resp = stages_table.put_item(

            Item={
                'stage_id'  : stage_id,
                'attributes' : body['attributes'],
                'stage_name' : stage_name
            }

        )
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 200, 'body': json.dumps(resp)}

    elif event['httpMethod'] == 'DELETE':
        stage_id = ""
        stages = stages_table.scan()
        for stage in stages['Items']:
            if str(stage['stage_id']) == str(event['pathParameters']['stage_id']):
                stage_id = stage['stage_id']
        if stage_id != "":
            delete = stages_table.delete_item(Key={'stage_id': stage_id})
            if delete['ResponseMetadata']['HTTPStatusCode'] == 200:
               return {'headers': {'Access-Control-Allow-Origin': '*'},
                       'statusCode': 200, 'body': "stage: " + stage_id + " was successfully deleted"}
            else:
               return {'headers': {'Access-Control-Allow-Origin': '*'},'statusCode': resp['ResponseMetadata']['HTTPStatusCode'], 'body': json.dumps(resp)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},'statusCode': 400, 'body': 'stage Id: ' + str(event['pathParameters']['stage_id']) + ' does not exist'}
