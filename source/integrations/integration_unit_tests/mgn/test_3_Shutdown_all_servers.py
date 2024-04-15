#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import importlib
import unittest
from unittest.mock import patch
from moto import mock_aws
import subprocess

from mgn.test_mgn_common import mock_file_open, default_mock_os_environ, logger, servers_list, mock_boto_api_call, \
    mock_factory_login, mock_get_factory_servers, mock_get_server_credentials, servers_list_linux, \
    mock_add_windows_servers_to_trusted_hosts


@mock_aws
@patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
@patch('mfcommon.factory_login', new=mock_factory_login)
@patch('mfcommon.get_factory_servers', new=mock_get_factory_servers)
@patch('mfcommon.get_server_credentials', new=mock_get_server_credentials)
@patch('mfcommon.add_windows_servers_to_trusted_hosts', new=mock_add_windows_servers_to_trusted_hosts)
@patch('builtins.open', new=mock_file_open)
@patch.dict('os.environ', default_mock_os_environ)
class ShutdownAllServersTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.popen_orig = subprocess.Popen

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_shutdown_for_windows_servers_success(self, mock_popen):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            ShutdownAllServersTestCase.popen_orig(['echo', 'working'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        failures = shut_down_all_servers.process_shutdown_for_windows_servers(
            copy.deepcopy(servers_with_os_split), 'test_secret')
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_shutdown_for_windows_servers_domain_user_success(self, mock_popen):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            ShutdownAllServersTestCase.popen_orig(['echo', 'working'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        shut_down_all_servers.mfcommon.get_server_credentials = \
            lambda local_username, local_password, server, secret_override=None, no_user_prompts=False: {
                'username': 'test_user@example.com',
                'password': 'test_password',
            }
        failures = shut_down_all_servers.process_shutdown_for_windows_servers(
            copy.deepcopy(servers_with_os_split), 'test_secret')
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_shutdown_for_windows_servers_no_secret(self, mock_popen):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        failures = shut_down_all_servers.process_shutdown_for_windows_servers(copy.deepcopy(servers_with_os_split), '')
        self.assertEqual(1, failures)
        self.assertEqual(0, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_shutdown_for_windows_servers_error(self, mock_popen):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            ShutdownAllServersTestCase.popen_orig(
                ['python', '-c', 'import sys; sys.stderr.write("ErrorId: ERR_11")'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        failures = shut_down_all_servers.process_shutdown_for_windows_servers(
            copy.deepcopy(servers_with_os_split), 'test_secret')
        self.assertEqual(1, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.execute_cmd_via_ssh')
    def test_shutdown_for_linux_servers_success(self, mock_execute_cmd_via_ssh):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        mock_execute_cmd_via_ssh.return_value = '', ''
        failures = shut_down_all_servers.process_shutdown_for_linux_servers(
            copy.deepcopy(servers_with_os_split), 'test_secret')
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.execute_cmd_via_ssh')
    def test_shutdown_for_linux_servers_no_secret(self, mock_execute_cmd_via_ssh):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        failures = shut_down_all_servers.process_shutdown_for_linux_servers(
            copy.deepcopy(servers_with_os_split), '')
        self.assertEqual(1, failures)
        self.assertEqual(0, mock_execute_cmd_via_ssh.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.execute_cmd_via_ssh')
    def test_shutdown_for_linux_servers_fail(self, mock_execute_cmd_via_ssh):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        servers_with_os_split = mock_get_factory_servers('1', 'test_token', os_split=True)[0]
        mock_execute_cmd_via_ssh.return_value = '', 'Error'
        failures = shut_down_all_servers.process_shutdown_for_linux_servers(
            copy.deepcopy(servers_with_os_split), 'test_secret')
        self.assertEqual(1, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.execute_cmd_via_ssh')
    @patch('subprocess.Popen')
    def test_main_no_secrets(self, mock_popen, mock_execute_cmd_via_ssh):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        mock_execute_cmd_via_ssh.return_value = '', ''
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            ShutdownAllServersTestCase.popen_orig(['echo', 'working'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        failures = shut_down_all_servers.main(['--Waveid', '1'])
        self.assertEqual(1, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.execute_cmd_via_ssh')
    @patch('subprocess.Popen')
    def test_main_success(self, mock_popen, mock_execute_cmd_via_ssh):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        mock_execute_cmd_via_ssh.return_value = '', ''
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            ShutdownAllServersTestCase.popen_orig(['echo', 'working'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        failures = shut_down_all_servers.main(
            ['--Waveid', '1', '--SecretWindows', 'test_secret', '--SecretLinux', 'test_secret'])
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    def test_main_no_servers(self):
        shut_down_all_servers = importlib.import_module('3-Shutdown-all-servers')
        with patch.object(shut_down_all_servers, 'mfcommon') as mock_mfcommon:
            mock_mfcommon.get_factory_servers.return_value = [], False, False
            failures = shut_down_all_servers.main(['--Waveid', '1'])
        self.assertEqual(0, failures)
