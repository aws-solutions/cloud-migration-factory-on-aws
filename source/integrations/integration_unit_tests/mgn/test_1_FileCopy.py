#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
from unittest import TestCase, mock
import importlib
from pathlib import Path
from operator import itemgetter

def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[2]

    sys.path.append(str(package_root_directory))
    sys.path.append(str(package_root_directory) + "/common/")
    sys.path.append(str(package_root_directory) + "/mgn/MGN-automation-scripts/1-FileCopy")

init()
filecopy = importlib.import_module('1-FileCopy')

class FileCopyTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.mock_user = {
            "username": "test-user", 
            "password": "test-pw", 
            "private_key": "test-key"
        }
        self.mock_user_with_prefix = {
            "username": "server\\test-user", 
            "password": "test-pw", 
            "private_key": "test-key"
        }
        self.mock_factory_servers = [
            {'aws_accountid': '111111111111', 
             'aws_region': 'us-east-1', 
             'servers_windows': [{"server_fqdn": "winserv1"}, {"server_fqdn": "winserv2"}], 
             'servers_linux': [{"server_fqdn": "aml1"}, {"server_fqdn": "aml2"}]
            },
        ]
        self.upload_files_commands = [
            "[ -d /tmp/copy_ce_files ] && echo 'Directory exists' || mkdir /tmp/copy_ce_files",
            "[ -d '/boot/post_launch' ] && echo 'Directory exists' || sudo mkdir /boot/post_launch",
            "sudo cp /tmp/copy_ce_files/* /boot/post_launch && sudo chown aws-replication /boot/post_launch/* && sudo chmod +x /boot/post_launch/*"
        ]

    def tearDown(self):
        super().tearDown()

    def mock_is_file(path):
        if('.' in path):
            return True
        else:
            return False
        
    def mock_upload_file_params(self, filepath):
        return ("winserv1", "test-user", "test-pw", "test-key", filepath)
    
    def mock_error(self):
        raise Exception("raised exception")
    
    def mock_main_commands(self, user, pw, source, fqdn):
        creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + \
                user + "', (ConvertTo-SecureString '" + pw + "' -AsPlainText -Force)))"
        destpath = "'c:\\Program Files (x86)\\AWS Replication Agent\\post_launch\\'"
        sourcepath = "'" + source + "\\*'"
        command1 = "Invoke-Command -ComputerName " + fqdn + " -ScriptBlock {if (!(Test-Path -Path " + destpath + \
            ")) {New-Item -Path " + destpath + " -ItemType directory}}" + creds
        command2 = "$Session = New-PSSession -ComputerName " + fqdn + creds + "\rCopy-Item -Path " + sourcepath + " -Destination " + destpath + " -ToSession $Session"

        return command1, command2

    @mock.patch("os.path.isfile", new=mock_is_file)
    @mock.patch("mfcommon.open_ssh")
    @mock.patch("paramiko.SSHClient")
    def test_upload_files_passes_with_file(self, mock_ssh_client, mock_open_ssh):
        mocked_ssh = mock_ssh_client.return_value
        mock_open_ssh.return_value = mocked_ssh, ""
        mocked_ftp = mocked_ssh.open_sftp.return_value
        file_path = "/file.test"

        result = filecopy.upload_files(*self.mock_upload_file_params(file_path))

        self.assertEqual(
            mocked_ssh.exec_command.call_args_list, 
            [        
                mock.call(self.upload_files_commands[0]),
                mock.call(self.upload_files_commands[1]),
                mock.call(self.upload_files_commands[2])
            ]
        )
        mocked_ftp.put.assert_called_with("/file.test", '/tmp/copy_ce_files/' + "file.test")
        mocked_ssh.close.assert_called()
        mocked_ftp.close.assert_called()
        self.assertEqual("", result)

    @mock.patch("os.listdir")
    @mock.patch("os.path.isfile", new=mock_is_file)
    @mock.patch("mfcommon.open_ssh")
    @mock.patch("paramiko.SSHClient")
    def test_upload_files_passes_with_dir(self, mock_ssh_client, mock_open_ssh, mock_list_dir):
        mocked_ssh = mock_ssh_client.return_value
        mock_open_ssh.return_value = mocked_ssh, ""
        mocked_ftp = mocked_ssh.open_sftp.return_value
        file_path = "/path"
        mock_list_dir.return_value = ["file.py" , "file2.txt", "subdir"]

        result = filecopy.upload_files(*self.mock_upload_file_params(file_path))

        self.assertEqual(
            mocked_ssh.exec_command.call_args_list, 
            [        
                mock.call(self.upload_files_commands[0]),
                mock.call(self.upload_files_commands[1]),
                mock.call(self.upload_files_commands[2])
            ]
        )
        self.assertEqual(
            mocked_ftp.put.call_args_list,
            [
                mock.call("/path/file.py", '/tmp/copy_ce_files/' + "file.py"),
                mock.call("/path/file2.txt", '/tmp/copy_ce_files/' + "file2.txt"),
            ]
        )
        mocked_ssh.close.assert_called()
        mocked_ftp.close.assert_called()
        self.assertEqual("", result)

    @mock.patch("mfcommon.open_ssh")
    @mock.patch("paramiko.SSHClient")
    def test_upload_files_fails_ssh_error(self, mock_ssh_client, mock_open_ssh):
        mock_open_ssh.return_value = None, "error"

        result = filecopy.upload_files(*self.mock_upload_file_params("/test/path"))

        self.assertEqual("error", result)

    @mock.patch("os.path.isfile", new=mock_error)
    @mock.patch("mfcommon.open_ssh")
    @mock.patch("paramiko.SSHClient")
    def test_upload_files_fails_ssh_error(self, mock_ssh_client, mock_open_ssh):
        mocked_ssh = mock_ssh_client.return_value
        mock_open_ssh.return_value = mocked_ssh, ""
        file_path = "/test/path"

        result = filecopy.upload_files(*self.mock_upload_file_params(file_path))

        self.assertEqual(
            "Copying " + file_path + " to " + "/boot/post_launch" + " on host " + "winserv1" + \
            " failed due to " + "raised exception", 
            result
        )

    @mock.patch("time.sleep", new=lambda _: None)
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login", new=lambda : "test-token")
    def test_main_passes_no_servers(self, mock_get_servers):
        args = ["--Waveid", "1", "--WindowsSource", "winsrc", "--LinuxSource", "linuxsrc"]
        mock_get_servers.return_value = self.mock_factory_servers, False, False

        result = filecopy.main(args)

        self.assertEqual(0, result)

    @mock.patch("time.sleep", lambda _: None)
    @mock.patch.object(filecopy, "upload_files")
    @mock.patch("subprocess.Popen")
    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login", new=lambda : "test-token")
    def test_main_passes_with_linux_and_windows(self, mock_get_servers, mock_get_creds, mock_popen, mock_upload):
        args = ["--Waveid", "1", "--WindowsSource", "winsrc", "--LinuxSource", "linuxsrc"]
        mock_get_servers.return_value = self.mock_factory_servers, True, True
        mock_get_creds.return_value = self.mock_user
        mocked_popen = mock_popen.return_value
        mocked_popen.communicate.return_value = "", ""
        mock_upload.return_value = ""

        result = filecopy.main(args)

        for server in self.mock_factory_servers[0]["servers_windows"]:
            cmd1, cmd2 = self.mock_main_commands(self.mock_user["username"], self.mock_user["password"], 
                "winsrc", server["server_fqdn"]
            )
            self.assertIn(mock.call(["powershell.exe", cmd1], stdout=-1, stderr=-1),mock_popen.call_args_list)
            self.assertIn(mock.call(["powershell.exe", cmd2], stdout=-1, stderr=-1), mock_popen.call_args_list)
        for server in self.mock_factory_servers[0]["servers_linux"]:
            self.assertIn(
                mock.call(
                    server['server_fqdn'], 
                    *itemgetter("username", "password", "private_key")(self.mock_user), 
                    "linuxsrc"
                ),
                mock_upload.call_args_list
            )
        self.assertEqual(0, result)

    @mock.patch("time.sleep", lambda value: None)
    @mock.patch.object(filecopy, "upload_files")
    @mock.patch("subprocess.Popen")
    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login", new=lambda : "test-token")
    def test_main_fails_windows_copy_item(self, mock_get_servers, mock_get_creds, mock_popen, mock_upload):
        args = ["--Waveid", "1", "--WindowsSource", "winsrc", "--LinuxSource", "linuxsrc"]
        mock_get_servers.return_value = self.mock_factory_servers, True, True
        mock_get_creds.return_value = self.mock_user
        mocked_popen = mock_popen.return_value
        mocked_popen.communicate.return_value = "", "ErrorId: copy error"
        mock_upload.return_value = ""

        result = filecopy.main(args)

        for server in self.mock_factory_servers[0]["servers_windows"]:
            cmd1, cmd2 = self.mock_main_commands(self.mock_user["username"], self.mock_user["password"], 
                "winsrc", server["server_fqdn"]
            )
            self.assertIn(mock.call(["powershell.exe", cmd1], stdout=-1, stderr=-1),mock_popen.call_args_list)
            self.assertIn(mock.call(["powershell.exe", cmd2], stdout=-1, stderr=-1), mock_popen.call_args_list)
        for server in self.mock_factory_servers[0]["servers_linux"]:
            self.assertIn(
                mock.call(
                    server['server_fqdn'], 
                    *itemgetter("username", "password", "private_key")(self.mock_user), 
                    "linuxsrc"
                ),
                mock_upload.call_args_list
            )
        self.assertEqual(1, result)

    @mock.patch("time.sleep", lambda value: None)
    @mock.patch.object(filecopy, "upload_files")
    @mock.patch("subprocess.Popen")
    @mock.patch("mfcommon.get_server_credentials")
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login", new=lambda : "test-token")
    def test_main_fails_linux_upload(self, mock_get_servers, mock_get_creds, mock_popen, mock_upload):
        args = ["--Waveid", "1", "--WindowsSource", "winsrc", "--LinuxSource", "linuxsrc"]
        mock_get_servers.return_value = self.mock_factory_servers, True, True
        mock_get_creds.return_value = self.mock_user_with_prefix
        mocked_popen = mock_popen.return_value
        mocked_popen.communicate.return_value = "", ""
        mock_upload.return_value = "upload error"

        result = filecopy.main(args)

        for server in self.mock_factory_servers[0]["servers_windows"]:
            cmd1, cmd2 = self.mock_main_commands(self.mock_user_with_prefix["username"], self.mock_user_with_prefix["password"], 
                "winsrc", server["server_fqdn"]
            )
            self.assertIn(mock.call(["powershell.exe", cmd1], stdout=-1, stderr=-1),mock_popen.call_args_list)
            self.assertIn(mock.call(["powershell.exe", cmd2], stdout=-1, stderr=-1), mock_popen.call_args_list)
        for server in self.mock_factory_servers[0]["servers_linux"]:
            self.assertIn(
                mock.call(
                    server['server_fqdn'], 
                    *itemgetter("username", "password", "private_key")(self.mock_user_with_prefix), 
                    "linuxsrc"
                ),
                mock_upload.call_args_list
            )
        self.assertEqual(1, result)
    
    @mock.patch("mfcommon.get_factory_servers")
    @mock.patch("mfcommon.factory_login", new=lambda : "test-token")
    def test_main_fails_missing_source_args(self, mock_get_servers):
        args = ["--Waveid", "1"]
        mock_get_servers.return_value = self.mock_factory_servers, True, True

        with self.assertRaises(SystemExit):
            filecopy.main(args)\
        