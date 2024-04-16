#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import boto3
from moto import mock_aws

from credential_manager.test_credential_manager_base import CredentialManagerTestBase


# positive tests with moto
@mock_aws
class CredentialManagerTest(CredentialManagerTestBase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_crud_os_secret(self):
        # test create, read, delete operations
        import CreateOsSecret, UpdateSecret, DeleteSecret
        # create one secret through the solutions api, which will be tagged accordingly
        CreateOsSecret.create(self.create_os_secret_event)
        self.assert_get_secrets('secretName')
        # update the secret through the solutions api
        UpdateSecret.update(self.create_os_secret_event_updated)
        # check if it's updated
        self.assert_secret_was_updated('USERNAME', 'testUserUpdated')
        # update the secret through the solutions api 2
        UpdateSecret.update(self.create_os_secret_event_2)
        # check if it's updated
        self.assert_secret_was_updated('USERNAME', 'testUserUpdated')
        # check if it's deleted
        DeleteSecret.delete(self.create_os_secret_event)
        self.assert_secret_was_deleted()

    def test_crud_key_value_secret(self):
        import CreateKeyValueSecret, UpdateSecret, DeleteSecret
        # create one secret through the solutions api, which will be tagged accordingly
        CreateKeyValueSecret.create(self.create_key_value_secret_event)
        self.assert_get_secrets('secretName')
        # update the secret through the solutions api
        UpdateSecret.update(self.create_key_value_secret_event_updated)
        # check if it's updated
        self.assert_secret_was_updated('SECRET_KEY', 'secretKeyUpdated')
        # check if it's deleted
        DeleteSecret.delete(self.create_key_value_secret_event)
        self.assert_secret_was_deleted()

    def test_crud_plain_text_secret(self):
        import CreatePlainTextSecret, UpdateSecret, DeleteSecret
        # create one secret through the solutions api, which will be tagged accordingly
        CreatePlainTextSecret.create(self.create_plain_text_secret_event)
        self.assert_get_secrets('secretName')
        # update the secret through the solutions api
        UpdateSecret.update(self.create_plain_text_secret_event_updated)
        # check if it's updated
        self.assert_secret_was_updated('SECRET_STRING', '*********')
        # check if it's deleted
        DeleteSecret.delete(self.create_plain_text_secret_event)
        self.assert_secret_was_deleted()

    def assert_get_secrets(self, solution_secret_name):
        import ListSecret
        # create another secret directly through the secrets manager api
        client_secrets_manager = boto3.client('secretsmanager')
        client_secrets_manager.create_secret(Name='secretName2', SecretString='secretString2')
        # should return both the tagged and untagged secrets
        all_secrets = client_secrets_manager.list_secrets()
        self.assertEqual(len(all_secrets['SecretList']), 2)
        # should only return the tagged secret
        solution_secrets = json.loads((ListSecret.list())['body'])
        self.assertEqual(len(solution_secrets), 1)
        self.assertEqual(solution_secrets[0]['Name'], solution_secret_name)

    def assert_secret_was_updated(self, key, value):
        import GetSecret
        read_secret = GetSecret.get(self.get_secret_event)
        secret_body = json.loads(read_secret['body'])
        self.assertEqual(secret_body[key], value)

    def assert_secret_was_deleted(self):
        import GetSecret
        read_secret = GetSecret.get(self.get_secret_event)
        self.assertEqual(read_secret['statusCode'], 404)

    def test_delete_non_existent(self):
        import DeleteSecret
        response = DeleteSecret.delete(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)

    def test_update_non_existent(self):
        import UpdateSecret
        response = UpdateSecret.update(self.create_os_secret_event)
        self.assertEqual(response['statusCode'], 404)
