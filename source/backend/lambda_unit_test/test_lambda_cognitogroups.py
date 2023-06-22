#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################


import json
import os
import unittest
from moto import mock_cognitoidp
import boto3

import common_utils

common_utils.init()
logger = common_utils.logger


class LambdaCognitoGroupsTest(unittest.TestCase):

    @mock_cognitoidp
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
