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
from policy import MFAuth

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

servers_table_name = '{}-{}-servers'.format(application, environment)
schema_table_name = '{}-{}-schema'.format(application, environment)
apps_table_name = '{}-{}-apps'.format(application, environment)
waves_table_name = '{}-{}-waves'.format(application, environment)

waves_table = boto3.resource('dynamodb').Table(waves_table_name)
servers_table = boto3.resource('dynamodb').Table(servers_table_name)
schema_table = boto3.resource('dynamodb').Table(schema_table_name)
apps_table = boto3.resource('dynamodb').Table(apps_table_name)

def lambda_handler(event, context):

    if event['httpMethod'] == 'GET':
        respServer = schema_table.get_item(Key={'schema_name' : 'server'})
        respApp = schema_table.get_item(Key={'schema_name' : 'app'})
        respWave = schema_table.get_item(Key={'schema_name' : 'wave'})
        defaultDate = datetime.datetime(2020, 1, 1)
        lastChangeDate = datetime.datetime(2020, 1, 1)
        notifications = {
                            'lastChangeDate': '',
                            'notifications' : []
                        }
        schema_notifications = {
                                'type' : 'schema',
                                'versions': []}

        if 'Item' in respServer:
            if 'lastModifiedTimestamp' in respServer['Item']:
                dt_object = datetime.datetime.strptime(respServer['Item']['lastModifiedTimestamp'], "%Y-%m-%dT%H:%M:%S.%f")
                if dt_object > lastChangeDate: lastChangeDate = dt_object
                schema_notifications['versions'].append(
                            {
                               'schema': 'server',
                               'lastModifiedTimestamp': respServer['Item']['lastModifiedTimestamp']
                })
            else:
                schema_notifications['versions'].append(
                            {
                               'schema': 'server',
                               'lastModifiedTimestamp': defaultDate.isoformat()
                })

        if 'Item' in respApp:
            if 'lastModifiedTimestamp' in respApp['Item']:
                dt_object = datetime.datetime.strptime(respApp['Item']['lastModifiedTimestamp'], "%Y-%m-%dT%H:%M:%S.%f")
                if dt_object > lastChangeDate: lastChangeDate = dt_object
                schema_notifications['versions'].append(
                            {
                               'schema': 'app',
                               'lastModifiedTimestamp': respApp['Item']['lastModifiedTimestamp']
                })
            else:
                schema_notifications['versions'].append(
                            {
                               'schema': 'app',
                               'lastModifiedTimestamp': defaultDate.isoformat()
                })

        if 'Item' in respWave:
            if 'lastModifiedTimestamp' in respWave['Item']:
                dt_object = datetime.datetime.strptime(respWave['Item']['lastModifiedTimestamp'], "%Y-%m-%dT%H:%M:%S.%f")
                if dt_object > lastChangeDate: lastChangeDate = dt_object
                schema_notifications['versions'].append(
                            {
                               'schema': 'wave',
                               'lastModifiedTimestamp': respWave['Item']['lastModifiedTimestamp']
                })
            else:
                schema_notifications['versions'].append(
                            {
                               'schema': 'wave',
                               'lastModifiedTimestamp': defaultDate.isoformat()
                })


        notifications['notifications'].append(schema_notifications)
        notifications['lastChangeDate'] = lastChangeDate.isoformat()

        return {'headers': {**default_http_headers},
                    'statusCode': 200,
                    'body': json.dumps(notifications)}