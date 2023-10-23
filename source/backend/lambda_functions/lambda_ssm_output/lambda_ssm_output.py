#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import gzip
import json
import base64
import boto3
import botocore
import os
import time
from datetime import datetime
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

application = os.environ["application"]
environment = os.environ["environment"]
dynamodb = boto3.resource("dynamodb")
connectionIds_table_name = '{}-{}-ssm-connectionIds'.format(application, environment)
connectionIds_table = dynamodb.Table(connectionIds_table_name)
ssm_jobs_table_name = '{}-{}-ssm-jobs'.format(application, environment)
ssm_jobs_table = dynamodb.Table(ssm_jobs_table_name)
job_timeout_seconds = 60 * 720  # 12 hours
ddb_retry_max = 2

socket_url = os.environ["socket_url"]
if 'wss://' not in socket_url:
    gatewayapi = None
else:
    gatewayapi = boto3.client("apigatewaymanagementapi", endpoint_url=socket_url)


def unix_time_seconds(dt):
    epoch = datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()


def update_log(ssm_id, output, ddb_retry_count):
    resp = ssm_jobs_table.get_item(TableName=ssm_jobs_table_name, Key={'SSMId': ssm_id})
    ssm_data = resp["Item"]

    if "outcomeDate" in ssm_data["_history"]:
        original_record_time = ssm_data["_history"]["outcomeDate"]
    else:
        original_record_time = ""
    created_timestamp = ssm_data["_history"]["createdTimestamp"]
    outcome_timestamp = datetime.utcnow()
    outcome_timestamp_str = outcome_timestamp.isoformat(sep='T')
    ssm_data["_history"]["outcomeDate"] = outcome_timestamp_str

    time_seconds_elapsed = unix_time_seconds(outcome_timestamp) - unix_time_seconds(
        datetime.strptime(created_timestamp, "%Y-%m-%dT%H:%M:%S.%f"))
    ssm_data["_history"]["timeElapsed"] = str(time_seconds_elapsed)
    logger.debug("time elapsed: " + str(time_seconds_elapsed))

    notification = {
        'type': '',
        'dismissible': True,
        'header': 'Job Update',
        'content': '',
        'timeStamp': ''
    }

    compute_job_status(output, ssm_data, notification, outcome_timestamp_str, time_seconds_elapsed, resp)

    ssm_data["output"] = str(ssm_data["output"]) + output

    output_array = ssm_data["output"].split("\n")

    if len(output_array) > 0:
        for i in range(len(output_array) - 1, 0, -1):
            if output_array[i].strip() != "" and \
                    not output_array[i].strip().startswith("JOB_") and \
                    not (output_array[i].strip().startswith("[") and output_array[i].strip().endswith("]")):
                ssm_data["outputLastMessage"] = output_array[i]
                break
    else:
        ssm_data["outputLastMessage"] = ''

    notification['content'] = ssm_data["jobname"] + ' - ' + ssm_data["outputLastMessage"]
    notification['uuid'] = ssm_data["uuid"]

    error_notification = update_ssm_job_status_in_db(original_record_time, ddb_retry_count, ssm_data, ssm_id, output)
    if error_notification is not None:
        notification = error_notification

    return notification


def compute_job_status(output, ssm_data, notification, outcome_timestamp_str, time_seconds_elapsed, resp):
    if "JOB_COMPLETE" in output:
        logger.info('Job Completed.')
        ssm_data["status"] = "COMPLETE"
        ssm_data["_history"]["completedTimestamp"] = outcome_timestamp_str
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = 'success'
    elif "JOB_FAILED" in output:
        logger.info('Job Failed.')
        ssm_data["status"] = "FAILED"
        ssm_data["_history"]["completedTimestamp"] = outcome_timestamp_str
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = 'error'
    elif int(time_seconds_elapsed) > job_timeout_seconds and resp["Item"]["SSMData"]["status"] == "RUNNING":
        logger.info('Job Timed out.')
        ssm_data["status"] = "TIMED-OUT"
        ssm_data["_history"]["completedTimestamp"] = outcome_timestamp_str
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = 'error'
    else:
        logger.info('Job still running.')
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = 'pending'


