#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from unittest.mock import patch

from credential_manager.test_credential_manager_base import CredentialManagerTestBase

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
        import CreateOsSecret
        self.assert_create_secret(CreateOsSecret, self.create_os_secret_event)

    def test_create_key_value_secret_failure(self):
        import CreateKeyValueSecret
        self.assert_create_secret(CreateKeyValueSecret, self.create_key_value_secret_event)

    def test_create_plain_text_secret_failure(self):
        import CreatePlainTextSecret
        self.assert_create_secret(CreatePlainTextSecret, self.create_plain_text_secret_event)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_delete_secret_failure(self):
        import DeleteSecret
        CredentialManagerNegativeTest.current_exception = 'AccessDeniedException'
        response = DeleteSecret.delete(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_get_secret_failure(self):
        import GetSecret
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
        import ListSecret
        CredentialManagerNegativeTest.current_exception = 'InternalServiceError'
        response = ListSecret.list()
        self.assertEqual(response['statusCode'], 500)
        CredentialManagerNegativeTest.current_exception = 'InvalidNextTokenException'
        response = ListSecret.list()
        self.assertEqual(response['statusCode'], 400)
        CredentialManagerNegativeTest.current_exception = 'InvalidParameterException'
        response = ListSecret.list()
        self.assertEqual(response['statusCode'], 400)

    @patch('botocore.client.BaseClient._make_api_call', new=mock_client)
    def test_update_secret_failure(self):
        import UpdateSecret
        CredentialManagerNegativeTest.current_exception = 'ResourceNotFoundException'
        response = UpdateSecret.update(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)
        CredentialManagerNegativeTest.current_exception = 'AccessDeniedException'
        response = UpdateSecret.update(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)
