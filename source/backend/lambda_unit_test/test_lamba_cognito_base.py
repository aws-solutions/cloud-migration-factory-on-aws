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
import os
import boto3

import botocore.session
import botocore.errorfactory

model = botocore.session.get_session().get_service_model('cognito-idp')
factory = botocore.errorfactory.ClientExceptionsFactory()
exceptions = factory.create_client_exceptions(model)


class CognitoTestsBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_group_name_1 = 'testUserGroup1'
        cls.test_group_name_2 = 'testUserGroup2'
        cls.test_group_name_3 = 'testUserGroup3'
        cls.test_user_name_1 = 'testUserName1'
        cls.test_user_name_2 = 'testUserName2'

    def setUp(self):
        super().setUp()
        self.boto_cognito_client = boto3.client('cognito-idp')
        self.user_pool_id = None

    def create_user_pool(self):
        user_pool_id = self.boto_cognito_client.create_user_pool(PoolName='testPool')['UserPool']['Id']
        os.environ['userpool_id'] = user_pool_id
        self.user_pool_id = user_pool_id

    def create_group(self, group_name):
        self.boto_cognito_client.create_group(GroupName=group_name, UserPoolId=self.user_pool_id)

    def create_user(self, user_name):
        self.boto_cognito_client.admin_create_user(UserPoolId=self.user_pool_id, Username=user_name)

    def add_user_to_group(self, user_name, group_name):
        self.boto_cognito_client.admin_add_user_to_group(UserPoolId=self.user_pool_id, Username=user_name,
                                                         GroupName=group_name)
