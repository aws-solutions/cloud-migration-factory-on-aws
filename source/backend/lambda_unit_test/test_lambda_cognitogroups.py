#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import unittest
from moto import mock_aws
import boto3

import test_common_utils


class LambdaCognitoGroupsTest(unittest.TestCase):

    @mock_aws
    def assert_lambda_handler(self):
        import lambda_cognitogroups
        test_client = boto3.client('cognito-idp')
        user_pool_id = test_client.create_user_pool(PoolName='testPool')['UserPool']['Id']
        test_group_name = 'testUserGroup'
        test_client.create_group(
            GroupName=test_group_name,
            UserPoolId=user_pool_id,
        )
        os.environ['userpool_id'] = user_pool_id
        response = lambda_cognitogroups.lambda_handler({}, {})
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(json.dumps([test_group_name]), response['body'])

    def test_lambda_handler(self):
        self.assert_lambda_handler()

    def test_lambda_handler_with_cors_set(self):
        import os
        os.environ['cors'] = '*'
        self.assert_lambda_handler()
