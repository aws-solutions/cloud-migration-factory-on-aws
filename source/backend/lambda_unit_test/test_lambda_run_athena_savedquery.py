#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import unittest
from unittest import mock
import time

import boto3
from moto import mock_aws
from test_common_utils import LambdaContextFnArn, test_account_id
from test_common_utils import logger, default_mock_os_environ


mock_os_environ = {
    **default_mock_os_environ,
    'database': 'cmf_db',
    'workgroup': 'cmf_workgroup'
}


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaRunAthenaSavedQueryTest(unittest.TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        self.athena_client = boto3.client('athena')
        self.athena_client.create_work_group(Name=os.getenv('workgroup'), Configuration={})
        # add sleep to make sure that the resource is created
        time.sleep(5)
        logger.info(f'{os.getenv("workgroup")} athena work group created')

    def test_lambda_handler(self):
        import lambda_run_athena_savedquery
        context = LambdaContextFnArn(
            'arn:aws:lambda:us-east-1:' + test_account_id + ':function:migration-factory-lab-test')
        workgroup = self.athena_client.get_work_group(WorkGroup=os.getenv('workgroup'))
        logger.info(f'In test_lambda_handler, retrieved workgroup - {workgroup}')
        response = lambda_run_athena_savedquery.lambda_handler(None, context)
        # the function doesn't return anything, so no validation with moto
        # can add test with patch that validate arguments called with
        self.assertIsNone(response)
