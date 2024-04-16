#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
from unittest.mock import patch
from moto import mock_aws

from test_common_utils import logger
from test_lambda_cognito_base import exceptions as boto_core_exceptions, CognitoTestsBase

import lambda_cognito_user_update


class LambdaCognitoUserUpdateTest(CognitoTestsBase):
    current_test_client = None

    def setUp(self):
        super().setUp()

    def initialize_user_pool(self):
        """
        creates the following before the tests are run
            - a user pool
            - three user groups
            - one user
            - adds the user to two groups
        """
        self.create_user_pool()
        self.create_group(self.test_group_name_1)
        self.create_group(self.test_group_name_2)
        self.create_group(self.test_group_name_3)
        self.create_user(self.test_user_name_1)
        self.add_user_to_group(self.test_user_name_1, self.test_group_name_1)
        self.add_user_to_group(self.test_user_name_1, self.test_group_name_2)

    @mock_aws
    def test_lambda_handler_groups(self):
        # user in two existing groups
        # request comes with two groups (one from the existing groups, and a new one)
        # the new state should be, user will be a member of two groups i.e. one of the existing will be removed
        self.initialize_user_pool()
        lambda_event = {
            'body': json.dumps({
                'users': [
                    {
                    'username': self.test_user_name_1,
                    'userpool_id': self.user_pool_id,
                    'groups': [
                        self.test_group_name_1,
                        self.test_group_name_3,
                    ]
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        groups = self.boto_cognito_client.admin_list_groups_for_user(Username=self.test_user_name_1,
                                                                     UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(2, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_add_groups(self):
        # user in two existing groups
        # request comes with two addGroups, one of which already exists
        # the new state should be, user will be a member of three groups
        self.initialize_user_pool()
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': self.test_user_name_1,
                        'userpool_id': self.user_pool_id,
                        'addGroups': [
                            self.test_group_name_1,
                            self.test_group_name_3,
                        ]
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        groups = self.boto_cognito_client.admin_list_groups_for_user(Username=self.test_user_name_1,
                                                                     UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(3, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_remove_groups(self):
        # user in two existing groups
        # request comes with two removeGroups, one of which already exists
        # the new state should be, user will be a member of one group
        self.initialize_user_pool()
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': self.test_user_name_1,
                        'userpool_id': self.user_pool_id,
                        'removeGroups': [
                            self.test_group_name_1,
                            self.test_group_name_3,
                        ]
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        groups = self.boto_cognito_client.admin_list_groups_for_user(Username=self.test_user_name_1,
                                                                     UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(1, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_enable_user(self):
        # create two users
        # invoke with one enabled True and another False
        # assert the Enabled states of the users
        self.create_user_pool()
        self.create_user(self.test_user_name_1)
        self.create_user(self.test_user_name_2)
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': self.test_user_name_1,
                        'userpool_id': self.user_pool_id,
                        'enabled': True
                    },
                    {
                        'username': self.test_user_name_2,
                        'userpool_id': self.user_pool_id,
                        'enabled': False
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        user1 = self.boto_cognito_client.admin_get_user(UserPoolId=self.user_pool_id, Username=self.test_user_name_1)
        self.assertEqual(True, user1['Enabled'])
        user2 = self.boto_cognito_client.admin_get_user(UserPoolId=self.user_pool_id, Username=self.test_user_name_2)
        self.assertEqual(False, user2['Enabled'])

    @mock_aws
    def test_lambda_handler_delete_user(self):
        # create two users
        # invoke with one delete True
        # assert the only one user remains
        self.create_user_pool()
        self.create_user(self.test_user_name_1)
        self.create_user(self.test_user_name_2)
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': self.test_user_name_1,
                        'userpool_id': self.user_pool_id,
                        'delete': True
                    },
                    {
                        'username': self.test_user_name_2,
                        'userpool_id': self.user_pool_id,
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        users = self.boto_cognito_client.list_users(UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(1, len(users['Users']))

    @mock_aws
    def test_lambda_handler_user_not_found(self):
        # create one user
        # invoke with one enabled True/False, including a second user
        # assert that 400 with the appropriate error is returned
        # the operation on the existing user succeeds though
        self.create_user_pool()
        self.create_user(self.test_user_name_1)
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': self.test_user_name_1,
                        'userpool_id': self.user_pool_id,
                        'enabled': True
                    },
                    {
                        'username': self.test_user_name_2,
                        'userpool_id': self.user_pool_id,
                        'enabled': False
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = f"User '{self.test_user_name_2}'  does not exist , skipping user updates."
        error_message = json.loads(response['body'])[0]
        self.assertEqual(expected_error_message, error_message)

    def mock_boto_api_call(self, operation_name, kwarg):
        logger.info(f"operation_name = {operation_name}, kwarg = {kwarg}")
        if operation_name == 'CreateUserPool':
            return {
                'UserPool': {
                    'Id': 'ID123',
                }
            }
        elif operation_name == 'AdminListGroupsForUser':
            return {
                'Groups': []
            }
        elif operation_name == 'AdminEnableUser' and kwarg['Username'] == 'NotAuthorizedException':
            raise LambdaCognitoUserUpdateTest.current_test_client.exceptions.NotAuthorizedException({
                'Error': {
                    'Code': 500,
                    'Message': 'Simulated unauthorized exception'
                }
            }, operation_name)
        elif operation_name == 'AdminEnableUser' and kwarg['Username'] == 'ClientError':
            raise boto_core_exceptions.ClientError({
                'Error': {
                    'Code': 500,
                    'Message': 'Simulated client error'
                }
            }, operation_name)
        elif operation_name == 'AdminEnableUser' and kwarg['Username'] == 'UnknownError':
            raise Exception({
                'Error': {
                    'Code': 500,
                    'Message': 'Simulated un expected error'
                }
            }, operation_name)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_not_authorized(self):
        # create a user
        # invoke with one enabled True/False
        # patch object raises NotAuthorizedException exception
        # assert the exception is thrown
        self.create_user_pool()
        self.create_user(self.test_user_name_1)
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': 'NotAuthorizedException',
                        'userpool_id': self.user_pool_id,
                        'enabled': True
                    },
                ]
            })
        }
        LambdaCognitoUserUpdateTest.current_test_client = self.boto_cognito_client
        self.assertRaises(self.boto_cognito_client.exceptions.NotAuthorizedException,
                          lambda_cognito_user_update.lambda_handler,
                          lambda_event, None)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_client_error(self):
        # create a user
        # invoke with one enabled True/False
        # patch object raises ClientError
        # assert no exception, but error in the response
        self.create_user_pool()
        self.create_user(self.test_user_name_1)
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': 'ClientError',
                        'userpool_id': self.user_pool_id,
                        'enabled': True
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'Internal error.'
        error_message = json.loads(response['body'])[0]
        self.assertEqual(expected_error_message, error_message)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_unknown_error(self):
        # create a user
        # invoke with one enabled True/False
        # patch object raises unexpected / unknown error
        # assert no exception, but error in the response
        self.create_user_pool()
        self.create_user(self.test_user_name_1)
        lambda_event = {
            'body': json.dumps({
                'users': [{
                        'username': 'UnknownError',
                        'userpool_id': self.user_pool_id,
                        'enabled': True
                    },
                ]
            })
        }
        response = lambda_cognito_user_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'Internal error.'
        error_message = json.loads(response['body'])[0]
        self.assertEqual(expected_error_message, error_message)
