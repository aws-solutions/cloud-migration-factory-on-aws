#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
import os
import boto3

import botocore.session
import botocore.errorfactory


model = botocore.session.get_session().get_service_model('cognito-idp')
factory = botocore.errorfactory.ClientExceptionsFactory()
exceptions = factory.create_client_exceptions(model)


class CognitoTestsBase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.boto_cognito_client = boto3.client('cognito-idp')
        self.user_pool_id = None
        self.client_name = 'testClientName'
        self.attribute1_name = 'testAttributeName'
        self.temporary_password = 'P2$Sword'
        self.new_password = ''.join(reversed(self.temporary_password))
        self.test_group_name_1 = 'testUserGroup1'
        self.test_group_name_2 = 'testUserGroup2'
        self.test_group_name_3 = 'testUserGroup3'
        self.test_user_name_1 = 'testUserName1'
        self.test_user_name_2 = 'testUserName2'
        self.test_user_name_3 = 'testUserName3'

    def create_user_pool(self):
        user_pool_id = self.boto_cognito_client.create_user_pool(PoolName='testPool',
                                                                 MfaConfiguration='OPTIONAL',
                                                                 AutoVerifiedAttributes=['email'])['UserPool']['Id']
        os.environ['userpool_id'] = user_pool_id
        self.user_pool_id = user_pool_id

    def create_group(self, group_name):
        self.boto_cognito_client.create_group(GroupName=group_name, UserPoolId=self.user_pool_id)

    def create_user(self, user_name):
        self.boto_cognito_client.admin_create_user(UserPoolId=self.user_pool_id, Username=user_name)

    def create_user_with_software_token_mfa(self, user_name):
        (access_token, current_session) = self.create_verified_user(user_name)
        self.boto_cognito_client.associate_software_token(
            AccessToken=access_token,
            Session=current_session
        )
        self.boto_cognito_client.verify_software_token(
            AccessToken=access_token,
            Session=current_session,
            UserCode='ABCDEFG'
        )
        self.boto_cognito_client.admin_set_user_mfa_preference(
            Username=user_name,
            UserPoolId=self.user_pool_id,
            SoftwareTokenMfaSettings={
                'Enabled': True,
                'PreferredMfa': True
            }
        )

    def create_verified_user(self, user_name):
        """
        creates user, verifies it by changing password
        returns the access token and session
        """
        client_id = self.boto_cognito_client.create_user_pool_client(
            UserPoolId=self.user_pool_id,
            ClientName=self.client_name,
            ReadAttributes=[self.attribute1_name],
            GenerateSecret=True,
        )['UserPoolClient']['ClientId']
        os.environ['clientId'] = client_id
        self.boto_cognito_client.admin_create_user(
            UserPoolId=self.user_pool_id,
            Username=user_name,
            TemporaryPassword=self.temporary_password,
            UserAttributes=[
                {
                    'Name': 'phone_number',
                    'Value': '11111111111'
                },
                {
                    'Name': 'phone_number_verified',
                    'Value': 'True'
                },
                {
                    'Name': 'email',
                    'Value': 'email@example.com'
                },
                {
                    'Name': 'User Name',
                    'Value': self.attribute1_name
                }
            ],
        )
        response = self.boto_cognito_client.admin_initiate_auth(
            UserPoolId=self.user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": user_name,
                            "PASSWORD": self.temporary_password},
        )
        current_session = response["Session"]
        response = self.boto_cognito_client.respond_to_auth_challenge(
            Session=current_session,
            ClientId=client_id,
            ChallengeName="NEW_PASSWORD_REQUIRED",
            ChallengeResponses={"USERNAME": user_name,
                                "NEW_PASSWORD": self.new_password},
        )
        return response['AuthenticationResult']['AccessToken'], current_session

    def create_user_with_sms_mfa(self, user_name):
        self.create_verified_user(user_name)
        response = self.boto_cognito_client.admin_set_user_mfa_preference(
            Username=user_name,
            UserPoolId=self.user_pool_id,
            SMSMfaSettings={
                'Enabled': True,
                'PreferredMfa': True
            }
        )

    def add_user_to_group(self, user_name, group_name):
        self.boto_cognito_client.admin_add_user_to_group(UserPoolId=self.user_pool_id, Username=user_name,
                                                         GroupName=group_name)