def update_ssm_job_status_in_db(original_record_time, ddb_retry_count, ssm_data, ssm_id, output):
    if original_record_time == "":
        response = process_new_log_item(ssm_data, ddb_retry_count, ssm_id, output)
        if response is not None:
            return response
    else:
        response = process_existing_log_item(ssm_data, original_record_time, ddb_retry_count, ssm_id, output)
        if response is not None:
            return response


def process_new_log_item(ssm_data, ddb_retry_count, ssm_id, output):
    try:
        # As no original record time set then this record is assumed to be a new log so check if outcome is present.
        ssm_jobs_table.put_item(
            Item=ssm_data,
            ConditionExpression="attribute_not_exists(#_history.#outcomeDate)",
            ExpressionAttributeNames={
                '#_history': '_history',
                '#outcomeDate': 'outcomeDate',
            }
        )
    except botocore.exceptions.ClientError as x:
        logger.error(x)
        error_code = x.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            if ddb_retry_count < ddb_retry_max:
                ddb_retry_count += 1
                logger.warning("Log write conflict detected. Retry %s of %s for job uuid: %s"
                               % (ddb_retry_count, ddb_retry_max, ssm_data["uuid"]))
                notification = update_log(ssm_id, output, ddb_retry_count)
                return notification
            else:
                logger.error("Log write conflict detected, "
                             "and max retries reached for update job uuid: %s" % ssm_data["uuid"])
        else:
            raise


def process_existing_log_item(ssm_data, original_record_time, ddb_retry_count, ssm_id, output):
    try:
        # Job record has outcomeDate, use this to ensure no changes made to record while processing this request.
        ssm_jobs_table.put_item(
            Item=ssm_data,
            ConditionExpression="#_history.#outcomeDate = :original_record_time",
            ExpressionAttributeNames={
                '#_history': '_history',
                '#outcomeDate': 'outcomeDate',
            },
            ExpressionAttributeValues={
                ":original_record_time": original_record_time,
            },
        )
    except botocore.exceptions.ClientError as x:
        error_code = x.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            # An update was made to the record by another process, retrying update with new record content.
            if ddb_retry_count < ddb_retry_max:
                ddb_retry_count += 1
                logger.warning("Log write conflict detected. Retry %s of %s for job uuid: %s"
                               % (ddb_retry_count, ddb_retry_max, ssm_data["uuid"]))
                notification = update_log(ssm_id, output, ddb_retry_count)
                return notification
            else:
                logger.error("Log write conflict detected, "
                             "and max retries reached for update job uuid: %s" % ssm_data["uuid"])
        else:
            raise


def lambda_handler(event, _):
    # parse Cloudwatch Log
    cw_data = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    message = payload['logEvents'][0]["message"]
    ddb_retry_count = 0

    logger.info('Processing Cloudwatch event.')

    logger.debug(json.dumps(payload))
    logger.debug("Log :" + message)

    # parse SSMId
    ssm_id = message.split("[", 1)[-1]
    ssm_id = ssm_id.split("]", 1)[0]

    logger.info('Job ID. %s', ssm_id)

    # remove remaining SSMIds
    output = message.split(" ", 1)[-1]
    output = output.replace("[" + ssm_id + "]", "")
    output = "[" + time.strftime("%H:%M:%S") + "] " + "\n" + output + "\n" + "\n"

    notification = update_log(ssm_id, output, ddb_retry_count)

    if gatewayapi:  # If socket is set then send notifications to users.
        # Send to all connections
        resp = connectionIds_table.scan()
        for item in resp["Items"]:
            try:
                gatewayapi.post_to_connection(ConnectionId=item["connectionId"], Data=json.dumps(notification))
            except botocore.exceptions.ClientError as e:
                logger.debug(f'Error posting to wss connection {e}')
