#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import TestCase, mock
import importlib
from mgn.test_mgn_common import mock_file_open, default_mock_os_environ
from cmf_logger import logger
import test_util

distribution = ''
ssh_client = test_util.MockParamiko()

DEFAULT_OUTPUT = 'error\n'

EXPECTED_RESPONSE_PYTHON_INSTALL_SUCCESSS = {
            'messages': ['***** Installing python3 *****',
                         'python was installed successfully.']
}

EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS = {
    'messages': ['***** Installing wget *****', 'wget got installed successfully']
}


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
    def test_install_wget_any_dist(self, find_distribution):
        logger.info("Testing Agent Install main: "
                    "wget install unknown dist")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''
        final_output = {"messages": []}
        agent_install.install_wget("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='ubuntu')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_wget_ubuntu_dist(self, find_distribution):
        logger.info("Testing Agent Install main: "
                    "wget install ubuntu dist")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''
        final_output = {"messages": []}
        agent_install.install_wget("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='suse')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_wget_suse_dist(self, find_distribution):
        logger.info("Testing Agent Install main: "
                    "wget install suse dist")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''

        final_output = {"messages": []}
        agent_install.install_wget("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_WGET_INSTALL_SUCCESS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_wget_error(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "error returned by wget install")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = DEFAULT_OUTPUT

        final_output = {"messages": []}
        agent_install.install_wget("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, {
            'messages': ['***** Installing wget *****',
                         'something went wrong while installing wget error\n']})

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_python_unknown_dist(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python installation")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''

        final_output = {"messages": []}
        agent_install.install_python3("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_PYTHON_INSTALL_SUCCESSS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='ubuntu')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_python_ubuntu(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python installation ubuntu")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''

        final_output = {"messages": []}
        agent_install.install_python3("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_PYTHON_INSTALL_SUCCESSS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='suse')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_python_suse(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python installation suse")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''

        final_output = {"messages": []}
        agent_install.install_python3("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_PYTHON_INSTALL_SUCCESSS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='fedora')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_python_fedora(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python installation fedora")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = ''

        final_output = {"messages": []}
        agent_install.install_python3("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, EXPECTED_RESPONSE_PYTHON_INSTALL_SUCCESSS)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='fedora')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_install_python_error(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python installation error")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = DEFAULT_OUTPUT

        final_output = {"messages": []}
        agent_install.install_python3("host", "username", "key_pwd", False, final_output)

        self.assertEqual(final_output, {
            'messages': ['***** Installing python3 *****',
                         DEFAULT_OUTPUT]})


    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='fedora')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_check_python_3_installed(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python check version 3 installed")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = 'Python 3'

        response = agent_install.check_python3("host", "username", "key_pwd", False)

        self.assertEqual(response, True)

    @mock.patch("mfcommon.open_ssh",
                new=ssh_open)
    @mock.patch("paramiko.SSHClient",
                new=ssh_open)
    @mock.patch("mfcommon.find_distribution",
                return_value='fedora')
    @mock.patch('builtins.open', new=mock_file_open)
    def test_check_python_3_not_installed(self, mock_find_dist):
        logger.info("Testing Agent Install: "
                    "python check version 3 installed")

        agent_install = importlib.import_module('1-Install-Linux')

        ssh_client.stderr_string = 'Python 2'

        response = agent_install.check_python3("host", "username", "key_pwd", False)

        self.assertEqual(response, False)