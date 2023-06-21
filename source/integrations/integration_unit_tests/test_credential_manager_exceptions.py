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
from unittest.mock import patch

from test_credential_manager_base import CredentialManagerTestBase

import botocore.session
import botocore.errorfactory

model = botocore.session.get_session().get_service_model('secretsmanager')
factory = botocore.errorfactory.ClientExceptionsFactory()
exceptions = factory.create_client_exceptions(model)


# negative tests
class CredentialManagerNegativeTest(CredentialManagerTestBase):
    current_exception = None

    def setUp(self):
        super().setUp()
        self.mock_boto3_client = patch("boto3.client").start()

    def tearDown(self):
        super().tearDown()

    def mock_client(self, operation_name, kwarg) -> dict:
        if operation_name == "CreateSecret" and CredentialManagerNegativeTest.current_exception is not None:
            raise exceptions.ClientError({'Error': {'Code': CredentialManagerNegativeTest.current_exception}},
                                         'test-op')
        elif operation_name == "DeleteSecret" and CredentialManagerNegativeTest.current_exception is not None:
            raise exceptions.ClientError({'Error': {'Code': CredentialManagerNegativeTest.current_exception}},
                                         'test-op')
        elif operation_name == "GetSecretValue" and CredentialManagerNegativeTest.current_exception is not None:
            raise exceptions.ClientError({'Error': {'Code': CredentialManagerNegativeTest.current_exception}},
                                         'test-op')
        elif operation_name == "ListSecrets":
            return {
                'SecretList': [
                    {
                        'Name': 'secretName',
                    }
                ]
            }

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def assert_create_secret(self, creator, create_event):
        CredentialManagerNegativeTest.current_exception = 'ResourceExistsException'
        response = creator.create(create_event)
        self.assertEqual(response['statusCode'], 202)
        CredentialManagerNegativeTest.current_exception = 'AccessDeniedException'
        response = creator.create(create_event)
        self.assertEqual(response['statusCode'], 404)
        CredentialManagerNegativeTest.current_exception = 'InvalidRequestException'
        response = creator.create(create_event)
        self.assertEqual(response['statusCode'], 405)
        CredentialManagerNegativeTest.current_exception = 'ValidationException'
        response = creator.create(create_event)
        self.assertEqual(response['statusCode'], 405)
        CredentialManagerNegativeTest.current_exception = 'UnknownException'
        response = creator.create(create_event)
        self.assertEqual(response['statusCode'], 403)

    def test_create_os_secret_failure(self):
        from credential_manager.lambdas import CreateOsSecret
        self.assert_create_secret(CreateOsSecret, self.create_os_secret_event)

    def test_create_key_value_secret_failure(self):
        from credential_manager.lambdas import CreateKeyValueSecret
        self.assert_create_secret(CreateKeyValueSecret, self.create_key_value_secret_event)

    def test_create_plain_text_secret_failure(self):
        from credential_manager.lambdas import CreatePlainTextSecret
        self.assert_create_secret(CreatePlainTextSecret, self.create_plain_text_secret_event)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_delete_secret_failure(self):
        from credential_manager.lambdas import DeleteSecret
        CredentialManagerNegativeTest.current_exception = 'AccessDeniedException'
        response = DeleteSecret.delete(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_get_secret_failure(self):
        from credential_manager.lambdas import GetSecret
        CredentialManagerNegativeTest.current_exception = 'ResourceNotFoundException'
        response = GetSecret.get(self.get_secret_event)
        self.assertEqual(response['statusCode'], 404)
        CredentialManagerNegativeTest.current_exception = 'AccessDeniedException'
        response = GetSecret.get(self.get_secret_event)
        self.assertEqual(response['statusCode'], 404)
        CredentialManagerNegativeTest.current_exception = 'InvalidRequestException'
        response = GetSecret.get(self.get_secret_event)
        self.assertEqual(response['statusCode'], 404)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_list_secrets_failure(self):
        from credential_manager.lambdas import ListSecret
        CredentialManagerNegativeTest.current_exception = 'InternalServiceError'
        response = ListSecret.list({})
        self.assertEqual(response['statusCode'], 500)
        CredentialManagerNegativeTest.current_exception = 'InvalidNextTokenException'
        response = ListSecret.list({})
        self.assertEqual(response['statusCode'], 400)
        CredentialManagerNegativeTest.current_exception = 'InvalidParameterException'
        response = ListSecret.list({})
        self.assertEqual(response['statusCode'], 400)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_update_secret_failure(self):
        from credential_manager.lambdas import UpdateSecret
        CredentialManagerNegativeTest.current_exception = 'ResourceNotFoundException'
        response = UpdateSecret.update(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)
        CredentialManagerNegativeTest.current_exception = 'AccessDeniedException'
        response = UpdateSecret.update(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)
