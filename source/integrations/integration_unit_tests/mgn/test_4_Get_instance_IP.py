#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import importlib
import unittest
from unittest.mock import patch, ANY
from moto import mock_sts, mock_ec2

import mgn.test_mgn_common as test_mgn_common
from mgn.test_mgn_common import mock_file_open, default_mock_os_environ, logger, servers_list, mock_boto_api_call,\
    mock_factory_login, mock_get_factory_servers, servers_list_no_fdqn, servers_list_with_instance_id


@mock_ec2
@mock_sts
@patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
@patch('mfcommon.factory_login', new=mock_factory_login)
@patch('mfcommon.get_factory_servers', new=mock_get_factory_servers)
@patch.dict('os.environ', default_mock_os_environ)
@patch('csv.DictWriter')
class VerifyInstanceStatusTestCase(unittest.TestCase):

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_id_mgn_with_running_ok(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        result = get_instance_ip.get_instance_id(copy.deepcopy(servers_list))
        self.assertEqual('i-111111111111', result[0]['servers'][0]['target_ec2InstanceID'])
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_id_mgn_instance_id_not_matching(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_instance_id_not_matching'
        result = get_instance_ip.get_instance_id(copy.deepcopy(servers_list))
        self.assertEqual('', result[0]['servers'][0]['target_ec2InstanceID'])
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_id_mgn_no_in(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        result = get_instance_ip.get_instance_id(copy.deepcopy(servers_list))
        self.assertEqual(result, servers_list)
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_id_server_no_server_fdqn(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        with self.assertRaises(SystemExit):
            get_instance_ip.get_instance_id(copy.deepcopy(servers_list_no_fdqn))
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_ips_no_instance_id(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        get_instance_ip.get_instance_ips(copy.deepcopy(servers_list), "1")
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_ips_with_instance_id_no_name(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'describe_instance_no_name'
        with self.assertRaises(SystemExit):
            get_instance_ip.get_instance_ips(copy.deepcopy(servers_list_with_instance_id), "1")
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_ips_with_instance_id_name(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'describe_instance_with_name'
        get_instance_ip.get_instance_ips(copy.deepcopy(servers_list_with_instance_id), "1")
        mock_csv_writer.assert_called_with(ANY, {'instance_ips': '192.168.0.5', 'instance_name': 'Name1'}.keys())

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_ips_with_instance_id_name_no_private_ip(self, mock_csv_writer):
        # works with no private ip too, not sure by design
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'describe_instance_no_private_ip'
        get_instance_ip.get_instance_ips(copy.deepcopy(servers_list_with_instance_id), "1")
        mock_csv_writer.assert_called_with(ANY, {'instance_ips': '', 'instance_name': 'Name1'}.keys())

    @patch('builtins.open', new=mock_file_open)
    def test_get_instance_ips_empty_instance_list(self, mock_csv_writer):
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        get_instance_ip.get_instance_ips([], "1")
        self.assertEqual(0, mock_csv_writer.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_main(self, mock_csv_writer):
        # no need to cover all cases, only make sure that main works
        # because all those cases are tested above by testing the function verify_replication
        get_instance_ip = importlib.import_module('4-Get-instance-IP')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        get_instance_ip.main(["--Waveid", "1"])
        mock_csv_writer.assert_called_with(ANY, {'instance_ips': '192.168.0.5', 'instance_name': 'Name1'}.keys())