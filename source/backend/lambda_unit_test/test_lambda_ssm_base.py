#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
import uuid
from datetime import datetime
from datetime import timedelta
from unittest import mock

from moto import mock_dynamodb

from test_common_utils import default_mock_os_environ


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_dynamodb
class LambdaSSMBaseTest(unittest.TestCase):
    def put_recent_job(self, table_obj, job_id, num_hours):
        current_time = datetime.utcnow()
        current_time = current_time + timedelta(hours=-num_hours)
        current_time_str = current_time.isoformat(sep='T')
        ssm_uuid = str(uuid.uuid4())
        instance_id = 'i-00000000000000000'
        ssm_id = instance_id + '+' + ssm_uuid + '+' + current_time_str
        item = {
            'SSMId': ssm_id,
            'uuid': ssm_uuid,
            'jobname': 'Test job ' + str(job_id),
            'status': 'RUNNING',
            'SSMData': {
                'status': 'RUNNING',
            },
            'output': 'job output 123',
            '_history': {
                'createdTimestamp': current_time_str
            }
        }
        table_obj.put_item(Item=item)
        return ssm_id
