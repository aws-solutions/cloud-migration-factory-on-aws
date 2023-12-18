#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import io
import sys
from argparse import Namespace
from unittest import TestCase, mock
import importlib
from pathlib import Path
from common.test_mfcommon_util import mock_raise_paramiko_ssh_exception

def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[2]

    sys.path.append(str(package_root_directory))
    sys.path.append(str(package_root_directory) + "/common/")
    sys.path.append(str(package_root_directory) + "/mgn/MGN-automation-scripts/0-Prerequisites-checks")

init()
prereq_check = importlib.import_module('0-Prerequisites-checks')

class MockThread():
    def __init__(self, args, name, target):
        self.name = name
        self.target = target
        self.args = args

    def start(self):
        self.target(*self.args)

    def join(self):
        pass

class PreRequsitesCheckTestCase(TestCase):

    def setUp(self):
        self.s_result = {
            "server_id": "test_server_id",
            "server_name": "server.test", 
            "test_results": [], 
            "success": True
        }
        self.params = {
            "MGNEndpoint": "test_mgn_endpoint",
            "S3Endpoint": "test_s3_endpoint",
            "s": {
                "server_id": "test_server_id",
                "server_fqdn": "server.test",
            },
            "MGNServerIP": "0.0.0.0",
            "user_name": "test_user",
            "windows_password": "test_pw",
            "secret_name": "test_secret",
            "no_user_prompts": False,
            "winrm_use_ssl": True,
            "pass_key": "test-key"
        }

        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()
    
    def check_windows_command(self, host, port):
        return "sudo timeout 2 bash -c '</dev/tcp/" + \
            host + "/" + port + \
            " && echo port is open || echo port is closed' || echo connection timeout"
    
    def check_freespace_command(self, dir):
        return "df -h " + dir + " | tail -1 | tr -s ' ' | cut -d' ' -f4"
    
    def check_dhclient_command(self):
        return "sudo dhclient -v"

    def mock_is_winrm_accessible_setup(self, mock_popen, out, err, wait):
        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO(out)
        mocked_popen.stderr = io.StringIO(err)
        mocked_popen.wait.return_value = wait

    @mock.patch("subprocess.Popen")     
    def test_is_winrm_accessible_passes(self, mock_popen):
        self.mock_is_winrm_accessible_setup(mock_popen, 'data\ndata\n', '', 0)

        response = prereq_check.is_winrm_accessible(self.s_result)
        popen_args = mock_popen.call_args.args

        self.assertIn(["powershell.exe", "Test-WSMan -ComputerName " + self.s_result["server_name"]], popen_args)
        self.assertIn(
            {
                'test': "WinRM Accessible", 
                'result': "Pass"
            },
            self.s_result["test_results"], 
        )
        self.assertEqual(response, True)

    @mock.patch("subprocess.Popen")
    def test_is_winrm_accessible_passes_and_includes_ssl(self, mock_popen):
        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO('data\ndata\n')
        mocked_popen.stderr = io.StringIO('')
        mocked_popen.wait.return_value = 0

        response = prereq_check.is_winrm_accessible(self.s_result, winrm_use_ssl=True)
        popen_args = mock_popen.call_args.args

        self.assertIn(
            ["powershell.exe", 
             "Test-WSMan -ComputerName " + self.s_result["server_name"] + " -UseSSL"
            ], popen_args)
        self.assertIn(
            {
                'test': "WinRM Accessible", 
                'result': "Pass"
            },
            self.s_result["test_results"], 
        )
        self.assertEqual(response, True)

    @mock.patch("subprocess.Popen")
    def test_is_winrm_accessible_passes_with_cert_error(self, mock_popen):
        mocked_popen = mock_popen.return_value
        stdout_result_string = 'data\ndata\n'
        stderr_result_string = 'unknown certificate authority\nerror\n'
        mocked_popen.stdout = io.StringIO('data\ndata\n')
        mocked_popen.stderr = io.StringIO('unknown certificate authority\nerror\n')

        response = prereq_check.is_winrm_accessible(self.s_result)
        popen_args = mock_popen.call_args.args

        self.assertIn(["powershell.exe", "Test-WSMan -ComputerName " + self.s_result["server_name"]], popen_args)
        self.assertIn(
            {
                'test': "WinRM Accessible", 
                'result': "Pass"
            },
            self.s_result["test_results"], 
        )
        self.assertEqual(response, True)

    @mock.patch("subprocess.Popen")
    def test_is_winrm_accessible_fails_when_exit_code_not_zero(self, mock_popen):
        mocked_popen = mock_popen.return_value
        mocked_popen.stdout = io.StringIO('data\ndata\n')
        mocked_popen.stderr = io.StringIO('error\n')
        mocked_popen.wait.return_value = 1

        response = prereq_check.is_winrm_accessible(self.s_result)
        popen_args = mock_popen.call_args.args

        self.assertIn(["powershell.exe", "Test-WSMan -ComputerName " + self.s_result["server_name"]], popen_args)
        self.assertIn(
            {
                'test': "WinRM Accessible", 
                'result': "Fail",
                "error": ["data\n", "data\n", "error\n"]
            },
            self.s_result["test_results"], 
        )
        self.assertEqual(response, False)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("subprocess.Popen")
    def test_check_windows_passes_no_user(self, mock_popen, mock_get_server_credentials):
        self.mock_is_winrm_accessible_setup(mock_popen, '', '', 0)
        mock_get_server_credentials.return_value = {"username": "", "password": "pw"}
        mocked_popen = mock_popen.return_value
        output = "FreeSpace:Pass\nTCP443:Pass"
        error = ""
        mocked_popen.communicate.return_value = (output.encode(), error.encode())
        expected_command = "Invoke-Command -ComputerName " + self.params["s"]["server_fqdn"] + \
              " -FilePath 0-Prerequisites-Windows.ps1 -ArgumentList " + \
              self.params["MGNServerIP"] + "," + self.params["MGNEndpoint"] + "," + self.params["S3Endpoint"]
        
        result = prereq_check.check_windows(self.params)

        popen_args = mock_popen.call_args.args
        self.assertIn(
            ["powershell.exe", expected_command
            ], popen_args)
        self.assertEqual(result[1], False)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("subprocess.Popen")
    def test_check_windows_passes_with_user_and_no_backslash(self, mock_popen, mock_get_server_credentials):
        self.mock_is_winrm_accessible_setup(mock_popen, '', '', 0)
        mock_get_server_credentials.return_value = {"username": "user", "password": "pw"}
        mocked_popen = mock_popen.return_value
        output = "FreeSpace:Pass\nTCP443:Pass"
        error = ""
        mocked_popen.communicate.return_value = (output.encode(), error.encode())
        expected_command = "Invoke-Command -ComputerName " + \
            self.params["s"]["server_fqdn"] + \
            " -FilePath 0-Prerequisites-Windows.ps1 -ArgumentList " + \
            self.params["MGNServerIP"] + "," + \
            self.params["MGNEndpoint"] + "," + \
            self.params["S3Endpoint"]
        server_name = self.params["s"]["server_fqdn"].split(".")[0]
        additional_user_args = " -Credential (New-Object System.Management.Automation.PSCredential('" + \
            server_name + "\\" "user" + "', (ConvertTo-SecureString '" + \
                "pw" + "' -AsPlainText -Force)))"
        
        result = prereq_check.check_windows(self.params)

        popen_args = mock_popen.call_args.args
        self.assertIn(
            ["powershell.exe", expected_command + additional_user_args
            ], popen_args)
        self.assertEqual(result[1], False)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("subprocess.Popen")
    def test_check_windows_passes_with_user_and_backslash(self, mock_popen, mock_get_server_credentials):
        self.mock_is_winrm_accessible_setup(mock_popen, '', '', 0)
        mock_get_server_credentials.return_value = {"username": "test\\user", "password": "pw"}
        mocked_popen = mock_popen.return_value
        output = "FreeSpace:Pass\nTCP443:Pass"
        error = ""
        mocked_popen.communicate.return_value = (output.encode(), error.encode())
        expected_command = "Invoke-Command -ComputerName " + \
            self.params["s"]["server_fqdn"] + \
            " -FilePath 0-Prerequisites-Windows.ps1 -ArgumentList " + \
            self.params["MGNServerIP"] + "," + \
            self.params["MGNEndpoint"] + "," + \
            self.params["S3Endpoint"]
        additional_user_args = " -Credential (New-Object System.Management.Automation.PSCredential('" + \
            "test\\user" + "', (ConvertTo-SecureString '" + \
                "pw" + "' -AsPlainText -Force)))"
        
        result = prereq_check.check_windows(self.params)

        popen_args = mock_popen.call_args.args
        self.assertIn(
            ["powershell.exe", expected_command + additional_user_args
            ], popen_args)
        self.assertEqual(result[1], False)

    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("subprocess.Popen")
    def test_check_windows_fails_when_error(self, mock_popen, mock_get_server_credentials):
        self.mock_is_winrm_accessible_setup(mock_popen, '', '', 0)
        mock_get_server_credentials.return_value = {"username": "", "password": "pw"}
        mocked_popen = mock_popen.return_value
        output = "FreeSpace:Pass\nTCP443:Pass"
        error = "error"
        mocked_popen.communicate.return_value = (output.encode(), error.encode())
        expected_command = "Invoke-Command -ComputerName " + self.params["s"]["server_fqdn"] + \
              " -FilePath 0-Prerequisites-Windows.ps1 -ArgumentList " + \
              self.params["MGNServerIP"] + "," + self.params["MGNEndpoint"] + "," + self.params["S3Endpoint"]
        
        result = prereq_check.check_windows(self.params)

        popen_args = mock_popen.call_args.args
        self.assertIn(
            ["powershell.exe", expected_command
            ], popen_args)
        self.assertEqual(result[1], True)
    
    @mock.patch("subprocess.Popen")
    def test_check_windows_fails_winrm_not_accessible(self, mock_popen):
        self.mock_is_winrm_accessible_setup(mock_popen, '', '', 1)
        
        
        result = prereq_check.check_windows(self.params)

        self.assertEqual(result[1], True)

    @mock.patch("mfcommon.open_ssh")
    def test_check_ssh_connectivity_passes(self, mock_open_ssh):
        mock_open_ssh.return_value = "test ssh", ""

        result = prereq_check.check_ssh_connectivity("0.0.0.0", "test_user", "test_pw", "test_key", self.s_result)
  
        self.assertIn({'test': prereq_check.MSG_SSH_SOURCE, 'result': "Pass"}, self.s_result["test_results"])
        self.assertEqual(result, "test ssh")

    @mock.patch("mfcommon.open_ssh")
    def test_check_ssh_connectivity_passes(self, mock_open_ssh):
        mock_open_ssh.return_value = "test ssh", "error"

        result = prereq_check.check_ssh_connectivity("0.0.0.0", "test_user", "test_pw", "test_key", self.s_result)

        self.assertIn({
            "test": prereq_check.MSG_SSH_SOURCE, "result": "Fail", "error": "error"}, 
            self.s_result["test_results"]
        )
        self.assertEqual(result, None)

    @mock.patch("paramiko.SSHClient")
    def test_check_sudo_permissions_passes(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", "output", ""]

        prereq_check.check_sudo_permissions(mocked_ssh, self.s_result)

        self.assertIn({'test': prereq_check.MSG_SUDO_PERMISSION, 'result': "Pass"}, self.s_result["test_results"])

    @mock.patch("paramiko.SSHClient")
    def test_check_sudo_permissions_passes_when_stderr(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", "output", io.StringIO("error")]

        prereq_check.check_sudo_permissions(mocked_ssh, self.s_result)

        self.assertIn({'test': prereq_check.MSG_SUDO_PERMISSION, 'result': "Pass"}, self.s_result["test_results"])

    @mock.patch("paramiko.SSHClient")
    def test_check_sudo_permissions_fails_no_ssh(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value

        prereq_check.check_sudo_permissions(None, self.s_result)
        
        self.assertIn(
            {
                'test': prereq_check.MSG_SUDO_PERMISSION, 
                'result': "Fail", 
                'error': prereq_check.MSG_SSH_UNABLE_TO_CONNECT
            }, 
            self.s_result["test_results"]
        )

    @mock.patch("paramiko.SSHClient")
    def test_check_sudo_permissions_fails_when_exec_cmd_fails(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = mock_raise_paramiko_ssh_exception

        prereq_check.check_sudo_permissions(mocked_ssh, self.s_result)

        self.assertIn(
            {
                'test': prereq_check.MSG_SUDO_PERMISSION, 
                'result': "Fail", 
                'error': ""
            }, 
            self.s_result["test_results"]
        )
        self.assertEqual(self.s_result['success'], False)

    @mock.patch("paramiko.SSHClient")
    def test_check_sudo_permissions_fails_password_required_stderr(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", "output", io.StringIO("error\npassword is required")]

        prereq_check.check_sudo_permissions(mocked_ssh, self.s_result)

        self.assertIn(
            {
                'test': prereq_check.MSG_SUDO_PERMISSION, 
                'result': "Fail", 
                'error': 'password is required'
            }, 
            self.s_result["test_results"]
        )
        self.assertEqual(self.s_result['success'], False)

    @mock.patch("paramiko.SSHClient")
    def test_check_tcp_connectivity_passes(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO("output\nopen"), io.StringIO("")]
        cmd = self.check_windows_command(self.params["MGNEndpoint"], '443')

        prereq_check.check_tcp_connectivity(
            mocked_ssh, self.params["MGNEndpoint"], '443', self.s_result, "test")      

        self.assertIn({"test": "test-443", "result": "Pass"}, self.s_result["test_results"])
        self.assertIn(cmd, mocked_ssh.exec_command.call_args.args)

    @mock.patch("paramiko.SSHClient")
    def test_check_tcp_connectivity_passes_ssh_refused(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO(""), io.StringIO("error\nrefused")]
        cmd = self.check_windows_command(self.params["MGNEndpoint"], '443')

        prereq_check.check_tcp_connectivity(mocked_ssh, self.params["MGNEndpoint"], '443', self.s_result)
        
        self.assertIn({"test": " TCP 443 to Endpoint", "result": "Pass"}, self.s_result["test_results"])
        self.assertIn(cmd, mocked_ssh.exec_command.call_args.args)

    @mock.patch("paramiko.SSHClient")
    def test_check_tcp_connectivity_fails_open_not_in_stdout(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO("output"), io.StringIO("error\nrefused")]

        prereq_check.check_tcp_connectivity(mocked_ssh, self.params["MGNEndpoint"], '443', self.s_result)
        
        self.assertIn(
            {"test": " TCP 443 to Endpoint", "result": "Fail", "error": "output"}, 
            self.s_result["test_results"]
        )
        self.assertEqual(False, self.s_result["success"])

    @mock.patch("paramiko.SSHClient")
    def test_check_tcp_connectivity_fails_stderr(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO(""), io.StringIO("error")]

        prereq_check.check_tcp_connectivity(
            mocked_ssh, self.params["MGNEndpoint"], '1500', self.s_result
        )   
        self.assertIn(
            {"test": " TCP 1500 to MGN Rep Server", "result": "Fail", "error": "error"}, 
            self.s_result["test_results"]
        )
        self.assertEqual(False, self.s_result["success"])
        
    @mock.patch("paramiko.SSHClient")
    def test_check_tcp_connectivity_fails_paramiko_exception(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = mock_raise_paramiko_ssh_exception
        cmd = self.check_windows_command(self.params["MGNEndpoint"], '636')
        paramiko_error = f"Got exception! while executing the command {cmd}  due to "

        prereq_check.check_tcp_connectivity(
            mocked_ssh, self.params["MGNEndpoint"], '636', self.s_result
        )

        self.assertIn(
            {"test": " TCP 636", "result": "Fail", "error": paramiko_error}, self.s_result["test_results"]
        )
        self.assertEqual(False, self.s_result["success"])


    def test_check_tcp_connectivity_fails_no_ssh(self):
        prereq_check.check_tcp_connectivity(
            None, self.params["MGNEndpoint"], '636', self.s_result
        )   
        self.assertIn(
            {"test": " TCP 636", "result": "Fail", "error": prereq_check.MSG_SSH_UNABLE_TO_CONNECT},
            self.s_result["test_results"]
        )
        self.assertEqual(False, self.s_result["success"])
    
    @mock.patch("paramiko.SSHClient")
    def test_check_freespace_passes(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO("20g"), io.StringIO("")]
        cmd = self.check_freespace_command("/")

        prereq_check.check_freespace(mocked_ssh, "/", 10, self.s_result)

        self.assertIn(cmd, mocked_ssh.exec_command.call_args.args)
        self.assertIn({"test": "10 GB / FreeSpace", "result": "Pass"}, self.s_result["test_results"])

    @mock.patch("paramiko.SSHClient")
    def test_check_freespace_fails_insufficient_space(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO("20"), io.StringIO("")]
        cmd = self.check_freespace_command("/")
        min_error = "/" + " directory should have a minimum of " + str(
                    30) + " GB free space, but got " + str(20.0)

        prereq_check.check_freespace(mocked_ssh, "/", 30, self.s_result)

        self.assertIn(cmd, mocked_ssh.exec_command.call_args.args)
        self.assertIn({"test": "30 GB / FreeSpace", "result": "Fail", "error": min_error}, self.s_result["test_results"])

    @mock.patch("paramiko.SSHClient")
    def test_check_freespace_fails_paramiko_exception(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = mock_raise_paramiko_ssh_exception
        cmd = self.check_freespace_command("/")
        expected_error = f"Got exception! while executing the command {cmd}  due to "

        prereq_check.check_freespace(mocked_ssh, "/", 30, self.s_result)

        self.assertIn(
            {"test": "30 GB / FreeSpace", "result": "Fail", "error": expected_error}, 
            self.s_result["test_results"]
        )

    def test_check_freespace_fails_no_ssh(self):
        prereq_check.check_freespace(None, "/", 30, self.s_result)

        self.assertIn(
            {"test": "30 GB / FreeSpace", "result": "Fail", "error": prereq_check.MSG_SSH_UNABLE_TO_CONNECT}, 
            self.s_result["test_results"]
        )

    @mock.patch("paramiko.SSHClient")
    def test_check_freespace_fails_stderr(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", io.StringIO("20"), io.StringIO("error")]

        prereq_check.check_freespace(mocked_ssh, "/", 10, self.s_result)

        self.assertIn(
            {"test": "10 GB / FreeSpace", "result": "Fail", "error": "error"}, 
            self.s_result["test_results"]
        )

    @mock.patch("paramiko.SSHClient")
    def test_check_dhclient_passes(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", "ouput", io.StringIO("")]
        cmd = self.check_dhclient_command()

        prereq_check.check_dhclient(mocked_ssh, self.s_result)

        self.assertIn(cmd, mocked_ssh.exec_command.call_args.args)
        self.assertIn({"test": "DHCLIENT Package", "result": "Pass", "error": ""}, self.s_result["test_results"])

    @mock.patch("paramiko.SSHClient")
    def test_check_dhclient_passes_with_stderr(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", "ouput", io.StringIO("error")]
        cmd = self.check_dhclient_command()

        prereq_check.check_dhclient(mocked_ssh, self.s_result)

        self.assertIn(cmd, mocked_ssh.exec_command.call_args.args)
        self.assertIn(
            {"test": "DHCLIENT Package", "result": "Pass", "error": "error"}, 
            self.s_result["test_results"]
        )

    def test_check_dhclient_fails_no_ssh(self):
        prereq_check.check_dhclient(None, self.s_result)

        self.assertIn({
            "test": "DHCLIENT Package", "result": "Fail", "error": prereq_check.MSG_SSH_UNABLE_TO_CONNECT}, 
            self.s_result["test_results"]
        )
        self.assertEquals(False, self.s_result["success"])

    @mock.patch("paramiko.SSHClient")
    def test_check_dhclient_paramiko_exception(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command = mock_raise_paramiko_ssh_exception

        prereq_check.check_dhclient(mocked_ssh, self.s_result)

        self.assertIn({'test': "DHCLIENT Package", "result": "Fail", "error": ""}, self.s_result["test_results"])
        self.assertEquals(False, self.s_result["success"])

    @mock.patch("paramiko.SSHClient")
    def test_check_dhclient_fails_stderr_contains_not_found(self, mock_ssh_client):
        mocked_ssh = mock_ssh_client.return_value
        mocked_ssh.exec_command.return_value = ["input", "ouput", io.StringIO("error\nnot found")]

        prereq_check.check_dhclient(mocked_ssh, self.s_result)

        self.assertIn(
            {"test": "DHCLIENT Package", "result": "Fail", "error": "error\nnot found"}, 
            self.s_result["test_results"]
        )

    @mock.patch.object(prereq_check, "check_dhclient")
    @mock.patch.object(prereq_check, "check_freespace")
    @mock.patch.object(prereq_check, "check_tcp_connectivity")
    @mock.patch.object(prereq_check, "check_sudo_permissions")
    @mock.patch.object(prereq_check, "check_ssh_connectivity")
    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("paramiko.SSHClient")
    def test_check_linux(self, 
        mock_ssh_client,
        mock_get_server_creds, 
        mock_ssh_connectivity,
        mock_sudo_permissions,
        mock_tcp_connectivity, 
        mock_freespace,mock_dhclient):

        mocked_ssh = mock_ssh_client.return_value
        mock_ssh_connectivity.return_value = mocked_ssh
        mock_get_server_creds.return_value = {
            "username": "test-user", 
            "password": "test-pw", 
            "private_key": "test-key"
        }

        result = prereq_check.check_linux(self.params)

        self.assertEquals(mock_tcp_connectivity.call_count, 3)
        self.assertIn(
            [
                mock.call(mocked_ssh, self.params["MGNEndpoint"], '443', self.s_result, "MGNEndpoint"),
                mock.call(mocked_ssh, self.params["S3Endpoint"], '443', self.s_result, "S3Endpoint"),
                mock.call(mocked_ssh, self.params["MGNServerIP"], '1500', self.s_result),
            ],
            mock_tcp_connectivity.call_args_list
        )
        self.assertEquals(mock_freespace.call_count, 2)
        self.assertIn(
            [
                mock.call(mocked_ssh, '/', 2.0, self.s_result),
                mock.call(mocked_ssh, '/tmp', 0.5, self.s_result),
            ],
            mock_freespace.call_args_list
        )
        mock_dhclient.assert_called_with(mocked_ssh, self.s_result)
        mock_sudo_permissions.assert_called_with(mocked_ssh, self.s_result)
        mock_ssh_connectivity.assert_called_with(
            self.params["s"]["server_fqdn"], 
            mock_get_server_creds.return_value["username"], 
            mock_get_server_creds.return_value['password'],
            mock_get_server_creds.return_value['private_key'],
            self.s_result
        )
        self.assertTrue(mocked_ssh.close.called)

    def test_parse_boolean_true_values(self):
        true_values = ["true", "yes", "y", "1", "t"]

        for value in true_values:
            result = prereq_check.parse_boolean(value)
            self.assertEqual(True, result)

    def test_parse_boolean_false_values(self):
        false_values = ["false", "no", "n", "0", "f"]
        
        for value in false_values:
            result = prereq_check.parse_boolean(value)
            self.assertEqual(False, result)

    def test_parse_boolean_other_values(self):
        other_values = ["2", "q", "random", "!@34]", "-5"]
        
        for value in other_values:
            result = prereq_check.parse_boolean(value)
            self.assertEqual(False, result)

    def test_parse_arguments_returns_args(self):
        args = ["--Waveid", "1", "--ReplicationServerIP", "0.0.0.0"]
        expectedResponse = Namespace(
            Waveid='1', 
            ReplicationServerIP='0.0.0.0', 
            NoPrompts=False, 
            SecretWindows=None, 
            SecretLinux=None, 
            S3Endpoint=None, 
            MGNEndpoint=None, 
            UseSSL=False
        )

        response = prereq_check.parse_arguments(args)

        self.assertEqual(response, expectedResponse)

    @mock.patch("mfcommon.update_server_migration_status")
    @mock.patch.object(prereq_check, "check_linux")
    @mock.patch.object(prereq_check, "check_windows")
    @mock.patch("threading.Thread", new=MockThread)
    @mock.patch("mfcommon.add_windows_servers_to_trusted_hosts")
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login")
    def test_main_passes(self, mock_login, mock_get_servers, mock_windows_trusted, mock_check_windows, 
                         mock_check_linux, mock_update_server_migration_status):
        args = ["--Waveid", "1", "--ReplicationServerIP", "0.0.0.0"]
        args = prereq_check.parse_arguments(args)
        mock_login.return_value = "test-token"
        mock_check_windows.return_value = (self.s_result, False)
        mock_check_linux.return_value = (self.s_result, False)
        servers_response = [
            {'aws_accountid': '111111111111', 
             'aws_region': 'us-east-1', 
             'servers_windows': [{"server_fqdn": "winserv1"}, {"server_fqdn": "winserv2"}], 
             'servers_linux': [{"server_fqdn": "aml1"}, {"server_fqdn": "aml2"}]
            },
        ]
        mock_get_servers.return_value = (servers_response, True, True)

        
        account = {"aws_region": "test-region-1"}
    
        response = prereq_check.main(args)

        self.assertEqual(0, response)

    @mock.patch("mfcommon.update_server_migration_status")
    @mock.patch.object(prereq_check, "check_linux")
    @mock.patch.object(prereq_check, "check_windows")
    @mock.patch("threading.Thread", new=MockThread)
    @mock.patch("mfcommon.add_windows_servers_to_trusted_hosts")
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login")
    def test_main_linux_fails(self, mock_login, mock_get_servers, mock_windows_trusted, mock_check_windows, 
                              mock_check_linux, mock_update_server_migration_status):
        args = ["--Waveid", "1", "--ReplicationServerIP", "0.0.0.0"]
        args = prereq_check.parse_arguments(args)
        mock_login.return_value = "test-token"
        mock_check_windows.return_value = (self.s_result, False)
        mock_check_linux.return_value = (self.s_result, True)
        servers_response = [
            {'aws_accountid': '111111111111', 
             'aws_region': 'us-east-1', 
             'servers_windows': [{"server_fqdn": "winserv1"}, {"server_fqdn": "winserv2"}], 
             'servers_linux': [{"server_fqdn": "aml1"}, {"server_fqdn": "aml2"}]
            },
        ]
        mock_get_servers.return_value = (servers_response, True, True)
    
        response = prereq_check.main(args)

        self.assertEqual(1, response)

    @mock.patch("mfcommon.update_server_migration_status")
    @mock.patch.object(prereq_check, "check_linux")
    @mock.patch.object(prereq_check, "check_windows")
    @mock.patch("threading.Thread", new=MockThread)
    @mock.patch("mfcommon.add_windows_servers_to_trusted_hosts")
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login")
    def test_main_windows_fails(self, mock_login, mock_get_servers, mock_windows_trusted, mock_check_windows, mock_check_linux, mock_update_server_migration_status):
        args = ["--Waveid", "1", "--ReplicationServerIP", "0.0.0.0"]
        args = prereq_check.parse_arguments(args)
        mock_login.return_value = "test-token"

        mock_check_windows.return_value = (self.s_result, True)
        mock_check_linux.return_value = (self.s_result, False)
        servers_response = [
            {'aws_accountid': '111111111111', 
             'aws_region': 'us-east-1', 
             'servers_windows': [{"server_fqdn": "winserv1"}, {"server_fqdn": "winserv2"}], 
             'servers_linux': [{"server_fqdn": "aml1"}, {"server_fqdn": "aml2"}]
            },
        ]
        mock_get_servers.return_value = (servers_response, True, True)
    
        response = prereq_check.main(args)

        self.assertEqual(1, response)
