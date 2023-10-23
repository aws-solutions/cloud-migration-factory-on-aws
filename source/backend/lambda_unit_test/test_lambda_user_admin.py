#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
from unittest import mock

from test_lambda_cognito_base import CognitoTestsBase

from moto import mock_cognitoidp
from test_common_utils import set_cors_flag, default_mock_os_environ


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_cognitoidp
class LambdaUserAdminTest(CognitoTestsBase):

    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        super().setUp()
        self.create_user_pool()

    def create_user_pool_and_user(self):
        self.create_group(self.test_group_name_1)
        self.create_user(self.test_user_name_1)
        self.create_user_with_software_token_mfa(self.test_user_name_2)
        self.create_user_with_sms_mfa(self.test_user_name_3)
        self.add_user_to_group(self.test_user_name_1, self.test_group_name_1)

    def set_global_vars(self, module_imported):
        module_imported.PoolId = self.user_pool_id
        module_imported.CognitoGroup = self.test_group_name_1

    def set_env_vars(self):
        os.environ['userpool_id'] = self.user_pool_id
        os.environ['CognitoGroupName'] = self.test_group_name_1

    def test_lambda_handler_success(self):
        set_cors_flag('lambda_user_admin', True)
        import lambda_user_admin
        self.create_user_pool_and_user()
        self.set_env_vars()
        response = lambda_user_admin.lambda_handler(None, None)
        self.assertEqual(200, response['statusCode'])
        users_created = json.loads(response['body'])
        self.assertEqual(3, len(users_created))
        users_created = sorted(users_created, key=lambda item: item['userRef'])
        user_name = users_created[0]['userRef']
        mfa_enabled = users_created[0]['mfaEnabled']
        self.assertEqual(self.test_user_name_1, user_name)
        self.assertEqual(False, mfa_enabled)
        user_name = users_created[1]['userRef']
        mfa_enabled = users_created[1]['mfaEnabled']
        self.assertEqual(self.test_user_name_2, user_name)
        self.assertEqual(False, mfa_enabled)
        user_name = users_created[2]['userRef']
        mfa_enabled = users_created[2]['mfaEnabled']
        self.assertEqual(self.test_user_name_3, user_name)
        self.assertEqual(False, mfa_enabled)

    def test_lambda_handler_success_no_users(self):
        set_cors_flag('lambda_user_admin', False)
        import lambda_user_admin
        response = lambda_user_admin.lambda_handler(None, None)
        self.assertEqual(200, response['statusCode'])
        users_created = json.loads(response['body'])
        self.assertEqual(0, len(users_created))
