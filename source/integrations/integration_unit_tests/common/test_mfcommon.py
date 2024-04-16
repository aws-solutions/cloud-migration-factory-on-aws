#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import os
import io
import contextlib
from moto import mock_aws
from unittest import TestCase, mock
from common.test_mfcommon_util import default_mock_os_environ, \
set_up_secret_manager, \
set_up_cognito_credential, \
mock_requests_get_empty_accounts, \
mock_requests_get_valid_accounts, \
mock_requests_get_invalid_accounts, \
mock_requests_get_valid_accounts_and_servers, \
mock_requests_get_missing_server_os, \
mock_requests_get_missing_server_fqdn, \
mock_requests_get_same_server_os, \
mock_requests_get_invalid_server_os, \
mock_requests_put, \
mock_requests_with_connection_error, \
mock_raise_paramiko_ssh_exception, \
mock_raise_io_exception, \
mock_raise_exception, \
mock_paramiko_get_private_key, \
mock_paramiko_set_missing_host_key_policy, \
mock_paramiko_ssh_connect, \
mock_paramiko_exec_command, \
mock_read_lines, \
mock_execute_cmd_via_ssh_with_ubuntu, \
mock_execute_cmd_via_ssh_with_fedora, \
mock_execute_cmd_via_ssh_with_suse, \
mock_subprocess_run, \
logger, \
mock_file_open
# from mfcommon import mf_config
# from mfcommon import factory_login, \
# mf_config, get_server_credentials, \
# get_credentials, \
# get_factory_servers, \
# get_mf_config_user_api_id, \
# get_api_endpoint_headers, \
# get_api_endpoint_url, \
# api_stage, \
# update_server_migration_status, \
# update_server_replication_status, \
# get_mgn_source_server, \
# execute_cmd, \
# execute_cmd_via_ssh, \
# create_csv_report, \
# find_distribution, \
# add_windows_servers_to_trusted_hosts, \
# logger

        
@mock.patch.dict('os.environ', default_mock_os_environ)
@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_aws
class CommonTestCase(TestCase):

    def setUp(self):
        # Initialize general configurations
        from mfcommon import mf_config, api_stage
        self.mf_config = mf_config
        self.api_stage = api_stage
        self.region = mf_config["Region"]
        self.service_account_email = "test@example.com"
        self.service_account_email_2 = "test2@example.com"
        self.service_account_email_3 = "test3@example.com"

        # Initialize cognito credentials
        self.ctb, self.token, self.session = set_up_cognito_credential()

        # Update general configurations
        self.mf_config['UserPoolId'] = self.ctb.user_pool_id
        self.mf_config['UserPoolClientId'] = os.environ['clientId']
        self.mf_config['session'] = self.session

        # Initialize configurations for credentials test
        self.local_username = ""
        self.local_password = ""
        self.server = {}
        self.secret_override = "test_secret"
        self.no_user_prompts = False

        # Initialize configurations for servers test
        self.wave_id = "1"
        self.token = "test_token"
        self.os_split = True
        self.r_type = "Rehost"
        self.server_id ="test_server_1"
        self.status ="test_status"
        self.cmf_server = {
            "server_name": "test_sever_1",
            "server_fqdn": "test_server_fqdn"

        }
        self.mgn_source_servers = [
            {
                "isArchived": False,
                "sourceProperties": {
                    "networkInterfaces": [
                        {
                            "isPrimary": True,
                            "ips": [
                                "test_sever_1",
                                "test_server_fqdn"
                            ]
                        }
                    ],
                    "identificationHints": {
                        "hostname": "test_host-1",
                        "fqdn": "test_fqdn"
                    }
                }
            }
        ]

        # Initialize configurations for executing command test
        self.user_name ="test_user"
        self.key = "test_key"
        self.using_key = True
        self.command = "test_command"
        self.multi_threaded = False

    def tearDown(self):
        pass

    def mock_get_cmf_user_login_data(self):
        login_data = {
            "username": "test3@example.com",
            "password": "test_password",
            "mfacode": "mfa_test_code",
            "session": str(self['session'])
        }
        username = "test3@example.com"
        using_secret = True
        return login_data, username, using_secret
    
    def mock_return_valid_cached_secret(self):
        return "test_secret"

    def mock_skip_cached_secret(self):
        pass

    def mock_get_secret_data_tmp_json_for_server_credential(self, *args):
        return {
            "USERNAME": "test@example.com",
            "PASSWORD": "test_password",
            "IS_SSH_KEY": "false",
            "SECRET_TYPE": "OS",
            "OS_TYPE": "Windows"
        }

    def mock_get_secret_data_tmp_json(self, *args):
        return {
            "USERNAME": "test@example.com",
            "PASSWORD": "test_password",
            "IS_SSH_KEY": "false",
            "SECRET_TYPE": "OS",
            "OS_TYPE": "Windows",
            "SECRET_TYPE": "OS",
            "SECRET_KEY": "test_secret_key",
            "SECRET_VALUE": "test_secret_value",
            "APIKEY": "test_api_key",
            "SECRET_STRING": "test_secret_string"
        }
    
    def mock_get_windows_password():
        return "test_password"

    def mock_get_linux_password():
        return "test@example.com", "test_pass_key", True
               
    def update_credentials_store(self, os_type):
        credentials_store = {
            os_type: "test_secret"
            }
        return credentials_store

    def update_credential_configurations(
            self, local_username="", local_password="",
            server={}, secret_override="test_secret",
            no_user_prompts=False):
        self.local_username = local_username
        self.local_password = local_password
        self.server = server
        self.secret_override = secret_override
        self.no_user_prompts = no_user_prompts
    
    def test_factory_login_with_invalid_account(self):
        logger.info("Testing test_mfcommon: "
                    "test_factory_login_with_invalid_account")
        from mfcommon import factory_login
        self.mf_config["Region"] = self.region
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, False, "test@example.com")
        self.assertRaises(Exception, factory_login)

    def test_factory_login_with_valid_account(self):
        logger.info("Testing test_mfcommon: "
                    "test_factory_login_with_valid_account")
        from mfcommon import factory_login
        self.mf_config["Region"] = self.region
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")
        response = factory_login()
        print("Response: ", response)
        self.assertIsNotNone(response)

    @mock.patch("builtins.input", lambda *args: "default_user")
    @mock.patch("getpass.getpass", "123456789")
    def test_factory_login_without_region (self):
        logger.info("Testing test_mfcommon: "
                    "test_factory_login_with_default_user")
        from mfcommon import factory_login
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")
        self.mf_config["DefaultUser"] = "default_user"
        del(self.mf_config["Region"])
        self.assertRaises(Exception, factory_login)
        self.mf_config["Region"] = self.region

    @mock.patch("mfcommon.get_cmf_user_login_data", 
                new=mock_get_cmf_user_login_data)
    def test_factory_login_with_mfa(self):
        logger.info("Testing test_mfcommon: "
                    "test_factory_login_with_mfa")
        from mfcommon import factory_login
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test3@example.com")
        with self.assertRaises(Exception) as e:
            factory_login()
        self.assertNotIn("NotAuthorizedException", str(e))

    def test_get_server_credentials_with_local_account(self):
        logger.info("Testing test_mfcommon: "
                    "test_factory_login_with_mfa")
        from mfcommon import get_server_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "local_test_user", "local_test_password")

        response = get_server_credentials(
            self.local_username, self.local_password, self.server)
        print("Response: ", response)
        expected_response = {
            'username': self.local_username,
            'password': self.local_password
            }
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    def test_get_server_credentials_without_cached_secret(self):
        logger.info("Testing test_mfcommon: "
                    "test_factory_login_with_mfa")
        from mfcommon import get_server_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"secret_name": self.secret_id}, 
            self.secret_id, True)
        
        response = get_server_credentials(
            self.local_username, self.local_password,
            self.server, self.secret_override,
            self.no_user_prompts)
        print("Response: ", response)
        expected_response = {
            'username': '', 'password': '',
            'secret_type': '', 'os_type': ''
            }
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    @mock.patch("mfcommon.get_secret_data_tmp_json",
                new=mock_get_secret_data_tmp_json_for_server_credential)
    def test_get_server_credentials_with_raw_secret_data(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_server_credentials_with_raw_secret_data")
        from mfcommon import get_server_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"secret_name": self.secret_id}, 
            self.secret_id, True)
        
        response = get_server_credentials(
            self.local_username, self.local_password,
            self.server, self.secret_override,
            self.no_user_prompts)
        print("Response: ", response)
        expected_response = {
            'username': 'test@example.com',
            'password': 'test_password',
            'private_key': False,
            'secret_type': 'OS',
            'os_type': 'Windows'
            }
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    @mock.patch("mfcommon.get_secret_data_tmp_json",
                new=mock_get_secret_data_tmp_json_for_server_credential)
    def test_get_server_credentials_without_user_prompts(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_server_credentials_for_windows")
        from mfcommon import get_server_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"server_os_family": "windows"}, 
            None, True)
        
        response = get_server_credentials(
            self.local_username, self.local_password,
            self.server, self.secret_override,
            self.no_user_prompts)
        print("Response: ", response)
        expected_response = {'password': '', 'private_key': False, 'username': ''}
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    @mock.patch("mfcommon.get_secret_data_tmp_json",
                new=mock_get_secret_data_tmp_json_for_server_credential)
    @mock.patch("mfcommon.get_windows_password",
                new=mock_get_windows_password)
    @mock.patch("builtins.input", lambda *args: "test@example.com")
    def test_get_windows_server_credentials_with_user_prompt(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_windows_server_credentials_with_user_prompt")
        from mfcommon import get_server_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"server_os_family": "windows"}, 
            None, False)

        response = get_server_credentials(
            self.local_username, self.local_password,
            self.server, self.secret_override,
            self.no_user_prompts)
        print("Response: ", response)
        expected_response = {'username': 'test@example.com', 'password': 'test_password'}
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    @mock.patch("mfcommon.get_secret_data_tmp_json",
                new=mock_get_secret_data_tmp_json_for_server_credential)
    @mock.patch("mfcommon.get_linux_password",
                new=mock_get_linux_password)
    @mock.patch("builtins.input", lambda *args: "test@example.com")
    def test_get_linux_server_credentials_with_user_prompt(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_linux_server_credentials_with_user_prompt")
        from mfcommon import get_server_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"server_os_family": "linux"}, 
            None, False)

        response = get_server_credentials(
            self.local_username, self.local_password,
            self.server, self.secret_override,
            self.no_user_prompts)
        print("Response: ", response)
        expected_response = {'username': 'test@example.com', 'password': 'test_pass_key', 'private_key': True}
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    @mock.patch("mfcommon.get_secret_data_tmp_json",
                new=mock_get_secret_data_tmp_json)
    def test_get_credentials_with_raw_secret_data(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_credentials_with_raw_secret_data")
        from mfcommon import get_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"secret_name": self.secret_id}, 
            self.secret_id, True)
        
        response = get_credentials(
            self.secret_override)
        print("Response: ", response)
        expected_response = {
            'username': 'test@example.com',
            'password': 'test_password', 
            'private_key': False, 
            'secret_type': 'OS', 
            'secret_key': 'test_secret_key', 
            'secret_value': 'test_secret_value', 
            'apikey': 'test_api_key', 
            'secret_string': 'test_secret_string', 
            'os_type': 'Windows'
        }
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.return_cached_secret", 
                new=mock_skip_cached_secret)
    @mock.patch("mfcommon.get_secret_data_tmp_json",
                new=mock_get_secret_data_tmp_json)
    def test_get_credentials_without_user_prompt(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_credentials_with_raw_secret_data")
        from mfcommon import get_credentials
        self.secretsmanager_client, \
        self.service_account_email, \
        self.secret_id, \
        self.secret_string = \
            set_up_secret_manager(
                self.mf_config, True, "test@example.com")

        self.update_credential_configurations(   
            "", "", 
            {"secret_name": ""}, 
            "", True)
        expected_response = {'username': '', 'password': ''}

        response = get_credentials(
            self.secret_override,
            self.no_user_prompts,
            expected_response
        )
        print("Response: ", response)
        self.assertEqual(response, expected_response)

    def test_get_factory_servers_with_bad_request(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_bad_request")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = ("ERROR: Bad response from API https://xxxxxx.exe.execute-api.us-east-1.amazonaws.com"
                             "/prod/user/server/user/server. The method is not implemented\n")
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_empty_accounts)
    def test_get_factory_servers_with_empty_accounts(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_empty_accounts")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = "ERROR: AWS Account list for wave 1 is empty....\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_valid_accounts)
    def test_get_factory_servers_with_valid_accounts(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_valid_accounts")
        from mfcommon import get_factory_servers
        response, _, _ = get_factory_servers(
            self.wave_id, self.token, self.os_split, self.r_type)
        print("Response: ", response)
        expected_response = [
            {'aws_accountid': '111111111111', 'aws_region': 'us-east-1', 'servers_windows': [], 'servers_linux': []}, 
            {'aws_accountid': '222222222222', 'aws_region': 'us-east-1', 'servers_windows': [], 'servers_linux': []}
        ]
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_invalid_accounts)
    def test_get_factory_servers_with_invalid_accounts(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_invalid_accounts")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = "ERROR: Incorrect AWS Account Id Length for app: app_name_1\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_missing_server_os)
    def test_get_factory_servers_with_missing_server_os(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_missing_server_os")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
        "### Servers in Target Account: 111111111111, region: us-east-1 ###\nERROR: server_os_family does not exist for: server1\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_missing_server_fqdn)
    def test_get_factory_servers_with_missing_server_fqdn(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_missing_server_fqdn")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
        "### Servers in Target Account: 111111111111, region: us-east-1 ###\nERROR: server_fqdn for server: server1 doesn't exist\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_valid_accounts_and_servers)
    def test_get_factory_servers_with_valid_accounts_and_servers(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_valid_accounts_and_servers")
        from mfcommon import get_factory_servers
        response, _, _ = get_factory_servers(
            self.wave_id, self.token, self.os_split, self.r_type)
        print("Response: ", response)
        expected_response = [
            {
                "aws_accountid": "111111111111",
                "aws_region": "us-east-1",
                "servers_windows": [],
                "servers_linux": [
                    {
                        "server_name": "server1",
                        "app_id": "app_id_1",
                        "r_type": "Rehost",
                        "server_os_family": "linux",
                        "server_fqdn": "wordpress-web.onpremsim.env"
                    }
                ]
            },
            {
                "aws_accountid": "222222222222",
                "aws_region": "us-east-1",
                "servers_windows": [
                    {
                        "server_name": "server2",
                        "app_id": "app_id_2",
                        "r_type": "Rehost",
                        "server_os_family": "windows",
                        "server_fqdn": "laptop-personal.workspace.net"
                    }
                ],
                "servers_linux": []
            }
        ]
        
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_get_same_server_os)
    def test_get_factory_servers_with_same_os(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_same_os")
        from mfcommon import get_factory_servers
        self.os_split = False
        response = get_factory_servers(
            self.wave_id, self.token, self.os_split, self.r_type)
        print("Response: ", response)
        expected_response = [
            {
                "aws_accountid": "111111111111",
                "aws_region": "us-east-1",
                "servers": [
                    {
                        "server_name": "server1",
                        "app_id": "app_id_1",
                        "r_type": "Rehost",
                        "server_os_family": "linux",
                        "server_fqdn": "wordpress-web.onpremsim.env"
                    }
                ]
            },
            {
                "aws_accountid": "222222222222",
                "aws_region": "us-east-1",
                "servers": [
                    {
                        "server_name": "server2",
                        "app_id": "app_id_2",
                        "r_type": "Rehost",
                        "server_os_family": "linux",
                        "server_fqdn": "wordpress-web.onpremsim.env"
                    }
                ]
            }
        ]
        self.assertEqual(response, expected_response)
        self.os_split = True    # Reset to default True

    @mock.patch("requests.get", new=mock_requests_get_invalid_server_os)
    def test_get_factory_servers_with_invalid_server_os(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_invalid_server_os")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
        "### Servers in Target Account: 111111111111, region: us-east-1 ###\nERROR: Invalid server_os_family for: server1, please select either Windows or Linux\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.get", new=mock_requests_with_connection_error)
    def test_get_factory_servers_with_connection_error(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_factory_servers_with_connection_error")
        from mfcommon import get_factory_servers
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
            response, _, _ = get_factory_servers(
                self.wave_id, self.token, self.os_split, self.r_type)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
        "ERROR: Could not connect to API endpoint https://xxxxxx.exe.execute-api.us-east-1.amazonaws.com/prod/user/server/user/server.\n"
        self.assertEqual(response, expected_response)

    def test_get_mf_config_user_api_id_with_user_api(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mf_config_user_api_id_with_user_api")
        from mfcommon import get_mf_config_user_api_id
        self.mf_config["UserApi"] = "test_user_api"
        response = get_mf_config_user_api_id()
        print("Response: ", response)
        expected_response = "test_user_api"
        self.assertEqual(response, expected_response)
        del(self.mf_config["UserApi"])  #Reset to default value

    def test_get_mf_config_user_api_id_without_user_api(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mf_config_user_api_id_without_user_api")
        from mfcommon import get_mf_config_user_api_id
        user_api_url = self.mf_config["UserApiUrl"]
        del(self.mf_config["UserApiUrl"])

        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
                get_mf_config_user_api_id()
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
        "ERROR: Invalid FactoryEndpoints.json file. UserApi or UserApiUrl not present.\n"
        self.assertEqual(response, expected_response)
        self.mf_config["UserApiUrl"] = user_api_url #Reset to default value

    def test_get_api_endpoint_headers_with_vpce_id(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_api_endpoint_headers_with_vpce_id")
        from mfcommon import get_api_endpoint_headers
        self.mf_config["VpceId"] = "test_vpce_id"
        # token = "test_token"
        api_id = "test_api_id"
        response = get_api_endpoint_headers(self.token)
        print("Response: ", response)
        expected_response = {
            "Authorization": self.token
        }
        self.assertEqual(response, expected_response)
        del(self.mf_config["VpceId"])  #Reset to default value

    def test_get_api_endpoint_url_with_vpce_id(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_api_endpoint_url_with_vpce_id")
        from mfcommon import get_api_endpoint_url
        self.mf_config["VpceId"] = "test_vpce_id"
        api_endpoint = "test_api_endpoint"
        api_id = "test_api_id"
        response = get_api_endpoint_url(api_id, api_endpoint)
        print("Response: ", response)
        expected_response = (f'https://{api_id}-{self.mf_config["VpceId"]}'
                             f'.execute-api.us-east-1.amazonaws.com/{self.api_stage}{api_endpoint}')
        self.assertEqual(response, expected_response)
        del(self.mf_config["VpceId"])  #Reset to default value

    @mock.patch("requests.put", new=mock_requests_put)
    def test_update_server_migration_status(self):
        logger.info("Testing test_mfcommon: "
                    "test_update_server_migration_status")
        from mfcommon import update_server_migration_status
        response = update_server_migration_status(self.token, self.server_id, self.status)
        print("Response: ", response)
        self.assertEqual(response.status_code, 200)

    def test_update_server_migration_status_with_failed_status_code(self):
        logger.info("Testing test_mfcommon: "
                    "test_update_server_migration_status_with_failed_status_code")
        from mfcommon import update_server_migration_status
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io) as print_str:
            update_server_migration_status(self.token, self.server_id, self.status)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
            "ERROR: Bad response from API https://xxxxxx.exe.execute-api.us-east-1.amazonaws.com/prod/user/server/test_server_1/user/server/test_server_1. The method is not implemented\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.put", new=mock_requests_with_connection_error)
    def test_update_server_migration_status_with_connection_error(self):
        logger.info("Testing test_mfcommon: "
                    "test_update_server_migration_status_with_connection_error")
        from mfcommon import update_server_migration_status
        str_io = io.StringIO()
        with self.assertRaises(SystemExit) as se, \
            contextlib.redirect_stdout(str_io) as print_str:
                update_server_migration_status(self.token, self.server_id, self.status)
        self.assertEqual(se.exception.code, None)
        response = print_str.getvalue()
        print("Response: ", response)
        expected_response = \
        "ERROR: Could not connect to API endpoint https://xxxxxx.exe.execute-api.us-east-1.amazonaws.com/prod/user/server/test_server_1/user/server/test_server_1.\n"
        self.assertEqual(response, expected_response)

    @mock.patch("requests.put", new=mock_requests_put)
    def test_update_server_replication_status(self):
        logger.info("Testing test_mfcommon: "
                    "test_update_server_replication_status")
        from mfcommon import update_server_replication_status
        response = update_server_replication_status(self.token, self.server_id, self.status)
        print("Response: ", response)
        self.assertEqual(response.status_code, 200)

    def test_get_mgn_source_server(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mgn_source_server")
        from mfcommon import get_mgn_source_server
        self.mgn_source_servers[0]["isArchived"] = True
        response = get_mgn_source_server(self.cmf_server, self.mgn_source_servers)
        print("Response: ", response)
        self.assertEqual(response, None)
        self.mgn_source_servers[0]["isArchived"] = False # Reset to default value

    def test_get_mgn_source_server_for_matching_ip(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mgn_source_server_for_matching_ip")
        from mfcommon import get_mgn_source_server
        response = get_mgn_source_server(self.cmf_server, self.mgn_source_servers)
        print("Response: ", response)
        expected_response = {
            'isArchived': False, 
            'sourceProperties': {
                'networkInterfaces': [
                    {
                        'isPrimary': True, 
                        'ips': ['test_sever_1', 'test_server_fqdn']
                     }
                ], 
                'identificationHints': {
                    'hostname': 'test_host-1', 
                    'fqdn': 'test_fqdn'
                }
            }
        }
        self.assertEqual(response, expected_response)

    def test_get_mgn_source_server_for_non_primary_ip(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mgn_source_server_for_non_primary_ip")
        from mfcommon import get_mgn_source_server
        self.mgn_source_servers[0]["sourceProperties"] \
           ["networkInterfaces"][0]["isPrimary"] = False
        response = get_mgn_source_server(
            self.cmf_server, self.mgn_source_servers)
        print("Response: ", response)
        self.assertEqual(response, None)

         # Reset to default value
        self.mgn_source_servers[0]["sourceProperties"] \
            ["networkInterfaces"][0]["isPrimary"] = True
        
    def test_get_mgn_source_server_for_mismatching_ip(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mgn_source_server_for_mismatching_ip")
        from mfcommon import get_mgn_source_server
        ips = self.mgn_source_servers[0]["sourceProperties"] \
            ["networkInterfaces"][0]["ips"]
        self.mgn_source_servers[0]["sourceProperties"] \
            ["networkInterfaces"][0]["ips"] = ["test_ip_1"]
        response = get_mgn_source_server(self.cmf_server, self.mgn_source_servers)
        print("Response: ", response)
        self.assertEqual(response, None)

        # Reset to default value
        self.mgn_source_servers[0]["sourceProperties"] \
            ["networkInterfaces"][0]["ips"] = ips

    def test_get_mgn_source_server_for_matching_host_name(self):
        logger.info("Testing test_mfcommon: "
                    "test_get_mgn_source_server_for_matching_host_name")
        from mfcommon import get_mgn_source_server
        network_interfaces = self.mgn_source_servers[0]["sourceProperties"] \
            ["networkInterfaces"]
        del(self.mgn_source_servers[0]["sourceProperties"]["networkInterfaces"])
        host_name = self.mgn_source_servers[0]["sourceProperties"] \
           ["identificationHints"]["hostname"]
        self.mgn_source_servers[0]["sourceProperties"] \
           ["identificationHints"]["hostname"] = self.cmf_server["server_name"]
        response = get_mgn_source_server(self.cmf_server, self.mgn_source_servers)
        print("Response: ", response)
        expected_response = {'isArchived': False, 'sourceProperties': {'identificationHints': {'hostname': 'test_sever_1', 'fqdn': 'test_fqdn'}}}
        self.assertEqual(response, expected_response)

        # Reset to default value
        self.mgn_source_servers[0]["sourceProperties"] \
            ["networkInterfaces"] = network_interfaces
        self.mgn_source_servers[0]["sourceProperties"] \
           ["identificationHints"]["hostname"] = host_name 

    @mock.patch("paramiko.RSAKey.from_private_key", 
                new=mock_raise_paramiko_ssh_exception)
    def test_execute_cmd_with_ssh_execption(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_with_ssh_execption")
        from mfcommon import execute_cmd
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io) as print_str:
            response, ssh_error = execute_cmd(
                self.server_id, self.user_name, self.key,
                self.command, self.using_key)
        message = print_str.getvalue()
        print("Message: ", message)
        expected_response = ""
        self.assertEqual(message, ssh_error+"\n")
        self.assertEqual(response, expected_response)

    @mock.patch("paramiko.RSAKey.from_private_key", 
                new=mock_raise_io_exception)
    def test_execute_cmd_with_io_exception(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_with_io_exception")
        from mfcommon import execute_cmd
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io) as print_str:
            response, io_error = execute_cmd(
                self.server_id, self.user_name, self.key,
                self.command, self.using_key)
        message = print_str.getvalue()
        print("Message: ", message)
        expected_response = ""
        self.assertEqual(message, io_error+"\n")
        self.assertEqual(response, expected_response)

    @mock.patch("paramiko.RSAKey.from_private_key", 
                new=mock_raise_exception)
    def test_execute_cmd_with_all_other_exception(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_with_all_other_exception")
        from mfcommon import execute_cmd
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io) as print_str:
            response, other_error = execute_cmd(
                self.server_id, self.user_name, self.key,
                self.command, self.using_key)
        message = print_str.getvalue()
        print("Message: ", message)
        expected_response = ""
        self.assertEqual(message, other_error+"\n")
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.open_ssh",
                new=mock_raise_paramiko_ssh_exception)
    def test_execute_cmd_via_ssh_with_ssh_execption(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_via_ssh_with_ssh_execption")
        from mfcommon import execute_cmd_via_ssh
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io) as print_str:
            response, ssh_error = execute_cmd_via_ssh(
                self.server_id, self.user_name, self.key,
                self.command, self.using_key)
        message = print_str.getvalue()
        print("Message: ", message)
        expected_response = ""
        self.assertEqual(message, ssh_error+"\n")
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.open_ssh",
                new=mock_raise_io_exception)
    def test_execute_cmd_via_ssh_with_io_exception(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_via_ssh_with_io_exception")
        from mfcommon import execute_cmd_via_ssh
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io) as print_str:
            response, ssh_error = execute_cmd_via_ssh(
                self.server_id, self.user_name, self.key,
                self.command, self.using_key)
        message = print_str.getvalue()
        print("Message: ", message)
        expected_response = ""
        self.assertEqual(message, ssh_error+"\n")
        self.assertEqual(response, expected_response)

    @mock.patch("paramiko.RSAKey.from_private_key",
                new=mock_paramiko_get_private_key)
    @mock.patch("paramiko.SSHClient.set_missing_host_key_policy",
            new=mock_paramiko_set_missing_host_key_policy)
    @mock.patch("paramiko.SSHClient.connect",
        new=mock_paramiko_ssh_connect)
    @mock.patch("paramiko.SSHClient.exec_command",
        new=mock_paramiko_exec_command)
    @mock.patch("sys.stdout.readlines",new=mock_read_lines)
    @mock.patch("sys.stderr.readlines",new=mock_read_lines)
    def test_execute_cmd_with_key(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_with_key")
        from mfcommon import execute_cmd
        response, _ = execute_cmd(
            self.server_id, self.user_name, self.key,
            self.command, self.using_key)
        print("Response: ", response)
        expected_response = "test_line"
        self.assertEqual(response, expected_response)

    @mock.patch("paramiko.SSHClient.set_missing_host_key_policy",
            new=mock_paramiko_set_missing_host_key_policy)
    @mock.patch("paramiko.SSHClient.connect",
        new=mock_paramiko_ssh_connect)
    @mock.patch("paramiko.SSHClient.exec_command",
        new=mock_paramiko_exec_command)
    @mock.patch("sys.stdout.readlines",new=mock_read_lines)
    @mock.patch("sys.stderr.readlines",new=mock_read_lines)
    def test_execute_cmd_without_key(self):
        logger.info("Testing test_mfcommon: "
                    "test_execute_cmd_without_key")
        from mfcommon import execute_cmd
        self.using_key = False
        response, _ = execute_cmd(
            self.server_id, self.user_name, self.key,
            self.command, self.using_key)
        print("Response: ", response)
        expected_response = "test_line"
        self.assertEqual(response, expected_response)
        self.using_key = True   # Reset to default value

    def test_create_csv_service_validation_report(self):
        logger.info("Testing test_mfcommon: "
                    "test_create_csv_service_validation_report")
        from mfcommon import create_csv_report
        report_name = "serviceValdationReport"
        server_details = [{"test_key_1": "test_value_1", "test_key_2": "test_value_2"}]
        final_report_name = f"cmf-{report_name}-report_Wave_{self.wave_id}.csv"
        response = create_csv_report(
            report_name, server_details, self.wave_id)
        print("Response: ", response)
        expected_response = final_report_name
        self.assertEqual(response, expected_response)
        if os.path.exists(final_report_name):
            os.remove(final_report_name)

    def test_create_csv_report(self):
        logger.info("Testing test_mfcommon: test_create_csv_report")
        from mfcommon import create_csv_report
        report_name = "otherReport"
        server_details = [{"test_key_1": "test_value_1", "test_key_2": "test_value_2"}]
        final_report_name = f"cmf-{report_name}-report_Wave_{self.wave_id}.csv"
        response = create_csv_report(
            report_name, server_details, self.wave_id)
        print("Response: ", response)
        expected_response = final_report_name
        self.assertEqual(response, expected_response)
        if os.path.exists(final_report_name):
            os.remove(final_report_name)

    @mock.patch("mfcommon.execute_cmd_via_ssh",
            new=mock_execute_cmd_via_ssh_with_ubuntu)
    def test_find_distribution_ubuntu(self):
        logger.info("Testing test_mfcommon: test_find_distribution_ubuntu")
        from mfcommon import find_distribution
        response = find_distribution(
            self.server_id, self.user_name, self.key, self.using_key)
        print("Response: ", response)
        expected_response = "ubuntu"
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.execute_cmd_via_ssh",
            new=mock_execute_cmd_via_ssh_with_fedora)
    def test_find_distribution_fedora(self):
        logger.info("Testing test_mfcommon: test_find_distribution_fedora")
        from mfcommon import find_distribution
        response = find_distribution(
            self.server_id, self.user_name, self.key, self.using_key)
        print("Response: ", response)
        expected_response = "fedora"
        self.assertEqual(response, expected_response)

    @mock.patch("mfcommon.execute_cmd_via_ssh",
            new=mock_execute_cmd_via_ssh_with_suse)
    def test_find_distribution_suse(self):
        logger.info("Testing test_mfcommon: test_find_distribution_suse")
        from mfcommon import find_distribution
        response = find_distribution(
            self.server_id, self.user_name, self.key, self.using_key)
        print("Response: ", response)
        expected_response = "suse"
        self.assertEqual(response, expected_response)

    def test_find_distribution_other(self):
        logger.info("Testing test_mfcommon: test_find_distribution_other")
        from mfcommon import find_distribution
        response = find_distribution(
            self.server_id, self.user_name, self.key, self.using_key)
        print("Response: ", response)
        expected_response = "linux"
        self.assertEqual(response, expected_response)

    @mock.patch("subprocess.run", new=mock_subprocess_run)
    def test_add_windows_servers_to_trusted_hosts(self):
        logger.info("Testing test_mfcommon: "
                    "test_add_windows_servers_to_trusted_hosts")
        from mfcommon import add_windows_servers_to_trusted_hosts
        response = add_windows_servers_to_trusted_hosts(
            [self.cmf_server])
        print("Response: ", response)
        expected_response = None
        self.assertEqual(response, expected_response)
