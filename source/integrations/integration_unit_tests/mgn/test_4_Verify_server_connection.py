#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import importlib
import unittest
from unittest.mock import patch, ANY
from moto import mock_sts, mock_ec2
import subprocess

from mgn.test_mgn_common import mock_file_open, default_mock_os_environ, logger, servers_list, mock_boto_api_call,\
    mock_factory_login, mock_get_factory_servers, mock_get_server_credentials, servers_list_linux


@mock_ec2
@mock_sts
@patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
@patch('mfcommon.factory_login', new=mock_factory_login)
@patch('mfcommon.get_factory_servers', new=mock_get_factory_servers)
@patch('mfcommon.get_server_credentials', new=mock_get_server_credentials)
@patch.dict('os.environ', default_mock_os_environ)
class VerifyServerConnectionTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.popen_orig = subprocess.Popen

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_check_windows_pass(self, mock_popen):
        verify_server_conn = importlib.import_module('4-Verify-server-connection')
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            VerifyServerConnectionTestCase.popen_orig(['echo', 'working'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        failures = verify_server_conn.check_windows(copy.deepcopy(servers_list)[0]['servers'], '3389')
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_check_windows_fail(self, mock_popen):
        verify_server_conn = importlib.import_module('4-Verify-server-connection')
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            VerifyServerConnectionTestCase.popen_orig(['echo', 'supress output'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        failures = verify_server_conn.check_windows(copy.deepcopy(servers_list)[0]['servers'], '3389')
        self.assertEqual(1, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.open_ssh')
    def test_check_linux_pass(self, mock_mfcommon_open_ssh):
        verify_server_conn = importlib.import_module('4-Verify-server-connection')
        mock_mfcommon_open_ssh.return_value = 'ok', ''
        failures = verify_server_conn.check_linux(copy.deepcopy(servers_list_linux)[0]['servers'], 'secret', '22')
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.open_ssh')
    def test_check_linux_error(self, mock_mfcommon_open_ssh):
        verify_server_conn = importlib.import_module('4-Verify-server-connection')
        mock_mfcommon_open_ssh.return_value = 'ok', 'some error'
        failures = verify_server_conn.check_linux(copy.deepcopy(servers_list_linux)[0]['servers'], 'secret', '22')
        self.assertEqual(1, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('mfcommon.open_ssh')
    def test_check_linux_ssh_fail(self, mock_mfcommon_open_ssh):
        verify_server_conn = importlib.import_module('4-Verify-server-connection')
        mock_mfcommon_open_ssh.return_value = '', ''
        failures = verify_server_conn.check_linux(copy.deepcopy(servers_list_linux)[0]['servers'], 'secret', '22')
        self.assertEqual(0, failures)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    @patch('mfcommon.open_ssh')
    def test_main_pass(self, mock_mfcommon_open_ssh, mock_popen):
        verify_server_conn = importlib.import_module('4-Verify-server-connection')
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            VerifyServerConnectionTestCase.popen_orig(['echo', 'working'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        mock_mfcommon_open_ssh.return_value = 'ok', ''
        failures = verify_server_conn.main(["--Waveid", "1"])
        self.assertEqual(0, failures)
