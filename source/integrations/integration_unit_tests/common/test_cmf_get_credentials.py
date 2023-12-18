#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import botocore
import contextlib, io
from unittest import TestCase, mock
from common.test_mfcommon_util import default_mock_os_environ, mock_file_open, logger


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock.patch('builtins.open', new=mock_file_open)
class CMFGetCredentialsTestCase(TestCase):

    def setUp(self):
        self.secret_name = "test_secret"
        self.no_user_prompts = False

    def tearDown(self):
        pass

    def test_return_none_cached_secret(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_return_none_cached_secret")
        from mfcommon import return_cached_secret
        response = return_cached_secret(self.secret_name)
        print("Response: ", response)
        expected_response = None
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.credentials_store", {
             "cached_secret:test_secret": "test_cached_secret"
        })
    def test_return_valid_cached_secret(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_return_valid_cached_secret")
        from mfcommon import return_cached_secret
        response = return_cached_secret(self.secret_name)
        print("Response: ", response)
        expected_response = "test_cached_secret"
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.credentials_store", {
             "windows": "test_cached_secret"
        })
    def test_get_windows_server_credentials(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_windows_server_credentials")
        from mfcommon import get_windows_server_credentials
        response = get_windows_server_credentials(self.no_user_prompts)
        print("Response: ", response)
        expected_response = "test_cached_secret"
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.credentials_store", {
             "linux":"test_cached_secret"
        })
    def test_get_linux_server_credentials(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_linux_server_credentials")
        from mfcommon import get_linux_server_credentials
        response = get_linux_server_credentials(self.no_user_prompts)
        print("Response: ", response)
        expected_response = "test_cached_secret"
        self.assertEqual(response, expected_response)
   

    def test_handle_client_error_without_user_prompts(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_handle_client_error_without_user_prompts")
        from mfcommon import handle_credentials_client_error
        error = botocore.exceptions.ClientError({
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'oops'
            }
        }, 'testing')
        secret_name = "test_secret"
        no_user_prompts = True
        message = f"Secret not found [{secret_name}] doesn't exist or access is denied to Secret.\n"

        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io):
            handle_credentials_client_error(error, secret_name, no_user_prompts)
        response = str_io.getvalue()
        print("Response: ", response)
        expected_response = message
        self.assertEqual(response, expected_response)

    def test_handle_client_error_with_user_prompts(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_handle_client_error_with_user_prompts")
        from mfcommon import handle_credentials_client_error
        error = botocore.exceptions.ClientError({
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'oops'
            }
        }, 'testing')
        secret_name = "test_secret"
        no_user_prompts = False
        message = f"please enter username and password"

        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io):
            handle_credentials_client_error(error, secret_name, no_user_prompts)
        response = str_io.getvalue()
        print("Response: ", response)
        self.assertIn(message, response)

    def test_handle_client_error_with_unsupported_error_code(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_handle_client_error_with_user_prompts")
        from mfcommon import handle_credentials_client_error
        error = botocore.exceptions.ClientError({
            'Error': {
                'Code': 'other_test_error_code',
                'Message': 'oops'
            }
        }, 'testing')
        secret_name = "test_secret"
        no_user_prompts = False

        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io):
            handle_credentials_client_error(error, secret_name, no_user_prompts)
        response = str_io.getvalue()
        print("Response: ", response)
        expected_response = "{'Code': 'other_test_error_code', 'Message': 'oops'}\n"
        self.assertEqual(response, expected_response)

    @mock.patch("getpass.getpass", create=True)    
    def test_get_windows_password_with_matching_password(self, mock_getpass):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_windows_password_with_matching_password")
        from mfcommon import get_windows_password
        mock_getpass.side_effect = ["123456789", "123456789"]
        response = get_windows_password()
        print("Response: ", response)
        expected_response = "123456789"
        self.assertEqual(response, expected_response)
 
    @mock.patch("getpass.getpass", create=True)    
    def test_get_windows_password_with_mismatching_password(self, mock_getpass):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_windows_password_with_mismatching_password")
        from mfcommon import get_windows_password
        mock_getpass.side_effect = ["123456789", "12345", "123456789", "123456789"]
        response = get_windows_password()
        print("Response: ", response)
        expected_response = "123456789"
        self.assertEqual(response, expected_response)

    @mock.patch("builtins.input", create=True)    
    def test_get_linux_password_with_private_key(self, mock_input):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_windows_password_with_mismatching_password")
        from mfcommon import get_linux_password
        user_name = "test_user"
        has_key = "Y"
        pass_key = "test_key"
        mock_input.side_effect = [user_name, has_key, pass_key]
        user_name, pass_key, key_exist = get_linux_password()
        print(f"user_name: {user_name}, pass_key: {pass_key}, key_exist: {key_exist}")
        self.assertEqual(key_exist, True)
  
    def test_get_linux_password_without_private_key_but_having_matching_password(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_linux_password_without_private_key_but_having_matching_password")
        from mfcommon import get_linux_password
        user_name = "test_user"
        has_key = "N"
        pass_key = "test_key"
        with mock.patch("builtins.input") as mock_input, \
            mock.patch("getpass.getpass") as mock_getpass:
            mock_input.side_effect = [user_name, has_key, pass_key]
            mock_getpass.side_effect = ["123456789", "123456789"]
            user_name, pass_key, key_exist = get_linux_password()
            print(f"user_name: {user_name}, pass_key: {pass_key}, key_exist: {key_exist}")
            self.assertEqual(key_exist, False)

    def test_get_linux_password_without_private_key_and_matching_password(self):
        logger.info("Testing test_cmf_get_credentials: "
                    "test_get_linux_password_without_private_key_and_matching_password")
        from mfcommon import get_linux_password
        user_name = "test_user"
        has_key = "N"
        pass_key = "test_key"
        with mock.patch("builtins.input") as mock_input, \
            mock.patch("getpass.getpass") as mock_getpass:
            mock_input.side_effect = [user_name, has_key, pass_key]
            mock_getpass.side_effect = ["123456789", "12345", "123456789", "123456789"]
            user_name, pass_key, key_exist = get_linux_password()
            print(f"user_name: {user_name}, pass_key: {pass_key}, key_exist: {key_exist}")
            self.assertEqual(key_exist, False)
