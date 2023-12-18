#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from moto import mock_secretsmanager
from unittest import TestCase, mock
from common.test_mfcommon_util import default_mock_os_environ, \
    load_default_config_file, \
    set_up_secret_manager, mock_file_open, logger


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock.patch('builtins.open', new=mock_file_open)
@mock_secretsmanager
class CMFUserLoginTestCase(TestCase):
    def setUp(self):
        self.mf_config = load_default_config_file("FactoryEndpoints.json")
        self.secretsmanager_client, \
            self.service_account_email, \
            self.secret_id, \
            self.secret_string = \
            set_up_secret_manager(self.mf_config, False, "test@example.com")

    def tearDown(self):
        self.secretsmanager_client.delete_secret(
            SecretId=self.secret_id)
        self.secretsmanager_client = None

    def mock_successful_factory_login_with_cognito_user_pool(self, *args):
        logger.info("Testing test_cmf_user_login: "
                    "mock_successful_factory_login_with_cognito_user_pool")
        response = {
            "statusCode": 200,
            "body": '"eyJhbGciOiJSUzI1NiIsImtpZCI6ImR1bW15I"'
        }
        return response

    def mock_failed_factory_login_with_cognito_user_pool(self, *args):
        logger.info("Testing test_cmf_user_login: "
                    "mock_failed_factory_login_with_cognito_user_pool")
        response = {
            "statusCode": 502,
            "body": '"eyJhbGciOiJSUzI1NiIsImtpZCI6ImR1bW15I"'
        }
        return response
    
    def mock_failed_factory_login_with_cognito_user_pool_with_other_status_code(self, *args):
        logger.info("Testing test_cmf_user_login: "
                    "mock_failed_factory_login_with_cognito_user_pool_with_other_status_code")
        response = {
            "statusCode": 999,
            "text": "login failed due to unidentified reason"
        }
        return response
    
    def mock_get_login_response(self, *args):
        logger.info("Testing test_cmf_user_login: mock_get_login_response")
        userid = "test@example.com"
        response = {
            "ChallengeName": "NEW_PASSWORD_REQUIRED"
        }
        return response, userid
    
    def test_get_login_data(self):
        logger.info("Testing test_cmf_user_login: get_cmf_user_login_data")
        from mfcommon import get_cmf_user_login_data
        login_data, username, using_secret = get_cmf_user_login_data(
            self.mf_config)
        print(
            f"login_data: {login_data}, user name: {username}, using_secret: {using_secret}")
        expected_response = {
            'username': 'test@example.com', 'password': 'P2$Sword'}
        self.assertEqual(login_data, expected_response)

    @mock.patch("builtins.input", lambda *args: "mfa_test_code")
    @mock.patch("mfcommon.factory_login_with_cognito_user_pool",
                new=mock_successful_factory_login_with_cognito_user_pool)
    def test_successful_factory_login_with_mfa(self):
        logger.info("Testing test_cmf_user_login: "
                    "test_successful_factory_login_with_mfa")
        from mfcommon import factory_login_with_mfa
        username = "test@example.com"
        r_content = {
            "ChallengeName": "SMS_MFA",
            "username": {username},
            "password": "drowS$2P",
            "mfacode": "mfa_test_code",
            "Session": "test_session"
        }
        response = factory_login_with_mfa(username, r_content, self.mf_config)
        print(f"response: {response}")
        expected_response = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImR1bW15I"
        self.assertEqual(response, expected_response)

    @mock.patch("builtins.input", lambda *args: "mfa_test_code")
    @mock.patch("mfcommon.factory_login_with_cognito_user_pool",
                new=mock_failed_factory_login_with_cognito_user_pool)
    def test_failed_factory_login_with_mfa(self):
        logger.info("Testing test_cmf_user_login: "
                    "test_failed_factory_login_with_mfa")
        from mfcommon import factory_login_with_mfa
        username = "test@example.com"
        r_content = {
            "ChallengeName": "SMS_MFA",
            "username": {username},
            "password": "drowS$2P",
            "mfacode": "mfa_test_code",
            "Session": "test_session"
        }
        with self.assertRaises(SystemExit) as e:
            factory_login_with_mfa(username, r_content, self.mf_config)
        self.assertEqual(e.exception.code, 1)

    @mock.patch("mfcommon.factory_login_with_cognito_user_pool",
                new=mock_failed_factory_login_with_cognito_user_pool)
    def test_validate_cmf_user_login_with_error_status_code(self):
        logger.info("Testing test_cmf_user_login: "
                    "test_validate_cmf_user_login_with_error_status_code")
        from mfcommon import validate_cmf_user_login
        username = "test@example.com"
        auth_data = {'username': 'test_user', 'password': 'drowS$2P'}
        using_secret = True
        with self.assertRaises(SystemExit) as e:
            validate_cmf_user_login(self.mf_config, auth_data, username, using_secret)
        self.assertEqual(e.exception.code, 1)

    @mock.patch("mfcommon.factory_login_with_cognito_user_pool",
                new=mock_failed_factory_login_with_cognito_user_pool_with_other_status_code)
    def test_validate_cmf_user_login_with_other_status_code(self):
        logger.info("Testing test_cmf_user_login: "
                    "test_validate_cmf_user_login_with_other_status_code")
        from mfcommon import validate_cmf_user_login
        username = "test@example.com"
        auth_data = {'username': 'test_user', 'password': 'drowS$2P'}
        using_secret = True
        with self.assertRaises(SystemExit) as e:
            validate_cmf_user_login(self.mf_config, auth_data, username, using_secret)
        self.assertEqual(e.exception.code, None)

    @mock.patch("mfcommon.get_login_response",
                new=mock_get_login_response)
    def test_factory_login_with_cognito_user_pool_with_challengename(self):
        logger.info("Testing test_cmf_user_login: "
                    "test_factory_login_with_cognito_user_pool_with_challengename")
        from mfcommon import factory_login_with_cognito_user_pool
        auth_data = {'username': 'test@example.com', 'password': 'drowS$2P'}
        response = factory_login_with_cognito_user_pool(auth_data, self.mf_config)
        print(f"response: {response}")
        expected_response = {
            'statusCode': 200, 
            'body': '{"ChallengeName": "NEW_PASSWORD_REQUIRED"}'
        }
        self.assertEqual(response, expected_response)

    def test_factory_login_with_cognito_user_pool_with_missing_cognito_config(self):
        logger.info("Testing test_cmf_user_login: "
                    "test_factory_login_with_cognito_user_pool_with_missing_cognito_config")
        from mfcommon import factory_login_with_cognito_user_pool
        updated_mf_config = self.mf_config
        del(updated_mf_config["Region"])
        auth_data = {'username': 'test@example.com', 'password': 'drowS$2P'}
        response = factory_login_with_cognito_user_pool(auth_data, updated_mf_config)
        print(f"response: {response}")
        expected_response = {
            'statusCode': 200, 
             'body': 'Missing Cognito configuration in factory.json.'
        }
        self.assertEqual(response, expected_response)
