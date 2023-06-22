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


import unittest
import json
import os

import boto3
from moto import mock_cognitoidp
import common_utils


common_utils.init()
logger = common_utils.logger


class LambdaLoginTest(unittest.TestCase):

    @classmethod
    def setUp(self):
        self.user_name = 'testUserName'
        self.temporary_password = 'P2$Sword'
        self.mfa_code = 'testMfaCode'
        self.session = 'testSession'
        self.pool_name = 'testuserPool'
        self.client_name = 'testClientName'
        self.attribute1_name = 'testAttributeName'
        self.new_password = "P2$Sword"

    def create_cognito_user(self):
        test_client = boto3.client('cognito-idp')
        user_pool_id = test_client.create_user_pool(PoolName=self.pool_name)['UserPool']['Id']
        client_id = test_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=self.client_name,
            ReadAttributes=[self.attribute1_name],
            GenerateSecret=True,
        )['UserPoolClient']['ClientId']
        os.environ['clientId'] = client_id
        test_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=self.user_name,
            TemporaryPassword=self.temporary_password,
            UserAttributes=[{'Name': 'User Name', 'Value': self.attribute1_name}],
        )

        result = test_client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": self.user_name, "PASSWORD": self.temporary_password},
        )
        result = test_client.respond_to_auth_challenge(
            Session=result["Session"],
            ClientId=client_id,
            ChallengeName="NEW_PASSWORD_REQUIRED",
            ChallengeResponses={"USERNAME": self.user_name, "NEW_PASSWORD": self.new_password},
        )
        logger.debug(result)
        result = test_client.admin_user_global_sign_out(
            UserPoolId=user_pool_id,
            Username=self.user_name
        )
        logger.debug(result)

    @mock_cognitoidp
    def test_lambda_login_with_password(self):
        import lambda_login
        self.create_cognito_user()
        event = {
            'body': json.dumps({
                'username': self.user_name,
                'password': self.new_password,
                'session': self.session,
            })
        }

        response = lambda_login.lambda_handler(event, {})
        self.assertEqual(200, response['statusCode'])

