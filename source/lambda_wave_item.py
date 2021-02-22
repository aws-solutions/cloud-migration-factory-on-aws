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
import logging
from boto3.dynamodb.conditions import Key, Attr
from policy import MFAuth

log = logging.getLogger()
log.setLevel(logging.INFO)

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
        resp = waves_table.get_item(Key={'wave_id': event['pathParameters']['waveid']})
        if 'Item' in resp:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(resp['Item'])}
        else:
            message = 'wave Id: ' + str(event['pathParameters']['waveid']) + ' does not exist'
            log.info(message)
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 400, 'body': message}

    elif event['httpMethod'] == 'PUT':
        auth = MFAuth()
        authResponse = auth.getUserResourceCrationPolicy(event)
        if authResponse['action'] == 'allow':
            try:
                body = json.loads(event['body'])
                wave_attributes = []
                if "wave_id" in body:
                    message = "You cannot modify wave_id, this is managed by the system"
                    log.info(message)
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 400, 'body': message}

                # check if wave id exist
                existing_attr = waves_table.get_item(Key={'wave_id': event['pathParameters']['waveid']})
                print(existing_attr)
                if 'Item' not in existing_attr:
                  message = 'wave Id: ' + str(event['pathParameters']['waveid']) + ' does not exist'
                  log.info(message)
                  return {'headers': {'Access-Control-Allow-Origin': '*'},
                          'statusCode': 400, 'body': message}

                # Check if there is a duplicate wave_name
                waves = waves_table.scan()
                for wave in waves['Items']:
                  if 'wave_name' in body:
                    if wave['wave_name'].lower() == str(body['wave_name']).lower() and wave['wave_id'] != str(event['pathParameters']['waveid']):
                        message = 'wave_name: ' +  body['wave_name'] + ' already exist'
                        log.info(message)
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': message}

                # Check if attribute is defined in the Wave schema
                for wave_schema in schema_table.scan()['Items']:
                    if wave_schema['schema_name'] == "wave":
                        wave_attributes = wave_schema['attributes']
                for key in body.keys():
                    check = False
                    for attribute in wave_attributes:
                        if key == attribute['name']:
                           check = True
                    if check == False:
                        message = "Wave attribute: " + key + " is not defined in the Wave schema"
                        log.info(message)
                        return {'headers': {'Access-Control-Allow-Origin': '*'},
                                'statusCode': 400, 'body': message}

                # Check if attribute in the body matches the list value defined in schema
                for attribute in wave_attributes:
                    if 'listvalue' in attribute:
                        listvalue = attribute['listvalue'].split(',')
                        for key in body.keys():
                            if key == attribute['name']:
                                if body[key] not in listvalue:
                                    message = "Wave attribute " + key + " for wave " + body['wave_name'] + " is '" + body[key] + "', does not match the list values '" + attribute['listvalue'] + "' defined in the Wave schema"
                                    log.info(message)
                                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                                            'statusCode': 400, 'body': message}

                # Merge new attributes with existing one
                for key in body.keys():
                    existing_attr['Item'][key] = body[key]
                print(existing_attr)
                resp = waves_table.put_item(
                Item=existing_attr['Item']
                )
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps(resp)}
            except Exception as e:
                log.info(str(e))
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': 'malformed json input'}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}

    elif event['httpMethod'] == 'DELETE':
        auth = MFAuth()
        authResponse = auth.getUserResourceCrationPolicy(event)
        if authResponse['action'] == 'allow':
            resp = waves_table.get_item(Key={'wave_id': event['pathParameters']['waveid']})
            if 'Item' in resp:
                respdel = waves_table.delete_item(Key={'wave_id': event['pathParameters']['waveid']})
                if respdel['ResponseMetadata']['HTTPStatusCode'] == 200:
                    # Remove Wave Id from apps
                    apps = apps_table.scan()
                    if apps['Count'] is not 0:
                        for app in apps['Items']:
                           newapp = app
                           if 'wave_id' in app:
                               if str(app['wave_id']) == str(event['pathParameters']['waveid']):
                                   del newapp['wave_id']
                                   appupdate = apps_table.put_item(
                                                    Item=newapp
                                                    )
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': 200, 'body': "Wave " + str(resp['Item']) + " was successfully deleted"}
                else:
                    return {'headers': {'Access-Control-Allow-Origin': '*'},
                            'statusCode': respdel['ResponseMetadata']['HTTPStatusCode'], 'body': json.dumps(respdel)}
            else:
                message = 'wave Id: ' + str(event['pathParameters']['waveid']) + ' does not exist'
                log.info(message)
                return {'headers': {'Access-Control-Allow-Origin': '*'},
                        'statusCode': 400, 'body': message}
        else:
            return {'headers': {'Access-Control-Allow-Origin': '*'},
                    'statusCode': 401,
                    'body': json.dumps(authResponse)}
