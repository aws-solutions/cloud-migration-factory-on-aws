#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from boto3 import client as boto3_client
import json
import re
from typing import Any
from typing import List
from typing import Dict

from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers, send_anonymous_usage_data
from shared.header_mapping import process_map_headers_request

bedrock_runtime = boto3_client("bedrock-runtime")
model = os.environ["model"]

# There is a risk of timeout by API Gateway when using a large number
# of headers for input.
#
# The lambda expects a body with the following shape:
#
#  {
#     headers: [
#         "header": "sample_value"
#     ],
#     schema: {
#        application: ["attribute_1"],
#        server: ["attribute_1"],
#        database: ["attribute_1"]
#     }
#  }
#
# , and returns 400 if either headers or schema is missing or empty.
def lambda_handler(event: Any, _):
    log_event_received(event)

    # Not Supported is the output of the BedrockModelSelector custom resource
    if model == "Not Supported":
        return {
            "headers": {**default_http_headers}, 
            "statusCode": 500, 
            "body": "No preferred model was available. Confirm Bedrock is available in your deployed AWS Region"
        }

    # Basic checks
    if "body" not in event:
        return {"valid": False, "error": "Missing request body"}

    try:
        body = json.loads(event["body"])
    except BaseException as e:
        logger.error(f"malformed json input {e}")
        return {"headers": {**default_http_headers}, "statusCode": 400, "body": "malformed json input"}

    try:
        headersToMap = parse_headers(body)
        schemas = parse_schemas(body)
    except ValueError as e:
        logger.error(f"Unable to parse headers or schema {e}")
        return {"headers": {**default_http_headers}, "statusCode": 400, "body": f"incorrect request type. {e}"}

    try:
        request = {"headers": headersToMap, "schemas": schemas}
        response = process_map_headers_request(request, bedrock_runtime, model)
        send_anonymous_usage_data('HeaderMappingComplete_Direct')
    except BaseException as e:
        logger.error(f"Unable to query bedrock {e}")
        return {"headers": {**default_http_headers}, "statusCode": 500, "body": f"internal server exception"}

    return {"headers": {**default_http_headers}, "statusCode": 200, "body": json.dumps(response)}


def validate_input(data, depth=0, max_depth=100):
    if depth > max_depth:
        raise ValueError("Maximum recursion depth exceeded")
    if isinstance(data, dict):
        for key, value in data.items():
            validate_input(key, depth+1, max_depth)
            validate_input(value, depth+1, max_depth)
    elif isinstance(data, list):
        for item in data:
            validate_input(item, depth+1, max_depth)
    elif isinstance(data, str):
        if not re.match(r'^[a-zA-Z0-9_ .#-]*$', data):
            raise ValueError("Invalid characters in input")


def parse_schemas(body):
    schemas = body.get("schemas")
    if not schemas:
        raise ValueError("attribute schemas is required")
    validate_input(schemas)
    return schemas


def parse_headers(body):
    headers = body.get("headers")
    if not headers:
        raise ValueError("attribute headers is required")
    validate_input(headers)
    return headers
