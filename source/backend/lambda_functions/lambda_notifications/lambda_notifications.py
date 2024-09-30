#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import simplejson as json
from datetime import datetime, timezone

import cmf_boto
from cmf_utils import cors, default_http_headers, CONST_DT_FORMAT, get_date_from_string
from cmf_logger import logger, log_event_received

application = os.environ['application']
environment = os.environ['environment']

schema_table_name = '{}-{}-schema'.format(application, environment)
schema_table = cmf_boto.resource('dynamodb').Table(schema_table_name)


def process_item(items, schema, schema_notifications, default_date, last_change_date):
    if 'lastModifiedTimestamp' in items['Item']:
        dt_object = get_date_from_string(items['Item']['lastModifiedTimestamp'])
        if dt_object > last_change_date:
            last_change_date = dt_object
        schema_notifications['versions'].append(
            {
                'schema': schema,
                'lastModifiedTimestamp': items['Item']['lastModifiedTimestamp']
            })
    else:
        schema_notifications['versions'].append(
            {
                'schema': schema,
                'lastModifiedTimestamp': default_date.isoformat()
            })
    return last_change_date


def lambda_handler(event, _):
    log_event_received(event)

    if event['httpMethod'] == 'GET':
        resp_server = schema_table.get_item(Key={'schema_name': 'server'})
        resp_app = schema_table.get_item(Key={'schema_name': 'app'})
        resp_wave = schema_table.get_item(Key={'schema_name': 'wave'})
        resp_db = schema_table.get_item(Key={'schema_name': 'database'})
        default_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        last_change_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        notifications = {
            'lastChangeDate': '',
            'notifications': []
        }
        schema_notifications = {
            'type': 'schema',
            'versions': []}
        if 'Item' in resp_server:
            last_change_date = process_item(resp_server, 'server', schema_notifications, default_date, last_change_date)

        if 'Item' in resp_app:
            last_change_date = process_item(resp_app, 'app', schema_notifications, default_date, last_change_date)

        if 'Item' in resp_wave:
            last_change_date = process_item(resp_wave, 'wave', schema_notifications, default_date, last_change_date)

        if 'Item' in resp_db:
            last_change_date = process_item(resp_db, 'database', schema_notifications, default_date, last_change_date)

        notifications['notifications'].append(schema_notifications)
        notifications['lastChangeDate'] = last_change_date.isoformat()

        return {'headers': {**default_http_headers},
                'statusCode': 200,
                'body': json.dumps(notifications)
                }
