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
from policy import MFAuth

application = os.environ['application']
environment = os.environ['environment']

waves_table_name = '{}-{}-waves'.format(application, environment)

waves_table = boto3.resource('dynamodb').Table(waves_table_name)

def lambda_handler(event, context):

    if event['httpMethod'] == 'GET':
        resp = waves_table.scan()
        item = resp['Items']
        newitem = sorted(item, key = lambda i: i['wave_id'])
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(newitem)}

    elif event['httpMethod'] == 'POST':
        auth = MFAuth()
        authResponse = auth.getUserResourceCrationPolicy(event)
        if authResponse['action'] == 'allow':
            try:
                body = json.loads(event['body'])
                if 'wave_name' not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'attribute wave_name is required'}
            except Exception as e:
                print(e)
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'malformed json input'}

            # Check if there is a duplicate wave_name
            itemlist = waves_table.scan()
            for item in itemlist['Items']:
                if body['wave_name'] in item['wave_name']:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'wave_name: ' +  body['wave_name'] + ' already exist'}

            # Get vacant wave_id
            ids = []
            for item in itemlist['Items']:
                ids.append(int(item['wave_id']))
            ids.sort()
            wave_id = 1
            for id in ids:
               if wave_id == id:
                  wave_id += 1
            body['wave_id'] = str(wave_id)

            # Update item
            resp = waves_table.put_item(
            Item=body
            )
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(resp)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}
