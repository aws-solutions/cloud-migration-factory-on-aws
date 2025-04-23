#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timezone
import os
from botocore.vendored import requests
#import requests
import json

# System-wide data format for logging and notifications.
CONST_DT_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
CONST_DT_FORMAT_V3 = '%Y-%m-%dT%H:%M:%S.%f'

REQUESTS_DEFAULT_TIMEOUT = 60

if 'cors' in os.environ:
    cors = os.environ['cors']
else:
    cors = '*'

default_http_headers = {
    'Access-Control-Allow-Origin': cors,
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

# anonymous_usage_data settings.
anonymous_usage_data = os.environ.get('AnonymousUsageData', 'Yes')
s_uuid = os.environ.get('solutionUUID', '')
region = os.environ.get('region','unknown')
if region == 'unknown':
    region = os.environ.get('REGION', 'unknown')
anonymous_usage_data_url = 'https://metrics.awssolutionsbuilder.com/generic'
solution_id = os.getenv('SOLUTION_ID', 'SO0097')


def send_anonymous_usage_data(status):
    if anonymous_usage_data == "Yes":
        usage_data = {"Solution": solution_id,
                      "UUID": s_uuid,
                      "Status": status,
                      "TimeStamp": str(datetime.now()),
                      "Region": region
                      }
        requests.post(anonymous_usage_data_url,
                      data=json.dumps(usage_data),
                      headers={'content-type': 'application/json'},
                      timeout=REQUESTS_DEFAULT_TIMEOUT)


def get_date_from_string(str_date):
    try:
        created_timestamp = datetime.strptime(str_date, CONST_DT_FORMAT)
    except Exception as _:
        # try old pre v4 format for backward compatibility.
        created_timestamp = datetime.strptime(str_date, CONST_DT_FORMAT_V3)

    created_timestamp = created_timestamp.replace(tzinfo=timezone.utc)

    return created_timestamp
