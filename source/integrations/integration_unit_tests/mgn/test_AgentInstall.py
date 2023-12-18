#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import io
from unittest import TestCase, mock
import importlib
from moto import mock_sts, mock_secretsmanager
import boto3

from mgn.test_mgn_common import mock_file_open
from mgn.test_mgn_common import default_mock_os_environ
from cmf_logger import logger

agent_install_main = importlib.import_module('1-AgentInstall')

CMF_LINUX_SERVER = {
    "server_id": "1",
    "server_name": "server1",
    "app_id": "1",
    "r_type": "Rehost",
    "server_os_family": "linux",
    "server_fqdn": "server1.onpremsim.env"
}

CMF_WINDOWS_SERVER = {
    "server_id": "2",
    "server_name": "server2",
    "app_id": "2",
    "r_type": "Rehost",
    "server_os_family": "windows",
    "server_fqdn": "server2.onpremsim.env"
}

DEFAULT_ARGS = [
    "--Waveid=1",
    "--NoPrompts=True",
    "--UseSSL=True",
    "--Concurrency=1"
]

DEFAULT_OUTPUT = 'data\ndata\n'

DEFAULT_RETURN_MESSAGE = "message 1"


def mock_return_valid_factory_login():
    return "1234567890abcdefgh"


def mock_return_valid_empty_factory_servers(waveid, token, os_split=True, rtype=None):
    return [], True, True


def mock_return_valid_populated_factory_servers(waveid, token, os_split=True, rtype=None):
    valid_factory_servers = [
        {
            "aws_accountid": "111111111111",
            "aws_region": "us-east-1",
            "servers_windows": [],
            "servers_linux": [
                CMF_LINUX_SERVER
            ]
        },
        {
            "aws_accountid": "222222222222",
            "aws_region": "us-east-1",
            "servers_windows": [
                CMF_WINDOWS_SERVER
            ],
            "servers_linux": []
        }
    ]
    return valid_factory_servers, True, True


def mock_return_valid_mgn_source_servers(_):
    return [{"isArchived": False,
             "sourceProperties": {
                 "identificationHints": {"hostname": "server1", "fqdn": CMF_LINUX_SERVER["server_fqdn"]}}},
            {"isArchived": False,
             "sourceProperties": {
                 "identificationHints": {"hostname": "server2", "fqdn": CMF_LINUX_SERVER["server_fqdn"]}}}]


def mock_return_invalid_mgn_source_servers(_):
    return []


def mock_install_task(parameters):
    final_output = {'messages': [], 'pid': 1001, 'host': parameters["server"]['server_fqdn']}
    final_output['messages'].append("Installing MGN Agent on :  " + parameters["server"]['server_fqdn'])
    final_output['return_code'] = 0

    return final_output


def mock_execute_cmd_via_ssh(host, username, key, cmd, using_key):
    output = ""
    error = ""
    return output, error


