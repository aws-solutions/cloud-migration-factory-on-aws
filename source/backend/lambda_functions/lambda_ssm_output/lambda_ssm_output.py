#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import gzip
import json
import base64
import botocore
import os
import time
from datetime import datetime, timezone
from typing import Optional

import cmf_boto
from cmf_logger import logger
import cmf_pipeline
from cmf_utils import get_date_from_string, publish_event
from cmf_types import NotificationDetailType, NotificationType

application = os.environ["application"]
environment = os.environ["environment"]
eventBusName = os.environ["EVENT_BUS_NAME"]
dynamodb = cmf_boto.resource("dynamodb")
ssm_jobs_table_name = '{}-{}-ssm-jobs'.format(application, environment)
ssm_jobs_table = dynamodb.Table(ssm_jobs_table_name)
job_timeout_seconds = 60 * 720  # 12 hours
ddb_retry_max = 2

eventsClient = cmf_boto.client('events')
eventSource = f'{application}-{environment}-ssm-output'

def update_log(ssm_id: str, output: str, ddb_retry_count: int) -> NotificationType:
    """
    Updates SSM job log with new output and computes updated status.
    
    Args:
        ssm_id: Unique identifier for the SSM job
        output: New output content to append to job log
        ddb_retry_count: Current retry attempt count for DynamoDB operations
        
    Returns:
        Notification object containing job status update details
        
    Raises:
        ClientError: If DynamoDB operations fail
    """
    
    resp = ssm_jobs_table.get_item(TableName=ssm_jobs_table_name, Key={'SSMId': ssm_id})
    ssm_data = resp["Item"]

    if "outcomeDate" in ssm_data["_history"]:
        original_record_time = ssm_data["_history"]["outcomeDate"]
    else:
        original_record_time = ""
    created_timestamp = get_date_from_string(ssm_data["_history"]["createdTimestamp"])
    outcome_timestamp = datetime.now(timezone.utc)
    outcome_timestamp_str = outcome_timestamp.isoformat(sep='T')
    ssm_data["_history"]["outcomeDate"] = outcome_timestamp_str

    time_elapsed = outcome_timestamp - created_timestamp
    time_seconds_elapsed = time_elapsed.total_seconds()

    ssm_data["_history"]["timeElapsed"] = str(time_seconds_elapsed)
    logger.debug("time elapsed: " + str(time_seconds_elapsed))

    notification: NotificationType = {
        'type': '',
        'dismissible': True,
        'header': 'Job Update',
        'content': '',
        'timeStamp': datetime.now(timezone.utc).isoformat(sep='T')
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

    pipeline_task_execution_status = cmf_pipeline.TaskExecutionStatus.IN_PROGRESS
    if ssm_data.get('status') == "COMPLETE":
        pipeline_task_execution_status = cmf_pipeline.TaskExecutionStatus.COMPLETE
    elif ssm_data.get('status') == "TIMED-OUT" or ssm_data.get('status') == 'FAILED':
        pipeline_task_execution_status = cmf_pipeline.TaskExecutionStatus.FAILED

   # Update any related pipeline task executions
    cmf_pipeline.update_task_execution_output(ssm_data["jobname"], ssm_data["outputLastMessage"], ssm_data["output"])
    cmf_pipeline.update_task_execution_status(ssm_data["jobname"], pipeline_task_execution_status)

    notification['content'] = ssm_data["jobname"] + ' - ' + ssm_data["outputLastMessage"]
    notification['uuid'] = ssm_data["uuid"]

    error_notification = update_ssm_job_status_in_db(original_record_time, ddb_retry_count, ssm_data, ssm_id, output)
    if error_notification is not None:
        notification = error_notification

    return notification


def compute_job_status(output: str, ssm_data: dict, notification: NotificationType, 
                      outcome_timestamp_str: str, time_seconds_elapsed: float, resp: dict) -> None:
    """
    Determines job status based on output content and updates relevant data structures.
    
    Args:
        output: Job output content to analyze
        ssm_data: SSM job data dictionary to be updated
        notification: Notification object to be updated
        outcome_timestamp_str: ISO formatted timestamp string
        time_seconds_elapsed: Total seconds elapsed since job start
        resp: Original DynamoDB response containing job data
        
    Returns:
        None
    """
    
    if "JOB_COMPLETE" in output:
        logger.info('Job Completed.')
        ssm_data["status"] = "COMPLETE"
        ssm_data["_history"]["completedTimestamp"] = outcome_timestamp_str
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = NotificationDetailType.TASK_SUCCESS.value
    elif "JOB_FAILED" in output:
        logger.info('Job Failed.')
        ssm_data["status"] = "FAILED"
        ssm_data["_history"]["completedTimestamp"] = outcome_timestamp_str
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = NotificationDetailType.TASK_FAILED.value
    elif int(time_seconds_elapsed) > job_timeout_seconds and resp["Item"]["SSMData"]["status"] == "RUNNING":
        logger.info('Job Timed out.')
        ssm_data["status"] = "TIMED-OUT"
        ssm_data["_history"]["completedTimestamp"] = outcome_timestamp_str
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = NotificationDetailType.TASK_TIMED_OUT.value
    else:
        logger.info('Job still running.')
        notification['timeStamp'] = outcome_timestamp_str
        notification['type'] = NotificationDetailType.TASK_PENDING.value


def update_ssm_job_status_in_db(original_record_time: str, ddb_retry_count: int, 
                               ssm_data: dict, ssm_id: str, output: str) -> Optional[NotificationType]:
    """
    Updates SSM job status in DynamoDB.
    
    Args:
        original_record_time: Original timestamp for optimistic locking
        ddb_retry_count: Current retry attempt count for DynamoDB operations
        ssm_data: SSM job data to be updated
        ssm_id: Unique identifier for the SSM job
        output: Job output content
        
    Returns:
        Error notification if update fails, None otherwise
        
    Raises:
        ClientError: If DynamoDB operations fail
    """
    
    if original_record_time == "":
        response = process_new_log_item(ssm_data, ddb_retry_count, ssm_id, output)
        if response is not None:
            return response
    else:
        response = process_existing_log_item(ssm_data, original_record_time, ddb_retry_count, ssm_id, output)
        if response is not None:
            return response


def process_new_log_item(ssm_data: dict, ddb_retry_count: int, 
                        ssm_id: str, output: str) -> Optional[NotificationType]:
    """
    Creates new SSM job log item in DynamoDB.
    
    Args:
        ssm_data: SSM job data to be stored
        ddb_retry_count: Current retry attempt count for DynamoDB operations
        ssm_id: Unique identifier for the SSM job
        output: Job output content
        
    Returns:
        Error notification if creation fails, None otherwise
        
    Raises:
        ClientError: If DynamoDB operations fail
    """
    
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


def process_existing_log_item(ssm_data: dict, original_record_time: str, 
                            ddb_retry_count: int, ssm_id: str, output: str) -> Optional[NotificationType]:
    """
    Updates existing SSM job log item in DynamoDB.
    
    Args:
        ssm_data: Updated SSM job data
        original_record_time: Original timestamp for optimistic locking
        ddb_retry_count: Current retry attempt count for DynamoDB operations
        ssm_id: Unique identifier for the SSM job
        output: Job output content
        
    Returns:
        Error notification if update fails, None otherwise
        
    Raises:
        ClientError: If DynamoDB operations fail
    """
    
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
    """
    Processes CloudWatch Log events and updates SSM job status.
    
    Args:
        event: AWS Lambda event containing CloudWatch Log data
        
    Returns:
        None
        
    Raises:
        ClientError: If DynamoDB operations fail
        ValueError: If log data cannot be decoded or decompressed
    """

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

    if not ssm_id:
        logger.error('No SSMId or empty SSMId in Cloudwatch event.')
        return None

    logger.info('Job ID. %s', ssm_id)

    # remove remaining SSMIds
    output = message.split(" ", 1)[-1]
    output = output.replace("[" + ssm_id + "]", "")
    output = "[" + time.strftime("%H:%M:%S") + "] " + "\n" + output + "\n" + "\n"

    notification: NotificationType = update_log(ssm_id, output, ddb_retry_count)

    publish_event(notification, eventsClient, eventSource, eventBusName)