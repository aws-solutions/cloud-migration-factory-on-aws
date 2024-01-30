#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import io
import sys
from argparse import Namespace
from unittest import TestCase, mock
import importlib
from pathlib import Path
from operator import itemgetter
from common.test_mfcommon_util import mock_raise_paramiko_ssh_exception

def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[2]

    sys.path.append(str(package_root_directory))
    sys.path.append(str(package_root_directory) + "/common/")
    sys.path.append(str(package_root_directory) + "/mgn/MGN-automation-scripts/2-RemoveUser")

init()
removeuser = importlib.import_module('2-RemoveUser')

class RemoveUserTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.mock_user = {"username": "test-user", "password": "test-pw", "private_key": "test-key"}
        self.mock_user_to_delete = {"username": "delete-user", "password": "delete-pw"}
        self.accounts = [
            {'aws_accountid': '111111111111',
             'aws_region': 'us-east-1', 
             'servers_windows': [{"server_fqdn": "winserv1"}, {"server_fqdn": "winserv2"}], 
             'servers_linux': [{"server_fqdn": "aml1"}, {"server_fqdn": "aml2"}]
            },
            {'aws_accountid': '222222222222', 
             'aws_region': 'us-east-2', 
             'servers_windows': [{"server_fqdn": "winserv3"}, {"server_fqdn": "winserv4"}], 
             'servers_linux': [{"server_fqdn": "aml3"}, {"server_fqdn": "aml4"}]
            },
        ]
        self.delete_linux_cmd = lambda user: 'sudo userdel -r ' + user

    def tearDown(self):
        super().tearDown()

    def mock_io_error(self): 
        raise IOError()
    
    def mock_windows_command(self, server, cred, user_to_delete):
        creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + cred[
                'username'] + "', (ConvertTo-SecureString '" + cred['password'] + "' -AsPlainText -Force)))"
        command = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {net user '" + \
                       user_to_delete['username'] + "' /delete}" + creds
        
        return command

    @mock.patch("paramiko.SSHClient")
    def test_find_distribution_passes_ubuntu(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        input, output, error = "input".encode(), "ubuntu".encode(), "error".encode()
        mocked_ssh.exec_command.return_value =io.BytesIO(input), io.BytesIO(output), io.BytesIO(error)

        result = removeuser.find_distribution(mocked_ssh)

        self.assertEqual("ubuntu", result)

    @mock.patch("paramiko.SSHClient")
    def test_find_distribution_passes_fedora(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        input, output, error = "input".encode(), "fedora".encode(), "error".encode()
        mocked_ssh.exec_command.return_value =io.BytesIO(input), io.BytesIO(output), io.BytesIO(error)

        result = removeuser.find_distribution(mocked_ssh)

        self.assertEqual("fedora", result)

    @mock.patch("paramiko.SSHClient")
    def test_find_distribution_passes_suse(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        input, output, error = "input".encode(), "suse".encode(), "error".encode()
        mocked_ssh.exec_command.return_value =io.BytesIO(input), io.BytesIO(output), io.BytesIO(error)

        result = removeuser.find_distribution(mocked_ssh)

        self.assertEqual("suse", result)

    @mock.patch("paramiko.SSHClient")
    def test_find_distribution_return_linux_unknown_output(self, mock_ssh_client):
        input, output, error = "input".encode(), "output".encode(), "error".encode()
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value =io.BytesIO(input), io.BytesIO(output), io.BytesIO(error)

        result = removeuser.find_distribution(mocked_ssh)

        self.assertEqual("linux", result)

    @mock.patch("io.BytesIO")
    @mock.patch("paramiko.SSHClient")
    def test_find_distribution_return_linux_with_io_error(self, mock_ssh_client, mock_io):
        input, output, error = "input".encode(), "output".encode(), "error".encode()
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value =io.BytesIO(input), io.BytesIO(output), io.BytesIO(error)
        mocked_string_io = mock_io.return_value
        mocked_string_io.read = self.mock_io_error

        result = removeuser.find_distribution(mocked_ssh)

        self.assertEqual("linux", result)

    @mock.patch("paramiko.SSHClient")
    def test_find_distribution_return_linux_with_paramiko_error(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = mock_raise_paramiko_ssh_exception
        
        result = removeuser.find_distribution(mocked_ssh)

        self.assertEqual("linux", result)

    @mock.patch.object(removeuser, "find_distribution", new=lambda _: "ubuntu")
    def test_get_add_user_cmd_ubuntu(self):
        user, pw = itemgetter("username", "password")(self.mock_user_to_delete)
        expected_cmd = 'sudo useradd -m ' + user + ' -p ' + pw + ' -G sudo'

        result = removeuser.get_add_user_cmd("ssh", user, pw)

        self.assertEqual(expected_cmd, result)

    @mock.patch.object(removeuser, "find_distribution", new=lambda _: "suse")
    def test_get_add_user_cmd_other_dist(self):
        user, pw = itemgetter("username", "password")(self.mock_user_to_delete)
        expected_cmd = 'sudo adduser -m ' + user + ' -p ' + pw + ' -g wheel'

        result = removeuser.get_add_user_cmd("ssh", user, pw)

        self.assertEqual(expected_cmd, result)

    @mock.patch.object(removeuser, "find_distribution", new=mock_raise_paramiko_ssh_exception)
    def test_get_add_user_cmd_returns_none_on_error(self):
        user, pw = itemgetter("username", "password")(self.mock_user_to_delete)

        result = removeuser.get_add_user_cmd("ssh", user, pw)

        self.assertEqual(None, result)

    @mock.patch("paramiko.SSHClient")
    @mock.patch("mfcommon.open_ssh")
    def test_delete_linux_user_passes(self, mock_open_ssh, mock_ssh_client):
        user, pw, key = itemgetter("username", "password", "private_key")(self.mock_user)
        delete_user = self.mock_user_to_delete["username"]
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = "input", io.BytesIO("user1\nuser2".encode()), ""
        mock_open_ssh.return_value = mocked_ssh, "error"

        result = removeuser.delete_linux_user(
            self.accounts[0]["servers_linux"][0]["server_fqdn"], 
            user, pw, key, delete_user
        )

        self.assertIn(mock.call(self.delete_linux_cmd(delete_user)),mocked_ssh.exec_command.call_args_list)
        self.assertEqual(True, result)

    @mock.patch("paramiko.SSHClient")
    @mock.patch("mfcommon.open_ssh")
    def test_delete_linux_user_fails_user_in_list(self, mock_open_ssh, mock_ssh_client):
        user, pw, key = itemgetter("username", "password", "private_key")(self.mock_user)
        delete_user = self.mock_user_to_delete["username"]
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = "input", io.BytesIO("user1\ndelete-user".encode()), ""
        mock_open_ssh.return_value = mocked_ssh, "error"

        result = removeuser.delete_linux_user(
            self.accounts[0]["servers_linux"][0]["server_fqdn"], 
            user, pw, key, delete_user
        )

        self.assertIn(mock.call(self.delete_linux_cmd(delete_user)),mocked_ssh.exec_command.call_args_list)
        self.assertEqual(False, result)

    @mock.patch("mfcommon.open_ssh")
    def test_delete_linux_user_fails_no_user(self, mock_ssh_client):
        user, pw, key = itemgetter("username", "password", "private_key")(self.mock_user)
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = "input", io.BytesIO("user1\nuser1".encode()), ""

        result = removeuser.delete_linux_user(self.accounts[0]["servers_linux"][0], user, pw, key, "")

        self.assertEqual(None, result)

    @mock.patch("paramiko.SSHClient")
    @mock.patch("mfcommon.open_ssh")
    def test_delete_linux_user_fails_no_ssh(self, mock_open_ssh, mock_ssh_client):
        user, pw, key = itemgetter("username", "password", "private_key")(self.mock_user)
        delete_user = self.mock_user_to_delete["username"]
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = "input", io.BytesIO("user1\nuser1\nnew-user".encode()), ""
        mock_open_ssh.return_value = None, "error"

        result = removeuser.delete_linux_user(
            self.accounts[0]["servers_linux"][0]["server_fqdn"], 
            user, pw, key, delete_user
        )

        self.assertEqual(False, result)

    @mock.patch("paramiko.SSHClient")
    @mock.patch("mfcommon.open_ssh")
    def test_delete_linux_user_fails_paramiko_exception(self, mock_open_ssh, mock_ssh_client):
        user, pw, key = itemgetter("username", "password", "private_key")(self.mock_user)
        delete_user = self.mock_user_to_delete["username"]
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = mock_raise_paramiko_ssh_exception
        mock_open_ssh.return_value = mocked_ssh, "error"

        result = removeuser.delete_linux_user(
            self.accounts[0]["servers_linux"][0]["server_fqdn"], 
            user, pw, key, delete_user
        )

        self.assertEqual(False, result)

    @mock.patch("paramiko.SSHClient")
    @mock.patch("mfcommon.open_ssh")
    def test_delete_linux_user_fails_other_exception(self, mock_open_ssh, mock_ssh_client):
        user, pw, key = itemgetter("username", "password", "private_key")(self.mock_user)
        delete_user = self.mock_user_to_delete["username"]
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = self.mock_io_error
        mock_open_ssh.return_value = mocked_ssh, "error"

        result = removeuser.delete_linux_user(
            self.accounts[0]["servers_linux"][0]["server_fqdn"], 
            user, pw, key, delete_user
        )

        self.assertEqual(False, result)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch.object(removeuser, "delete_linux_user")
    def test_process_user_remove_for_linux_servers_passes(self, mock_delete_linux_users, mock_get_server_creds):
        linux_server_list = self.accounts[0]["servers_linux"]
        mock_get_server_creds.side_effect = (self.mock_user, self.mock_user_to_delete, self.mock_user, self.mock_user_to_delete)
        mock_delete_linux_users.return_value = True

        result = removeuser.process_user_remove_for_linux_servers(linux_server_list, "", "")

        self.assertEqual(mock_delete_linux_users.call_count, len(linux_server_list))
        self.assertEqual(0, result)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch.object(removeuser, "delete_linux_user")
    def test_process_user_remove_for_linux_servers_fails_single_server(self, mock_delete_linux_users, mock_get_server_creds):
        linux_server_list = self.accounts[0]["servers_linux"]
        mock_get_server_creds.side_effect = (self.mock_user, self.mock_user_to_delete, self.mock_user, self.mock_user_to_delete)
        mock_delete_linux_users.side_effect = True, False

        result = removeuser.process_user_remove_for_linux_servers(linux_server_list, "", "")

        self.assertEqual(mock_delete_linux_users.call_count, len(linux_server_list))
        self.assertEqual(1, result)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch.object(removeuser, "delete_linux_user")
    def test_process_user_remove_for_linux_servers_fails_multiple_server(self, mock_delete_linux_users, mock_get_server_creds):
        linux_server_list = self.accounts[0]["servers_linux"]
        mock_get_server_creds.side_effect = (self.mock_user, self.mock_user_to_delete, self.mock_user, self.mock_user_to_delete)
        mock_delete_linux_users.side_effect = False, False

        result = removeuser.process_user_remove_for_linux_servers(linux_server_list, "", "")

        self.assertEqual(mock_delete_linux_users.call_count, len(linux_server_list))
        self.assertEqual(2, result)

    @mock.patch("mfcommon.add_windows_servers_to_trusted_hosts")
    @mock.patch("subprocess.Popen")
    @mock.patch("mfcommon.get_server_credentials")
    def test_process_user_remove_for_windows_servers_passes(self, mock_get_server_creds, mock_popen, mock_trusted):
        windows_server_list = self.accounts[0]["servers_windows"]
        mock_get_server_creds.side_effect = (self.mock_user, self.mock_user_to_delete, self.mock_user, self.mock_user_to_delete)
        mocked_popen = mock_popen.return_value
        mocked_popen.communicate.return_value = "", ""
        
        result = removeuser.process_user_remove_for_windows_servers(windows_server_list, "", "")

        for server in windows_server_list:
            cmd = self.mock_windows_command(server, self.mock_user, self.mock_user_to_delete)
            self.assertIn(mock.call(["powershell.exe", cmd], stdout=-1, stderr=-1), mock_popen.call_args_list)
        self.assertEqual(0, result)

    @mock.patch("mfcommon.add_windows_servers_to_trusted_hosts")
    @mock.patch("subprocess.Popen")
    @mock.patch("mfcommon.get_server_credentials")
    def test_process_user_remove_for_windows_servers_fails_stderr(self, mock_get_server_creds, mock_popen, mock_trusted):
        windows_server_list = self.accounts[0]["servers_windows"]
        mock_get_server_creds.side_effect = (self.mock_user, self.mock_user_to_delete, self.mock_user, self.mock_user_to_delete)
        mocked_popen = mock_popen.return_value
        mocked_popen.communicate.return_value = "", "test\nErrorId"
        
        result = removeuser.process_user_remove_for_windows_servers(windows_server_list, "", "")

        for server in windows_server_list:
            cmd = self.mock_windows_command(server, self.mock_user, self.mock_user_to_delete)
            self.assertIn(mock.call(["powershell.exe", cmd], stdout=-1, stderr=-1), mock_popen.call_args_list)
        self.assertEqual(2, result)

    @mock.patch("mfcommon.add_windows_servers_to_trusted_hosts")
    @mock.patch("subprocess.Popen")
    @mock.patch("mfcommon.get_server_credentials")
    def test_process_user_remove_for_windows_servers_fails_exception(self, mock_get_server_creds, mock_popen, mock_trusted):
        windows_server_list = self.accounts[0]["servers_windows"]
        mock_get_server_creds.side_effect = self.mock_io_error

        result = removeuser.process_user_remove_for_windows_servers(windows_server_list, "", "")

        self.assertEqual(0, mock_popen.call_count)
        self.assertEqual(2, result)

    @mock.patch.object(removeuser, "process_user_remove_for_linux_servers")
    @mock.patch.object(removeuser, "process_user_remove_for_windows_servers")
    def test_mock_process_user_remove_for_servers_passes(self, mock_windows_remove, mock_linux_remove):
        args = Namespace(
            SecretWindows="", RemoveSecretWindows="", NoPrompts=False,
            SecretLinux="", RemoveSecretLinux="",
        )
        mock_windows_remove.return_value = 0
        mock_linux_remove.return_value = 0

        result = removeuser.process_user_remove_for_servers(self.accounts, args)

        self.assertEqual(0, result)

    @mock.patch.object(removeuser, "process_user_remove_for_linux_servers")
    @mock.patch.object(removeuser, "process_user_remove_for_windows_servers")
    def test_mock_process_user_remove_for_servers_fails_all(self, mock_windows_remove, mock_linux_remove):
        args = Namespace(
            SecretWindows="", RemoveSecretWindows="", NoPrompts=False,
            SecretLinux="", RemoveSecretLinux="",
        )
        mock_windows_remove.return_value = 2
        mock_linux_remove.return_value = 2

        result = removeuser.process_user_remove_for_servers(self.accounts, args)

        self.assertEqual(8, result)

    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login")
    @mock.patch.object(removeuser, "process_user_remove_for_servers")
    def test_main_passes(self, mock_user_remove, mock_login, mock_get_servers):
        mock_args = ["--Waveid", "2"]
        mock_get_servers.return_value = self.accounts, "", ""
        mock_login.return_value = "test_key"
        mock_user_remove.return_value = 0

        result = removeuser.main(mock_args)

        self.assertEqual(0, result)

    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login")
    @mock.patch.object(removeuser, "process_user_remove_for_servers")
    def test_main_with_failure_count(self, mock_user_remove, mock_login, mock_get_servers):
        mock_args = ["--Waveid", "2"]
        mock_get_servers.return_value = self.accounts, "", ""
        mock_login.return_value = "test_key"
        mock_user_remove.return_value = 3

        result = removeuser.main(mock_args)

        self.assertEqual(1, result)