def set_up_secret_manager():
    secretsmanager_client = boto3.client(
        'secretsmanager', 'us-east-1')
    response = secretsmanager_client.create_secret(
        Name='MGNAgentInstallUser',
        Description="MGNInstallerUser",
        SecretString="{\"AccessKeyId\": \"123456789\", \"SecretAccessKey\": \"123456789\"}"
    )
    print(response)


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_secretsmanager
@mock_sts
@mock.patch('builtins.open', new=mock_file_open)
class AgentInstall(TestCase):

    @mock.patch('builtins.open', new=mock_file_open)
    def test_parse_boolean(self):
        logger.info("Testing parse_boolean: "
                    "function used to parse strings to bool")
        agent_install = importlib.import_module('1-AgentInstall')

        response = agent_install.parse_boolean('YES')

        self.assertEqual(response, True)

        response = agent_install.parse_boolean('NO')

        self.assertEqual(response, False)

    @mock.patch("mfcommon.factory_login",
                new=mock_return_valid_factory_login)
    @mock.patch("mfcommon.get_factory_servers",
                new=mock_return_valid_empty_factory_servers)
    @mock.patch.dict('os.environ', default_mock_os_environ)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_empty_server_list(self):
        logger.info("Testing Agent Install main: "
                    "Empty server list provided")

        agent_install = importlib.import_module('1-AgentInstall')

        response = agent_install.main(DEFAULT_ARGS)

        self.assertEqual(response, 0)

    @mock.patch("mfcommon.factory_login",
                new=mock_return_valid_factory_login)
    @mock.patch("mfcommon.get_factory_servers",
                new=mock_return_valid_populated_factory_servers)
    @mock_sts
    @mock.patch.object(agent_install_main, "get_unfiltered_mgn_source_servers",
                       new=mock_return_valid_mgn_source_servers)
    @mock.patch("subprocess.Popen")
    @mock.patch("subprocess.run")
    @mock.patch.object(agent_install_main, "run_task_windows",
                       new=mock_install_task)
    @mock.patch.object(agent_install_main, "run_task_linux",
                       new=mock_install_task)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_with_server_list(self, mock_popen, mock_run):
        logger.info("Testing Agent Install main: "
                    "With server list provided, no windows processing")

        agent_install = importlib.import_module('1-AgentInstall')

        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(DEFAULT_OUTPUT)
        mocked_popen.stderr = io.StringIO('')
        mocked_popen.wait.return_value = 0

        response = agent_install.main(DEFAULT_ARGS)

        self.assertEqual(response, 0)

    @mock.patch("mfcommon.factory_login",
                new=mock_return_valid_factory_login)
    @mock.patch("mfcommon.get_factory_servers",
                new=mock_return_valid_populated_factory_servers)
    @mock_sts
    @mock.patch.object(agent_install_main, "get_unfiltered_mgn_source_servers",
                       new=mock_return_invalid_mgn_source_servers)
    @mock.patch("subprocess.Popen")
    @mock.patch("subprocess.run")
    @mock.patch.object(agent_install_main, "run_task_windows",
                       new=mock_install_task)
    @mock.patch.object(agent_install_main, "run_task_linux",
                       new=mock_install_task)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_with_server_list_mgn_notfound(self, mock_popen, mock_run):
        logger.info("Testing Agent Install main: "
                    "Agent install successful but not found in MGN console")

        agent_install = importlib.import_module('1-AgentInstall')

        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(DEFAULT_OUTPUT)
        mocked_popen.stderr = io.StringIO('')
        mocked_popen.wait.return_value = 0

        response = agent_install.main(DEFAULT_ARGS)

        self.assertEqual(response, 1)

    @mock.patch("mfcommon.factory_login",
                new=mock_return_valid_factory_login)
    @mock.patch("mfcommon.get_factory_servers",
                new=mock_return_valid_populated_factory_servers)
    @mock_sts
    @mock.patch.object(agent_install_main, "get_unfiltered_mgn_source_servers",
                       new=mock_return_valid_mgn_source_servers)
    @mock.patch("subprocess.Popen")
    @mock.patch("subprocess.run")
    @mock.patch.object(agent_install_main, "run_task_windows",
                       new=mock_install_task)
    @mock.patch.object(agent_install_main, "run_task_linux",
                       new=mock_install_task)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_with_server_list_endpoints(self, mock_popen, mock_run):
        logger.info("Testing Agent Install main: "
                    "With server list provided and endpoints arguments, no windows processing")

        agent_install = importlib.import_module('1-AgentInstall')

        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(DEFAULT_OUTPUT)
        mocked_popen.stderr = io.StringIO('')
        mocked_popen.wait.return_value = 0

        response = agent_install.main(DEFAULT_ARGS + [
            "--S3Endpoint=S3endpoint",
            "--MGNEndpoint=MGNendpoint"
        ])

        self.assertEqual(response, 0)

    @mock.patch("mfcommon.execute_cmd_via_ssh",
                new=mock_execute_cmd_via_ssh)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_liunx(self):
        logger.info("Testing Agent Install Linux: "
                    "Server provided")

        agent_install = importlib.import_module('1-AgentInstall')

        server_parameters = {
            "windows_user_name": '',
            "windows_password": '',
            "windows_secret_name": None,
            "linux_user_name": "test",
            "linux_pass_key": "test",
            "linux_key_exist": False,
            "linux_secret_name": None,
            "no_user_prompts": True,
            "reinstall": False,
            "s3_endpoint": None,
            "mgn_endpoint": None,
            "windows_use_ssl": False,
            "server": CMF_LINUX_SERVER,
            "agent_linux_download_url": "test",
            "server_fqdn": CMF_LINUX_SERVER['server_fqdn'],
            "region": 'us-east-1',
            "agent_install_secrets": {
                "AccessKeyId": "12345",
                "SecretAccessKey": "123456",
                "SessionToken": "123456"
            }
        }

        response = agent_install.run_task_linux(server_parameters)

        self.assertEqual(response['return_code'], 0)

    @mock.patch("mfcommon.execute_cmd_via_ssh",
                new=mock_execute_cmd_via_ssh)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_liunx_with_endpoints(self):
        logger.info("Testing Agent Install Linux: "
                    "Server provided and endpoints provided")

        agent_install = importlib.import_module('1-AgentInstall')

        server_parameters = {
            "windows_user_name": '',
            "windows_password": '',
            "windows_secret_name": None,
            "linux_user_name": "test",
            "linux_pass_key": "test",
            "linux_key_exist": False,
            "linux_secret_name": None,
            "no_user_prompts": True,
            "reinstall": False,
            "s3_endpoint": "S3Enpoint",
            "mgn_endpoint": "MGNEnpoint",
            "windows_use_ssl": False,
            "server": CMF_LINUX_SERVER,
            "agent_linux_download_url": "test",
            "server_fqdn": CMF_LINUX_SERVER['server_fqdn'],
            "region": 'us-east-1',
            "agent_install_secrets": {
                "AccessKeyId": "12345",
                "SecretAccessKey": "123456",
                "SessionToken": "123456"
            }
        }

        response = agent_install.run_task_linux(server_parameters)

        self.assertEqual(response['return_code'], 0)

    @mock.patch("subprocess.Popen")
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_windows_success(self, mock_popen):
        logger.info("Testing Agent Install Windows: "
                    "Server provided and success")

        agent_install = importlib.import_module('1-AgentInstall')

        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(DEFAULT_OUTPUT)
        mocked_popen.stderr = io.StringIO('notanerror')
        mocked_popen.wait.return_value = 0

        server_parameters = {
            "windows_user_name": '',
            "windows_password": '',
            "windows_secret_name": None,
            "linux_user_name": "test",
            "linux_pass_key": "test",
            "linux_key_exist": False,
            "linux_secret_name": None,
            "no_user_prompts": True,
            "reinstall": False,
            "s3_endpoint": None,
            "mgn_endpoint": None,
            "windows_use_ssl": False,
            "server": CMF_WINDOWS_SERVER,
            "agent_windows_download_url": "test",
            "server_fqdn": CMF_WINDOWS_SERVER['server_fqdn'],
            "region": 'us-east-1',
            "agent_install_secrets": {
                "AccessKeyId": "12345",
                "SecretAccessKey": "123456",
                "SessionToken": "123456"
            }
        }

        response = agent_install.run_task_windows(server_parameters)

        self.assertEqual(response['return_code'], 0)

    @mock.patch("subprocess.Popen")
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_windows_fail(self, mock_popen):
        logger.info("Testing Agent Install Windows: "
                    "Server provided and failure")

        agent_install = importlib.import_module('1-AgentInstall')

        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(DEFAULT_OUTPUT)
        mocked_popen.stderr = io.StringIO('Installation failed')
        mocked_popen.wait.return_value = 0

        server_parameters = {
            "windows_user_name": '',
            "windows_password": '',
            "windows_secret_name": None,
            "linux_user_name": "test",
            "linux_pass_key": "test",
            "linux_key_exist": False,
            "linux_secret_name": None,
            "no_user_prompts": True,
            "reinstall": False,
            "s3_endpoint": None,
            "mgn_endpoint": None,
            "windows_use_ssl": False,
            "server": CMF_WINDOWS_SERVER,
            "agent_windows_download_url": "test",
            "server_fqdn": CMF_WINDOWS_SERVER['server_fqdn'],
            "region": 'us-east-1',
            "agent_install_secrets": {
                "AccessKeyId": "12345",
                "SecretAccessKey": "123456",
                "SessionToken": "123456"
            }
        }

        response = agent_install.run_task_windows(server_parameters)

        self.assertEqual(response['return_code'], 1)

    @mock.patch("mfcommon.factory_login",
                new=mock_return_valid_factory_login)
    @mock.patch("mfcommon.get_factory_servers",
                new=mock_return_valid_populated_factory_servers)
    @mock_sts
    @mock.patch.object(agent_install_main, "get_unfiltered_mgn_source_servers",
                       new=mock_return_valid_mgn_source_servers)
    @mock.patch("subprocess.Popen")
    @mock.patch("subprocess.run")
    @mock.patch.object(agent_install_main, "run_task_windows",
                       new=mock_install_task)
    @mock.patch.object(agent_install_main, "run_task_linux",
                       new=mock_install_task)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_agent_install_with_server_list_iam_security(self, mock_popen, mock_run):
        logger.info("Testing Agent Install main: "
                    "With server list provided, no windows processing")

        agent_install = importlib.import_module('1-AgentInstall')

        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(DEFAULT_OUTPUT)
        mocked_popen.stderr = io.StringIO('')
        mocked_popen.wait.return_value = 0

        response = agent_install.main([
            "--Waveid=1",
            "--AWSUseIAMUserCredentials=True",
            "--NoPrompts=True",
            "--Concurrency=1"
        ])

        self.assertEqual(response, 0)

    @mock_sts
    @mock_secretsmanager
    @mock.patch('builtins.open', new=mock_file_open)
    def test_get_agent_install_secrets_iam_user(self):
        logger.info("Testing Agent Install get agent install secrets: "
                    "using IAM user to install")

        agent_install = importlib.import_module('1-AgentInstall')

        secretsmanager_client = boto3.client(
            'secretsmanager', 'us-east-1')

        secret = {'AccessKeyId': '123456789', 'SecretAccessKey': '123456789'}

        secretsmanager_client.create_secret(
            Name="MGNAgentInstallUser",
            Description="MGNInstallerUser",
            SecretString="{\"AccessKeyId\": \"123456789\", \"SecretAccessKey\": \"123456789\"}"
        )

        response = agent_install.get_agent_install_secrets(
            True,
            {
                "aws_accountid": "123456789012",
                "aws_region": "us-east-1"
            })

        self.assertEqual(response, secret)

    @mock.patch('builtins.open', new=mock_file_open)
    def test_add_vpc_endpoints_to_command(self):
        logger.info("Testing Agent Install functions: "
                    "append vpc endpoints to install command")

        agent_install = importlib.import_module('1-AgentInstall')

        parameters = {"s3_endpoint": "s3_endpoint", "mgn_endpoint": "mgn_endpoint"}

        command = []

        agent_install.add_vpc_endpoints_to_command(parameters, command)

        self.assertEqual(command, ['-s3endpoint', 's3_endpoint', '-mgnendpoint', 'mgn_endpoint'])

    @mock.patch('builtins.open', new=mock_file_open)
    def test_add_windows_credentials_to_command_domain_windows(self):
        logger.info("Testing Agent Install functions: "
                    "append domain windows credentials to install command")

        agent_install = importlib.import_module('1-AgentInstall')

        parameters = {"windows_user_name": "mydomain\\user1", "windows_password": "P2$Sword"}

        command = []

        final_output = {"messages": []}

        agent_install.add_windows_credentials_to_command(parameters, command, final_output)

        self.assertEqual(command, ['-windowsuser', "'mydomain\\user1'", '-windowspwd', "'P2$Sword'"])

    @mock.patch('builtins.open', new=mock_file_open)
    def test_add_windows_credentials_to_command_local_windows(self):
        logger.info("Testing Agent Install functions: "
                    "append local windows credentials to install command")

        agent_install = importlib.import_module('1-AgentInstall')

        parameters = {"server": {"server_fqdn": "server1.mydomain.local"}, "windows_user_name": "user1",
                      "windows_password": "P2$Sword"}

        command = []

        final_output = {"messages": []}

        agent_install.add_windows_credentials_to_command(parameters, command, final_output)

        self.assertEqual(command, ['-windowsuser', "'server1\\user1'", '-windowspwd', "'P2$Sword'"])

        self.assertEqual(final_output, {"messages": ["INFO: Using local account to connect: server1\\user1"]})

    @mock.patch('sys.stdout', new_callable=io.StringIO)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_print_result(self, mock_sysout):
        logger.info("Testing Agent Install functions: "
                    "print results")

        agent_install = importlib.import_module('1-AgentInstall')

        process = {"host": "server1", "messages": [DEFAULT_RETURN_MESSAGE]}

        agent_install.print_result(process)

        self.assertIn(DEFAULT_RETURN_MESSAGE, mock_sysout.getvalue())

    @mock.patch('builtins.open', new=mock_file_open)
    def test_is_successful_message_unsucessful(self):
        logger.info("Testing Agent Install functions: "
                    "is_successful_message return code 1 is unsuccessful")

        agent_install = importlib.import_module('1-AgentInstall')

        process = {"return_code": 1}

        response = agent_install.is_successful_message(process)

        self.assertEqual(response, False)

    @mock.patch('builtins.open', new=mock_file_open)
    def test_is_successful_message_successful(self):
        logger.info("Testing Agent Install functions: "
                    "is_successful_message return code 0 is successful")

        agent_install = importlib.import_module('1-AgentInstall')

        # verify that a return code of 0 returns
        process = {"return_code": 0}

        response = agent_install.is_successful_message(process)

        self.assertEqual(response, True)

    @mock.patch('builtins.open', new=mock_file_open)
    def test_is_successful_message_no_process(self):
        logger.info("Testing Agent Install functions: "
                    "is_successful_message no return given")

        agent_install = importlib.import_module('1-AgentInstall')

        # verify that a return code of 0 returns
        process = {}

        response = agent_install.is_successful_message(process)

        self.assertEqual(response, None)

    @mock.patch('sys.stdout', new_callable=io.StringIO)
    @mock.patch('builtins.open', new=mock_file_open)
    def test_process_message(self, mock_sysout):
        logger.info("Testing Agent Install functions: "
                    "is_successful_message no return given")

        agent_install = importlib.import_module('1-AgentInstall')

        # verify that a return code of 0 returns
        process = {"host": "server1", "messages": [DEFAULT_RETURN_MESSAGE], "printed": False, "return_code": 0}

        response = agent_install.process_message(process)

        self.assertEqual(response, True)

        self.assertIn(DEFAULT_RETURN_MESSAGE, mock_sysout.getvalue())
