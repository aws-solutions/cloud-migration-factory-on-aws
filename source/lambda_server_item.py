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
        if 'appid' in event['pathParameters']:
            resp = servers_table.query(
                    IndexName='app_id-index',
                    KeyConditionExpression=Key('app_id').eq(event['pathParameters']['appid'])
                )
            if resp['Count'] is not 0:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps(resp['Items'])}
            else:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'App Id: ' + str(event['pathParameters']['appid']) + ' does not exist'}
        elif 'serverid' in event['pathParameters']:
            resp = servers_table.get_item(Key={'server_id': event['pathParameters']['serverid']})
            if 'Item' in resp:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps(resp['Item'])}
            else:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'Server Id: ' + str(event['pathParameters']['serverid']) + ' does not exist'}

    elif event['httpMethod'] == 'PUT':
        auth = MFAuth()
        authResponse = auth.getUserAttributePolicy(event)
        if authResponse['action'] == 'allow':
                try:
                    body = json.loads(event['body'])
                    server_attributes = []
                    if "server_id" in body:
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': "You cannot modify server_id, it is managed by the system"}
                except Exception as e:
                    print(e)
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': 'malformed json input'}
                # check if server id exist
                existing_attr = servers_table.get_item(Key={'server_id': event['pathParameters']['serverid']})
                print(existing_attr)
                if 'Item' not in existing_attr:
                  return {'headers': {'Access-Control-Allow-Origin': '*'},
                          'statusCode': 400, 'body': 'server Id: ' + str(event['pathParameters']['serverid']) + ' does not exist'}

                # Check if there is a duplicate server_name
                servers = scan_dynamodb_server_table()
                for server in servers:
                  if 'server_name' in body:
                    if server['server_name'].lower() == str(body['server_name']).lower() and server['server_id'] != str(event['pathParameters']['serverid']):
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': 'server_name: ' +  body['server_name'] + ' already exist'}

                # Validate App_id
                if 'app_id' in body:
                    apps = scan_dynamodb_app_table()
                    check = False
                    for app in apps:
                        if app['app_id'] == str(body['app_id']):
                            check = True
                    if check == False:
                        message = 'app Id: ' + body['app_id'] + ' does not exist'
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': message}

                # Check if attribute is defined in the Server schema
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

                # Merge new attributes with existing one
                for key in body.keys():
                    existing_attr['Item'][key] = body[key]
                new_attr = existing_attr
                keys = list(new_attr['Item'].keys())
                # Delete empty keys
                for key in keys:
                    if new_attr['Item'][key] == '':
                       del new_attr['Item'][key]
                       continue
                    if isinstance(new_attr['Item'][key], list):
                       if len(new_attr['Item'][key]) == 1 and new_attr['Item'][key][0] == '':
                            del new_attr['Item'][key]
                print(new_attr)
                resp = servers_table.put_item(
                Item=new_attr['Item']
                )
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps(resp)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}

    elif event['httpMethod'] == 'DELETE':
        auth = MFAuth()
        authResponse = auth.getUserResourceCrationPolicy(event)
        if authResponse['action'] == 'allow':
            resp = servers_table.get_item(Key={'server_id': event['pathParameters']['serverid']})
            if 'Item' in resp:
                respdel = servers_table.delete_item(Key={'server_id': event['pathParameters']['serverid']})
                if respdel['ResponseMetadata']['HTTPStatusCode'] == 200:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 200, 'body': "Server " + str(resp['Item']) + " was successfully deleted"}
                else:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': respdel['ResponseMetadata']['HTTPStatusCode'], 'body': json.dumps(respdel)}
            else:
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'server Id: ' + str(event['pathParameters']['serverid']) + ' does not exist'}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}

#Add Pagination for DDB table scan  
def scan_dynamodb_server_table():
    response = servers_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key is   " + str(response['LastEvaluatedKey']))
        response = servers_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)

# Pagination for app DDB table scan  
def scan_dynamodb_app_table():
    response = apps_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key for app is   " + str(response['LastEvaluatedKey']))
        response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)