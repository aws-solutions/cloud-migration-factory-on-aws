#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import gzip
import json
import base64
import re
import os
from datetime import datetime
import time

import cmf_boto
from cmf_logger import logger
import cmf_pipeline

ddb_client = cmf_boto.resource("dynamodb")
application = os.environ["application"]
environment = os.environ["environment"]
task_executions_table_name = '{}-{}-task_executions'.format(application, environment)
task_executions_table = ddb_client.Table(task_executions_table_name)


def update_log(task_execution_id, status, message):
    logger.info(f'Writing log for task execution ID: {task_execution_id}')
    resp = task_executions_table.get_item(Key={'task_execution_id': task_execution_id})
    if "Item" not in resp:
        logger.warn("Task execution ID not found")
        return
    task_execution_data = resp["Item"]

    message = "[" + time.strftime("%H:%M:%S") + "] " + "\n" + message + "\n"
    output = task_execution_data.get("output", "") + message
    last_output_message = message.split(f'[{status}]',1)[1]

    cmf_pipeline.update_task_execution_output(task_execution_id, last_output_message, output)
    cmf_pipeline.update_task_execution_status(task_execution_id, cmf_pipeline.TaskExecutionStatus(status))


def lambda_handler(event, _):
    # parse Cloudwatch Log
    cw_data = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    for log_event in payload['logEvents']:
        message = log_event["message"]

        logger.info('Processing Cloudwatch event.')

        # Expected log format to be "[task_execution_id][status] message"
        message_metadata = re.findall(r"\[(.*?)\]", message)
        if (len(message_metadata) < 2):
            logger.debug(f"Can't process message format: {message}")
            continue

        update_log(message_metadata[0], message_metadata[1], message)