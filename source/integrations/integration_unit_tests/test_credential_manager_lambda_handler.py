#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from unittest.mock import patch

from test_credential_manager_base import CredentialManagerTestBase


class CredentialManagerLambdaHandlerTest(CredentialManagerTestBase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @patch('CredentialManager.ListSecret')
    def test_lambda_handler_get(self, mock_list_secret):
        import CredentialManager
        import ListSecret
        CredentialManager.lambda_handler(self.lambda_get_event, {})
        mock_list_secret.list.assert_called_once()

    @patch('CredentialManager.UpdateSecret')
    def test_lambda_handler_put(self, mock_update_secret):
        import CredentialManager
        import UpdateSecret
        CredentialManager.lambda_handler(self.lambda_put_event, {})
        mock_update_secret.update.assert_called_once()

    @patch('CredentialManager.DeleteSecret')
    def test_lambda_handler_delete(self, mock_delete_secret):
        import CredentialManager
        import DeleteSecret
        CredentialManager.lambda_handler(self.lambda_delete_event, {})
        mock_delete_secret.delete.assert_called_once()

    @patch('CredentialManager.CreateOsSecret')
    @patch('CredentialManager.CreateKeyValueSecret')
    @patch('CredentialManager.CreatePlainTextSecret')
    def test_lambda_handler_post(self, mock_create_plainText_secret, mock_create_keyValue_secret, mock_create_OS_secret):
        import CredentialManager
        import CreateOsSecret, CreateKeyValueSecret,  CreatePlainTextSecret
        CredentialManager.lambda_handler(self.lambda_post_OS_event, {})
        mock_create_OS_secret.create.assert_called_once()
        CredentialManager.lambda_handler(self.lambda_post_keyValue_event, {})
        mock_create_keyValue_secret.create.assert_called_once()
        CredentialManager.lambda_handler(self.lambda_post_plainText_event, {})
        mock_create_plainText_secret.create.assert_called_once()