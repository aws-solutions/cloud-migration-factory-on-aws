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

apps_table_name = '{}-{}-apps'.format(application, environment)
schema_table_name = '{}-{}-schema'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)

apps_table = boto3.resource('dynamodb').Table(apps_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)
waves_table = boto3.resource('dynamodb').Table(waves_table_name)

def lambda_handler(event, context):

    if event['httpMethod'] == 'GET':
        items = scan_dynamodb_app_table()
        newitem = sorted(items, key = lambda i: i['app_name'])
        return {'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(newitem)}
    elif event['httpMethod'] == 'POST':
        auth = MFAuth()
        authResponse = auth.getUserResourceCrationPolicy(event)
        if authResponse['action'] == 'allow':
            try:
                body = json.loads(event['body'])
                if 'app_name' not in body:
                   return {'headers': {'Access-Control-Allow-Origin': '*'},
                           'statusCode': 400, 'body': 'attribute app_name is required'}
                if "app_id" in body:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': "You cannot create app_id, this is managed by the system"}
                # Check if attribute is defined in the App schema
                app_attributes = []
                for app_schema in schema_table.scan()['Items']:
                       if app_schema['schema_name'] == "app":
                           app_attributes = app_schema['attributes']
                for key in body.keys():
                    check = False
                    for attribute in app_attributes:
                        if key == attribute['name']:
                           check = True
                    if check == False:
                        message = "App attribute: " + key + " is not defined in the App schema"
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': message}
                # Check if attribute in the body matches the list value defined in schema
                for attribute in app_attributes:
                    if 'listvalue' in attribute:
                        listvalue = attribute['listvalue'].split(',')
                        for key in body.keys():
                            if key == attribute['name']:
                                if body[key] not in listvalue:
                                    message = "App attribute " + key + " for app " + body['app_name'] + " is '" + body[key] + "', does not match the list values '" + attribute['listvalue'] + "' defined in the App schema"
                                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                                            'statusCode': 400, 'body': message}
            except Exception as e:
                print(e)
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'malformed json input'}

            # Check if there is a duplicate app_name
            itemlist = scan_dynamodb_app_table()
            for app in itemlist:
               if app['app_name'].lower() == str(body['app_name']).lower():
                  return {'headers': {'Access-Control-Allow-Origin': '*'},
                          'statusCode': 400, 'body': 'app_name: ' +  body['app_name'] + ' already exist'}

            # Validate Wave_id
            if 'wave_id' in body:
                waves = waves_table.scan(ConsistentRead=True)
                check = False
                for wave in waves['Items']:
                    if wave['wave_id'] == str(body['wave_id']):
                       check = True
                if check == False:
                    message = 'wave Id: ' + body['wave_id'] + ' does not exist'
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': message}

            # Get vacant app_id
            ids = []
            for item in itemlist:
                ids.append(int(item['app_id']))
            ids.sort()
            app_id = 1
            for id in ids:
               if app_id == id:
                   app_id += 1
            body['app_id'] = str(app_id)

            # Update item
            resp = apps_table.put_item(
               Item=body
            )
            if (resp['ResponseMetadata']['HTTPStatusCode'] == 200):
                new_item = {}
                query_resp = apps_table.query(KeyConditionExpression=Key('app_id').eq(str(app_id)))
                if 'Items' in query_resp:
                    new_item = query_resp['Items']
                else:
                    new_item = "Creating app " + body['app_name'] + " failed"
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(new_item)}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}

#Add Pagination for apps DDB table scan  
def scan_dynamodb_app_table():
    response = apps_table.scan(ConsistentRead=True)
    scan_data = response['Items']
    while 'LastEvaluatedKey' in response:
        print("Last Evaluate key is   " + str(response['LastEvaluatedKey']))
        response = apps_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],ConsistentRead=True)
        scan_data.extend(response['Items'])
    return(scan_data)
