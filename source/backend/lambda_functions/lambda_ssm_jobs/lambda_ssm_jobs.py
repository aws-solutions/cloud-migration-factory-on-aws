#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import boto3
from datetime import datetime
from datetime import timedelta
import os
import uuid
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}
application = os.environ['application']
environment = os.environ['environment']

dynamodb = boto3.resource("dynamodb")
ssm_jobs_table_name = '{}-{}-ssm-jobs'.format(application, environment)
table = dynamodb.Table(ssm_jobs_table_name)
job_timeout_seconds = 60 * 720  # 12 hours
default_maximum_days_logs_returned = 30  # Set to None to return all logs.

CONST_DT_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


def unix_time_seconds(dt):
    epoch = datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()


def get_latest_datetimestamp(job_history):
    if 'completedTimestamp' in job_history:
        return datetime.strptime(job_history["completedTimestamp"], CONST_DT_FORMAT)

    if 'createdTimestamp' in job_history:
        return datetime.strptime(job_history["createdTimestamp"], CONST_DT_FORMAT)


def update_job_status(ssm_data):
    current_time = datetime.utcnow()
    current_time_str = current_time.isoformat(sep='T')
    created_timestamp = datetime.strptime(ssm_data["_history"]["createdTimestamp"], CONST_DT_FORMAT)
    time_seconds_elapsed = unix_time_seconds(current_time) - unix_time_seconds(created_timestamp)
    if time_seconds_elapsed > job_timeout_seconds:
        logger.info('Job timeout breached')
        logger.info(ssm_data)
        ssm_data["status"] = "TIMED-OUT"
        ssm_data["_history"]["completedTimestamp"] = current_time_str
        table.put_item(Item=ssm_data)


def process_post(event):
    logger.info("Processing POST")
    job_uuid = str(uuid.uuid4())
    ssm_data = json.loads(event['payload']['body'])
    ssm_data["status"] = "RUNNING"

    # Assign an id for the job as not currently set.
    if "uuid" not in ssm_data.keys():
        ssm_data['uuid'] = job_uuid

    table.put_item(Item=ssm_data)

    return {
        'headers': {**default_http_headers},
        'body': json.dumps("SSMId: " + ssm_data['SSMId'])
    }


def process_get(event):
    logger.info("Processing GET")

    if "queryStringParameters" in event and event["queryStringParameters"] and \
            "maximumdays" in event["queryStringParameters"]:
        maximum_days_logs_returned = int(event["queryStringParameters"]["maximumdays"])
    else:
        maximum_days_logs_returned = default_maximum_days_logs_returned

    if maximum_days_logs_returned is not None:
        current_time = datetime.utcnow()
        current_time = current_time + timedelta(days=-maximum_days_logs_returned)
        current_time_str = current_time.isoformat(sep='T')

        response = table.scan(FilterExpression="#_history.#createdTimestamp > :current_time_30days",
                              ExpressionAttributeNames={
                                  '#_history': '_history',
                                  '#createdTimestamp': 'createdTimestamp',
                              },
                              ExpressionAttributeValues={
                                  ":current_time_30days": current_time_str,
                              }
                              )
    else:
        response = table.scan()

    if response["Count"] == 0:
        return {
            'headers': {**default_http_headers},
            'body': json.dumps([])
        }

    ssm_jobs = response['Items']
    while 'LastEvaluatedKey' in response:
        if maximum_days_logs_returned is not None:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'],
                                  FilterExpression="#_history.#createdTimestamp > :current_time_30days",
                                  ExpressionAttributeNames={
                                      '#_history': '_history',
                                      '#createdTimestamp': 'createdTimestamp',
                                  },
                                  ExpressionAttributeValues={
                                      ":current_time_30days": current_time_str,
                                  }
                                  )
        else:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        ssm_jobs.extend(response['Items'])

    # Scan all jobs with a RUNNING status and check that timeout has not been breached.
    for ssm_data in ssm_jobs:
        if ssm_data["status"] == "RUNNING":
            update_job_status(ssm_data)

    ssm_jobs.sort(key=lambda SSMJob: get_latest_datetimestamp(SSMJob["_history"]), reverse=True)

    logger.info("Request successful, returning job results list.")

    logger.debug(ssm_jobs)

    return {
        'headers': {**default_http_headers},
        'body': json.dumps(ssm_jobs)
    }


def process_delete(event):
    logger.info("Processing DELETE")
    ssm_id = event['pathParameters']["jobid"]
    table.delete_item(Key={"SSMId": ssm_id})

    return {
        'headers': {**default_http_headers},
        'body': ssm_id + " deleted"
    }


def lambda_handler(event, _):
    logger.debug(event)
    if 'payload' in event and event['payload']['httpMethod'] == 'POST':
        return process_post(event)
    elif event['httpMethod'] == 'GET':
        return process_get(event)
    elif event['httpMethod'] == 'DELETE':
        return process_delete(event)
