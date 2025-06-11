#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import ListSecret
import CreateOsSecret
import CreateKeyValueSecret
import DeleteSecret
import UpdateSecret
import CreatePlainTextSecret

from cmf_utils import default_http_headers
from cmf_logger import logger, log_event_received


def lambda_handler(event, _):
    log_event_received(event)
    if event['httpMethod'] == 'GET':
        logger.info("sending to ListSecret")
        return {**{'headers': default_http_headers}, **ListSecret.list()}
    if event['body']:
        body = json.loads(event['body'])
        secret_type = body['secretType']
    if event['httpMethod'] == 'POST':
        return process_post(secret_type, event)
    if event['httpMethod'] == 'DELETE':
        if secret_type == 'keyValue' or secret_type == 'OS' or secret_type == 'plainText':
            logger.info("sending to DeleteSecret")
            return {**{'headers': default_http_headers}, **DeleteSecret.delete(event)}
    if event['httpMethod'] == 'PUT':
        if secret_type == 'keyValue' or secret_type == 'OS' or secret_type == 'plainText':
            logger.info("sending to UpdateSecret")
            return {**{'headers': default_http_headers}, **UpdateSecret.update(event)}


def process_post(secret_type, event):
    if secret_type == 'OS':
        logger.info("sending to CreateOsSecret")
        return {**{'headers': default_http_headers}, **CreateOsSecret.create(event)}
    if secret_type == 'keyValue':
        logger.info("sending to CreateKeyValueSecret")
        return {**{'headers': default_http_headers}, **CreateKeyValueSecret.create(event)}
    if secret_type == 'plainText':
        logger.info("sending to CreatePlainTextSecret")
        return {**{'headers': default_http_headers}, **CreatePlainTextSecret.create(event)}
