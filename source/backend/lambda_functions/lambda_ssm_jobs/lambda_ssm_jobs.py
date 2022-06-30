import json
import boto3
from datetime import datetime
import os
import uuid
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level = logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

dynamodb = boto3.resource("dynamodb")
ssm_jobs_table_name = '{}-{}-ssm-jobs'.format(application, environment)
table = dynamodb.Table(ssm_jobs_table_name)
job_timeout_seconds = 60*720 # 12 hours

def unix_time_seconds(dt):
    epoch = datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()

def get_latest_datetimestamp(job_history):

    if 'completedTimestamp' in job_history:
        return datetime.strptime(job_history["completedTimestamp"], "%Y-%m-%dT%H:%M:%S.%f")

    if 'createdTimestamp' in job_history:
        return datetime.strptime(job_history["createdTimestamp"], "%Y-%m-%dT%H:%M:%S.%f")

def updateJobStatus(SSMData):
    currentTime = datetime.utcnow()
    currentTimeStr = currentTime.isoformat(sep='T')
    createdTimestamp = datetime.strptime(SSMData["_history"]["createdTimestamp"], "%Y-%m-%dT%H:%M:%S.%f")
    timeSecondsElapsed = unix_time_seconds(currentTime) - unix_time_seconds(createdTimestamp)
    if timeSecondsElapsed > job_timeout_seconds:
        logger.info('Job timeout breached')
        logger.info(SSMData)

        SSMData["status"] = "TIMED-OUT"
        SSMData["_history"]["completedTimestamp"] = currentTimeStr
        table.put_item(Item=SSMData)

def lambda_handler(event, context):
    logger.debug(event)
    if 'payload' in event and event['payload']['httpMethod'] == 'POST':
        logger.info("Processing POST")
        jobUUID = str(uuid.uuid4())
        SSMData = json.loads(event['payload']['body'])
        SSMData["status"] = "RUNNING"

        #Assign an id for the job as not currently set.
        if "uuid" not in SSMData.keys():
            SSMData['uuid'] = jobUUID

        table.put_item(Item=SSMData)

        return {'headers': {**default_http_headers},
                'body': json.dumps("SSMId: " + SSMData['SSMId'])}

    elif event['httpMethod'] == 'GET':
        logger.info("Processing GET")
        response = table.scan()
        if response["Count"] == 0:
            return {'headers': {**default_http_headers},
                        'body': json.dumps([])}

        SSMJobs = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            SSMJobs.extend(response['Items'])

        # Scan all jobs with a RUNNING status and check that timeout has not been breached.
        for SSMData in SSMJobs:
            if SSMData["status"] == "RUNNING":
                updateJobStatus(SSMData)

        dt_object = datetime.strptime(SSMData["_history"]["createdTimestamp"], "%Y-%m-%dT%H:%M:%S.%f")

        SSMJobs.sort(key=lambda SSMJob: get_latest_datetimestamp(SSMJob["_history"]), reverse=True)

        logger.info("Request successful, returning job results list.")

        logger.debug(SSMJobs)

        return {'headers': {**default_http_headers},
                'body': json.dumps(SSMJobs)}

    elif event['httpMethod'] == 'DELETE':
        logger.info("Processing DELETE")
        SSMId = event['pathParameters']["jobid"]
        table.delete_item(Key={"SSMId": SSMId})

        return {'headers': {**default_http_headers},
                'body': SSMId + " deleted"}



