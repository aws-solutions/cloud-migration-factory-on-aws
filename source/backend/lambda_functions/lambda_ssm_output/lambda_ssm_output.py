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
    SSMData = resp["Item"]

    if "outcomeDate" in SSMData["_history"]:
        original_record_time = SSMData["_history"]["outcomeDate"]
    else:
        original_record_time = ""
    createdTimestamp = SSMData["_history"]["createdTimestamp"]
    outcomeTimestamp = datetime.utcnow()
    outcomeTimestampStr = outcomeTimestamp.isoformat(sep='T')
    SSMData["_history"]["outcomeDate"] = outcomeTimestampStr

    timeSecondsElapsed = unix_time_seconds(outcomeTimestamp) - unix_time_seconds(
        datetime.strptime(createdTimestamp, "%Y-%m-%dT%H:%M:%S.%f"))
    SSMData["_history"]["timeElapsed"] = str(timeSecondsElapsed)
    logger.debug("time elapsed: " + str(timeSecondsElapsed))

    notification = {
        'type': '',
        'dismissible': True,
        'header': 'Job Update',
        'content': '',
        'timeStamp': ''
    }

    if "JOB_COMPLETE" in output:
        logger.info('Job Completed.')
        SSMData["status"] = "COMPLETE"
        SSMData["_history"]["completedTimestamp"] = outcomeTimestampStr
        notification['timeStamp'] = outcomeTimestampStr
        notification['type'] = 'success'
    elif "JOB_FAILED" in output:
        logger.info('Job Failed.')
        SSMData["status"] = "FAILED"
        SSMData["_history"]["completedTimestamp"] = outcomeTimestampStr
        notification['timeStamp'] = outcomeTimestampStr
        notification['type'] = 'error'
    elif int(timeSecondsElapsed) > job_timeout_seconds and resp["Item"]["SSMData"]["status"] == "RUNNING":
        logger.info('Job Timed out.')
        SSMData["status"] = "TIMED-OUT"
        SSMData["_history"]["completedTimestamp"] = outcomeTimestampStr
        notification['timeStamp'] = outcomeTimestampStr
        notification['type'] = 'error'
    else:
        logger.info('Job still running.')
        notification['timeStamp'] = outcomeTimestampStr
        notification['type'] = 'pending'

    SSMData["output"] = str(SSMData["output"]) + output

    outputArray = SSMData["output"].split("\n")

    if len(outputArray) > 0:
        for i in range(len(outputArray) - 1, 0, -1):
            if outputArray[i].strip() != "" and not outputArray[i].strip().startswith("JOB_") and not (
                outputArray[i].strip().startswith("[") and outputArray[i].strip().endswith("]")):
                SSMData["outputLastMessage"] = outputArray[i]
                break
    else:
        SSMData["outputLastMessage"] = ''

    notification['content'] = SSMData["jobname"] + ' - ' + SSMData["outputLastMessage"]
    notification['uuid'] = SSMData["uuid"]

    if original_record_time == "":
        try:
            # As no original record time set then this record is assumed to be a new log so check if outcome is present.
            ssm_jobs_table.put_item(
                Item=SSMData,
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
                                   % (ddb_retry_count, ddb_retry_max, SSMData["uuid"]))
                    notification = update_log(ssm_id, output, ddb_retry_count)
                else:
                    logger.error("Log write conflict detected, "
                                 "and max retries reached for update job uuid: %s" % SSMData["uuid"])
                pass
            else:
                raise
    else:
        try:
            # Job record has outcomeDate, use this to ensure no changes made to record while processing this request.
            ssm_jobs_table.put_item(
                Item=SSMData,
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
                                   % (ddb_retry_count, ddb_retry_max, SSMData["uuid"]))
                    notification = update_log(ssm_id, output, ddb_retry_count)
                else:
                    logger.error("Log write conflict detected, "
                                 "and max retries reached for update job uuid: %s" % SSMData["uuid"])
                pass
            else:
                raise
    return notification


def lambda_handler(event, context):
    # parse Cloudwatch Log
    cw_data = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    message = payload['logEvents'][0]["message"]
    ddb_retry_count = 0

    logger.info('Processing Cloudwatch event.')

    logger.debug(json.dumps(payload))
    logger.debug("Log :" + message)

    # parse SSMId
    SSMId = message.split("[", 1)[-1]
    SSMId = SSMId.split("]", 1)[0]

    logger.info('Job ID. %s', SSMId)

    # remove remaining SSMIds
    output = message.split(" ", 1)[-1]
    output = output.replace("[" + SSMId + "]", "")
    output = "[" + time.strftime("%H:%M:%S") + "] " + "\n" + output + "\n" + "\n"

    notification = update_log(SSMId, output, ddb_retry_count)

    if gatewayapi:  # If socket is set then send notifications to users.
        # Send to all connections
        resp = connectionIds_table.scan()
        for item in resp["Items"]:
            try:
                gatewayapi.post_to_connection(ConnectionId=item["connectionId"], Data=json.dumps(notification))
            except botocore.exceptions.ClientError as e:
                pass
