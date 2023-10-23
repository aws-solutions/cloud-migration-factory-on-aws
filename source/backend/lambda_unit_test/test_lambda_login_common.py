#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from test_common_utils import logger
import botocore

model = botocore.session.get_session().get_service_model('cognito-idp')
factory = botocore.errorfactory.ClientExceptionsFactory()
exceptions = factory.create_client_exceptions(model)


def mock_boto_api_call_success(client, operation_name, kwarg):
    logger.info(f'client = {client}, operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'InitiateAuth':
        return {
            'ChallengeName': 'NEW_PASSWORD_REQUIRED',
            'Session': 'TEST_SESSION'
        }
    if operation_name == 'RespondToAuthChallenge':
        return {
            'AuthenticationResult': {
                'IdToken': 'TOKEN_123'
            }
        }


def mock_boto_api_call_incorrect_chanllenge(client, operation_name, kwarg):
    logger.info(f'client = {client}, operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'InitiateAuth':
        return {
            'ChallengeName': 'NEW_PASSWORD_REQUIRED_INCORRECT',
            'Session': 'TEST_SESSION'
        }


def mock_boto_api_call_exception(client, operation_name, kwarg):
    logger.info(f'client = {client}, operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'InitiateAuth':
        raise exceptions.ClientError({'Error': {'Code': 'NotAuthorizedException'}},
                                     'test-op')


def mock_boto_api_call_exception_unexpected(client, operation_name, kwarg):
    logger.info(f'client = {client}, operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'InitiateAuth':
        raise exceptions.ClientError({'Error': {'Code': 'UnExpectedException'}},
                                     'test-op')


def mock_boto_api_call_next_challenge(client, operation_name, kwarg):
    logger.info(f'client = {client}, operation_name = {operation_name}, kwarg = {kwarg}')
    if operation_name == 'InitiateAuth':
        return {
            'ChallengeName': 'NEW_PASSWORD_REQUIRED',
            'Session': 'TEST_SESSION'
        }
    if operation_name == 'RespondToAuthChallenge':
        return {
            'AuthenticationResult': {
                'IdToken': 'TOKEN_123'
            }
        }
