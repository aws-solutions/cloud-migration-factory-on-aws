#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
from unittest.mock import patch
from moto import mock_aws


from test_common_utils import logger
from test_lambda_cognito_base import exceptions as boto_core_exceptions, CognitoTestsBase

import lambda_cognito_group_update


class LambdaCognitoGroupUpdateTest(CognitoTestsBase):
    current_test_client = None

    def setUp(self):
        super().setUp()

    @mock_aws
    def test_lambda_handler_delete_no_body(self):
        # create a group
        # send DELETE event
        # assert that there are no groups
        self.create_user_pool()
        self.create_group(self.test_group_name_1)
        lambda_event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'group_name': self.test_group_name_1
            }
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        groups = self.boto_cognito_client.list_groups(UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual([], groups['Groups'])

    @mock_aws
    def test_lambda_handler_delete_non_existing(self):
        # send DELETE event with no groups existing
        # assert that a ClientError (ResourceNotFoundException)  exception is thrown
        self.create_user_pool()
        lambda_event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'group_name': self.test_group_name_1
            }
        }
        self.assertRaises(boto_core_exceptions.ClientError,
                          lambda_cognito_group_update.lambda_handler,
                          lambda_event, None)
        with self.assertRaises(boto_core_exceptions.ClientError) as ex:
            lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual('ResourceNotFoundException', ex.exception.response['Error']['Code'])

    @mock_aws
    def test_lambda_handler_post_with_body(self):
        # send POST event with two groups
        # asser that two groups are created
        self.create_user_pool()
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name': self.test_group_name_1
                    },
                    {
                        'group_name': self.test_group_name_2
                    },
                ],
            }),
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(200, response['statusCode'])
        groups = self.boto_cognito_client.list_groups(UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(2, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_post_with_body_error(self):
        # send POST with one correct group and another faulty
        # the correct group has an extra attribute which would be ignored
        # assert that response is 400 with error message
        # assert that one group is created
        self.create_user_pool()
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name_wrong': self.test_group_name_1
                    },
                    {
                        'group_name': self.test_group_name_2,
                        'extra_attribute': 'all extra attributes are ignored by the code'
                    },
                ],
            }),
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'group_name not provided for group object in provided'
        error_message = json.loads(response['body'])[0]
        self.assertTrue(error_message.startswith(expected_error_message))
        groups = self.boto_cognito_client.list_groups(UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(1, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_post_with_body_group_exists(self):
        # create a group
        # send POST with two groups, one of them the above
        # assert that response is 400 with error message
        # assert that two groups are created
        self.create_user_pool()
        self.create_group(self.test_group_name_1)
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name': self.test_group_name_1
                    },
                    {
                        'group_name': self.test_group_name_2
                    },
                ],
            }),
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'A group already exists with the name'
        error_message = json.loads(response['body'])[0]
        self.assertTrue(error_message.startswith(expected_error_message))
        groups = self.boto_cognito_client.list_groups(UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(2, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_post_with_body_group_exists_twice(self):
        # create a group
        # send POST with two groups, one of them the above
        # assert that response is 400 with error message
        # assert that two groups are created
        self.create_user_pool()
        self.create_group(self.test_group_name_1)
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name': self.test_group_name_1
                    },
                    {
                        'group_name': self.test_group_name_1
                    },
                    {
                        'group_name': self.test_group_name_2
                    },
                ],
            }),
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'A group already exists with the name'
        error_message = json.loads(response['body'])
        error_message_0 = error_message[0]
        error_message_1 = error_message[1]
        self.assertTrue(error_message_0.startswith(expected_error_message))
        self.assertTrue(error_message_1.startswith(expected_error_message))
        groups = self.boto_cognito_client.list_groups(UserPoolId=self.user_pool_id, Limit=10)
        self.assertEqual(2, len(groups['Groups']))

    @mock_aws
    def test_lambda_handler_other_http_verbs_and_unexpected(self):
        self.create_user_pool()
        self.create_group(self.test_group_name_1)

        # unexpected http verbs
        lambda_event = {
            'httpMethod': 'GET',
        }
        self.assertRaises(Exception, lambda_cognito_group_update.lambda_handler, lambda_event, None)
        lambda_event['httpMethod'] = 'PUT'
        self.assertRaises(Exception, lambda_cognito_group_update.lambda_handler, lambda_event, None)
        lambda_event['httpMethod'] = 'PATCH'
        self.assertRaises(Exception, lambda_cognito_group_update.lambda_handler, lambda_event, None)

        # expected http verbs with incomplete body
        lambda_event['httpMethod'] = 'DELETE'
        self.assertRaises(Exception, lambda_cognito_group_update.lambda_handler, lambda_event, None)
        lambda_event['httpMethod'] = 'POST'
        self.assertRaises(Exception, lambda_cognito_group_update.lambda_handler, lambda_event, None)

    def mock_boto_api_call(self, operation_name, kwarg):
        logger.debug(f"operation_name = {operation_name}, kwarg = {kwarg}")
        if operation_name == 'CreateUserPool':
            return {
                'UserPool': {
                    'Id': 'ID123',
                }
            }
        elif operation_name == 'DeleteGroup':
            raise boto_core_exceptions.ClientError({
                'Error': {
                    'Code': 500,
                    'Message': 'UnExpected Error'
                }
            }, operation_name)
        elif operation_name == 'CreateGroup' and kwarg['GroupName'] == 'NotAuthorizedException':
            raise LambdaCognitoGroupUpdateTest.current_test_client.exceptions.NotAuthorizedException({
                'Error': {
                    'Code': 500,
                    'Message': 'Simulated unauthorized exception'
                }
            }, operation_name)
        elif operation_name == 'CreateGroup' and kwarg['GroupName'] == 'ClientError':
            raise boto_core_exceptions.ClientError({
                'Error': {
                    'Code': 500,
                    'Message': 'Simulated client error'
                }
            }, operation_name)
        elif operation_name == 'CreateGroup' and kwarg['GroupName'] == 'UnknownError':
            raise Exception({
                'Error': {
                    'Code': 500,
                    'Message': 'Simulated un expected error'
                }
            }, operation_name)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_unhandled_delete(self):
        self.create_user_pool()
        self.create_group(self.test_group_name_1)
        lambda_event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'group_name': self.test_group_name_1
            }
        }
        self.assertRaises(boto_core_exceptions.ClientError, lambda_cognito_group_update.lambda_handler,
                          lambda_event, None)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_not_authorized(self):
        # if the aws api call fails for 'DELETE' no error handing added
        # tests that the lambda throws the unhandled exception
        self.create_user_pool()
        LambdaCognitoGroupUpdateTest.current_test_client = self.boto_cognito_client
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name': 'NotAuthorizedException'
                    },
                ],
            }),
        }
        self.assertRaises(self.boto_cognito_client.exceptions.NotAuthorizedException,
                          lambda_cognito_group_update.lambda_handler,
                          lambda_event, None)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_client_error(self):
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name': 'ClientError'
                    },
                ],
            }),
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'Internal error.'
        error_message = json.loads(response['body'])[0]
        self.assertEqual(expected_error_message, error_message)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
    def test_lambda_handler_exceptions_unknown_error(self):
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'groups': [
                    {
                        'group_name': 'UnknownError'
                    },
                ],
            }),
        }
        response = lambda_cognito_group_update.lambda_handler(lambda_event, None)
        self.assertEqual(400, response['statusCode'])
        expected_error_message = 'Internal error.'
        error_message = json.loads(response['body'])[0]
        self.assertEqual(expected_error_message, error_message)
