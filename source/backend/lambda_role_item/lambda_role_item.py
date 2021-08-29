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
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr

application = os.environ['application']
environment = os.environ['environment']

roles_table_name = '{}-{}-roles'.format(application, environment)
stage_table_name = '{}-{}-stage'.format(application, environment)

role_table = boto3.resource('dynamodb').Table(roles_table_name)
stage_table = boto3.resource('dynamodb').Table(stage_table_name)

def lambda_handler(event, context):
    print(event)
    if event['httpMethod'] == 'GET':
        resp = role_table.get_item(Key={'role_id': event['pathParameters']['role_id']})
        if 'Item' in resp:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(resp['Item'])}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'role Id: ' + str(event['pathParameters']['role_id']) + ' does not exist'}
    elif event['httpMethod'] == 'PUT':
        try:
            body = json.loads(event['body'])
            if "role_id" in body:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': "You cannot modify role_id, this is managed by the system"}
            if 'stages' not in body:
               return {'statusCode': 400, 'body': 'attribute stages is required'}
            for item in body['stages']:
               if 'stage_id' not in item:
                   return {'statusCode': 400, 'body': 'attribute stage_id is required'}
            if 'role_name' not in body:
               return {'statusCode': 400, 'body': 'attribute role_name is required'}
            if 'groups' not in body:
               return {'statusCode': 400, 'body': 'attribute groups is required'}
            for item in body['groups']:
               if 'group_name' not in item:
                   return {'statusCode': 400, 'body': 'attribute group_name is required'}
        except:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'malformed json input'}

       # Check if role id exist
        resp = role_table.get_item(Key={'role_id': event['pathParameters']['role_id']})
        if 'Item' not in resp:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'role Id: ' + str(event['pathParameters']['role_id']) + ' does not exist'}

       # Check if stage id exist
        stageids = []
        stages = stage_table.scan()['Items']
        for stage in stages:
            stageids.append(stage['stage_id'])
        check = True
        for item in body['stages']:
            if item['stage_id'] not in stageids:
                check = False
        if check == False:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': 'One or more stage_id in ' + str(body['stages']) + ' does not exist'}

        # Check if there is a duplicate role_name
        roles = role_table.scan()
        for role in roles['Items']:
            if 'role_name' in body:
                if role['role_name'].lower() == str(body['role_name']).lower() and role['role_id'] != str(event['pathParameters']['role_id']):
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'role_name: ' +  body['role_name'] + ' already exist'}

       # Updating existing role
        resp = role_table.put_item(
            Item={
                'role_id' : event['pathParameters']['role_id'],
                'role_name': body['role_name'],
                'stages': body['stages'],
                'groups' : body['groups']
            }
        )
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(resp)}

    elif event['httpMethod'] == 'DELETE':
        resp = role_table.get_item(Key={'role_id': event['pathParameters']['role_id']})
        if 'Item' in resp:
            respdel = role_table.delete_item(Key={'role_id': event['pathParameters']['role_id']})
            if respdel['ResponseMetadata']['HTTPStatusCode'] == 200:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 200, 'body': "Role " + str(resp['Item']) + " was successfully deleted"}
            else:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': respdel['ResponseMetadata']['HTTPStatusCode'], 'body': json.dumps(respdel)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'role Id: ' + str(event['pathParameters']['role_id']) + ' does not exist'}
