#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import io
import sys
from unittest import TestCase, mock
import importlib
from automation_packages.ads.test_ads_common import mock_file_open, default_mock_os_environ
from cmf_logger import logger
import test_util

distribution = ''
ssh_client = test_util.MockParamiko()

DEFAULT_OUTPUT = 'error\n'

EXPECTED_RESPONSE_PYTHON_INSTALL_SUCCESSS = {
            'messages': ['***** Installing python3 *****',
                         'python was installed successfully.']
}

EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS = '\n***** Installing wget *****\nwget got installed successfully\n'


def ssh_open(host, username, key_pwd, using_key, multi_threaded=False):
    return ssh_client, ''


def ssh_exec_command(host, username, key, using_key):
    return


def find_distribution(host, username, key, using_key):
    return distribution


@mock.patch.dict('os.environ', default_mock_os_environ)
class InstallLinux(TestCase):
    distribution = ''

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='')
    @mock.patch('builtins.open', new=mock_file_open)
    @mock.patch('sys.stdout', new=io.StringIO())
    def test_install_wget_any_dist(self, find_distribution):
        logger.info("Testing Agent Install main: "
                    "wget install unknown dist")

        agent_install = importlib.import_module('1-ADS-Install-Linux')

        ssh_client.stderr_string = ''

        agent_install.install_wget("host", "username", "key_pwd", False)

        output = sys.stdout.getvalue()

        self.assertEqual(output,  EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='ubuntu')
    @mock.patch('builtins.open', new=mock_file_open)
    @mock.patch('sys.stdout', new=io.StringIO())
    def test_install_wget_ubuntu_dist(self, find_distribution):
        logger.info("Testing Agent Install main: "
                    "wget install ubuntu dist")

        agent_install = importlib.import_module('1-ADS-Install-Linux')

        ssh_client.stderr_string = ''
        agent_install.install_wget("host", "username", "key_pwd", False)

        output = sys.stdout.getvalue()

        self.assertEqual(output,  EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='suse')
    @mock.patch('builtins.open', new=mock_file_open)
    @mock.patch('sys.stdout', new=io.StringIO())
    def test_install_wget_suse_dist(self, find_distribution):
        logger.info("Testing Agent Install main: "
                    "wget install suse dist")

        agent_install = importlib.import_module('1-ADS-Install-Linux')

        ssh_client.stderr_string = ''

        agent_install.install_wget("host", "username", "key_pwd", False)
        output = sys.stdout.getvalue()

        self.assertEqual(output,  EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='')
    @mock.patch('builtins.open', new=mock_file_open)
    @mock.patch('sys.stdout', new=io.StringIO())
    def test_install_wget_error(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "error returned by wget install")

        agent_install = importlib.import_module('1-ADS-Install-Linux')

        ssh_client.stderr_string = DEFAULT_OUTPUT

        agent_install.install_wget("host", "username", "key_pwd", False)
        output = sys.stdout.getvalue()

        self.assertEqual(output,  '\n***** Installing wget *****\nsomething went wrong while installing wget  error\n\n')
