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

servers_table_name = '{}-{}-servers'.format(application, environment)
schema_table_name = '{}-{}-schema'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)

servers_table = boto3.resource('dynamodb').Table(servers_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)
apps_table = boto3.resource('dynamodb').Table(apps_table_name)

def lambda_handler(event, context):

    if event['httpMethod'] == 'GET':
        resp = servers_table.scan()
        item = resp['Items']
        newitem = sorted(item, key = lambda i: i['server_name'])
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(newitem)}

    elif event['httpMethod'] == 'POST':
        auth = MFAuth()
        authResponse = auth.getUserResourceCrationPolicy(event)
        if authResponse['action'] == 'allow':
            try:
                body = json.loads(event['body'])
                if 'server_name' not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'attribute server_name is required'}
                if 'app_id' not in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'attribute app_id is required'}
                if 'server_id' in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "You cannot create server_id, this is managed by the system"}

                # Check if attribute is defined in the Server schema
                server_attributes = []
                for server_schema in schema_table.scan()['Items']:
                    if server_schema['schema_name'] == "server":
                        server_attributes = server_schema['attributes']
                for key in body.keys():
                    check = False
                    for attribute in server_attributes:
                        if key == attribute['name']:
                           check = True
                    if check == False:
                        message = "Server attribute: " + key + " is not defined in the Server schema"
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': message}

                # Check if attribute in the body matches the list value defined in schema
                for attribute in server_attributes:
                    if 'listvalue' in attribute:
                        listvalue = attribute['listvalue'].split(',')
                        for key in body.keys():
                            if key == attribute['name']:
                                if body[key] not in listvalue:
                                    message = "Server attribute " + key + " for server " + body['server_name'] + " is '" + body[key] + "', does not match the list values '" + attribute['listvalue'] + "' defined in the Server schema"
                                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                                            'statusCode': 400, 'body': message}
            except Exception as e:
                print(e)
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'malformed json input'}

            # Check if there is a duplicate server_name
            itemlist = servers_table.scan()
            for item in itemlist['Items']:
                if body['server_name'] in item['server_name']:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'server_name: ' +  body['server_name'] + ' already exist'}

            # Validate App_id
            apps = apps_table.scan()
            check = False
            for app in apps['Items']:
               if app['app_id'] == str(body['app_id']):
                   check = True
            if check == False:
                 message = 'app Id: ' + body['app_id'] + ' does not exist'
                 return {'headers': {'Access-Control-Allow-Origin': '*'},
                         'statusCode': 400, 'body': message}

            # Get vacant server_id
            ids = []
            for item in itemlist['Items']:
                ids.append(int(item['server_id']))
            ids.sort()
            server_id = 1
            for id in ids:
               if server_id == id:
                  server_id += 1
            body['server_id'] = str(server_id)

            # Update item
            resp = servers_table.put_item(
            Item=body
            )
            if (resp['ResponseMetadata']['HTTPStatusCode'] == 200):
                new_item = {}
                items = servers_table.scan()['Items']
                for item in items:
                    if str(item['server_id']) == str(server_id):
                        new_item = item
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(new_item)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}
