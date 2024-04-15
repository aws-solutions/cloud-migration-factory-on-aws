#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import copy
import importlib
import subprocess
import unittest
from unittest.mock import patch
from moto import mock_aws
import boto3

import mgn.test_mgn_common as test_mgn_common
from mgn.test_mgn_common import mock_file_open, default_mock_os_environ, logger, servers_list, mock_boto_api_call, \
    mock_factory_login, mock_get_factory_servers, servers_list_no_fdqn, \
    mock_get_server_credentials, mock_add_windows_servers_to_trusted_hosts, servers_list_linux, mock_execute_cmd, \
    servers_list_linux_private_ip, mock_create_csv_report


@mock_aws
@patch('botocore.client.BaseClient._make_api_call', new=mock_boto_api_call)
@patch('mfcommon.get_server_credentials', new=mock_get_server_credentials)
@patch('mfcommon.get_factory_servers', new=mock_get_factory_servers)
@patch('mfcommon.factory_login', new=mock_factory_login)
@patch('mfcommon.add_windows_servers_to_trusted_hosts', new=mock_add_windows_servers_to_trusted_hosts)
@patch('mfcommon.execute_cmd', new=mock_execute_cmd)
@patch('mfcommon.create_csv_report', new=mock_create_csv_report)
@patch.dict('os.environ', default_mock_os_environ)
class PostCutoverValidationsTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.popen_orig = subprocess.Popen

    def setUp(self) -> None:
        self.base_report_windows = [
            {
                'waveId': '1',
                'serverName': 'server1.local',
                'serverType': 'Windows',
                'validationStatus': 'Pass',
                'termination_protection_enabled': 'Pass',
                'mandatory_tags': 'Pass',
                'Linux_Apps': 'NA',
                'amazon-ssm-agent': 'NA',
                'host_ip_check_status': 'NA',
                '': 'NA',
                'host_ip': 'NA',
                'Windows_Apps': 'Windows_Apps',
                'Win_Wanted_Apps': 'Win_Wanted_Apps ->',
                'Amazon SSM Agent': 'NA',
                'Win_UnWanted_Apps': 'Win_UnWanted_Apps ->',
                'McAfee': 'NA',
                'Norton': 'NA',
                'Symantec': 'NA',
                'VMWare Tools': 'NA',
                'AVG': 'NA',
                'Qualys': 'NA',
                'Win_Running_Apps': 'Win_Running_Apps ->',
                'AmazonSSMAgent': 'NA'
            }
        ]
        self.base_report_linux = [
            {
                '': 'NA',
                'AVG': 'NA',
                'Amazon SSM Agent': 'NA',
                'AmazonSSMAgent': 'NA',
                'Linux_Apps': 'Linux_Apps',
                'McAfee': 'NA',
                'Norton': 'NA',
                'Qualys': 'NA',
                'Symantec': 'NA',
                'VMWare Tools': 'NA',
                'Win_Running_Apps': 'NA',
                'Win_UnWanted_Apps': 'NA',
                'Win_Wanted_Apps': 'NA',
                'Windows_Apps': 'NA',
                'amazon-ssm-agent': 'Pass',
                'host_ip': '192.168.0.5',
                'host_ip_check_status': 'NA',
                'mandatory_tags': 'Pass',
                'serverName': 'server1.local',
                'serverType': 'Linux',
                'termination_protection_enabled': 'Pass',
                'validationStatus': 'Pass',
                'waveId': '1'
            }
        ]

    @patch('builtins.open', new=mock_file_open)
    def test_no_matching_server(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        with self.assertRaises(SystemExit):
            post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), None)

    @patch('builtins.open', new=mock_file_open)
    def test_no_fdqn(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_matching_server'
        with self.assertRaises(SystemExit):
            post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_no_fdqn), None)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_no_instance_id(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_no_instance_id'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        with self.assertRaises(SystemExit):
            post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        self.assertEqual(0, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_not_matching_instance_id(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_instance_id_not_matching'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        with self.assertRaises(SystemExit):
            post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        self.assertEqual(0, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_with_popen_unexpected_output(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            PostCutoverValidationsTestCase.popen_orig(['echo', 'unexpected'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['unexpected'] = 'unexpected'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_with_popen_unexpected_output_multi(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            PostCutoverValidationsTestCase.popen_orig(['echo', 'unexpected,multi1,multi2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['unexpected'] = 'multi1'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_with_popen_std_error(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            PostCutoverValidationsTestCase.popen_orig(['sh', 'echo'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_with_popen_set_validation_status_custom(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            PostCutoverValidationsTestCase.popen_orig(['echo', 'validationStatus|test_validation_status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_with_popen_set_validation_status_pass(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            PostCutoverValidationsTestCase.popen_orig(['echo', 'validationStatus|Pass'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_with_popen_set_validation_status_fail(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        mock_popen.side_effect = lambda pargs, stdout=None, stderr=None: \
            PostCutoverValidationsTestCase.popen_orig(['echo', 'validationStatus|Fail'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_domain_credentials(
            self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        post_cutover_validations.mfcommon.get_server_credentials = \
            lambda local_username, local_password, server, secret_override=None, no_user_prompts=False: {
                'username': 'test_user@example.com',
                'password': 'test_password',
            }
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_true_credentials_exception(
            self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        post_cutover_validations.mfcommon.get_server_credentials = \
            lambda local_username, local_password, server, secret_override=None, no_user_prompts=False: \
                exec('raise Exception("Simulated Error")')
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        self.assertRaises(
            Exception, post_cutover_validations.verify_instance_details, copy.deepcopy(servers_list), args)
        self.assertEqual(0, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_false(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_false'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['termination_protection_enabled'] = 'Fail'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_false_enable_200(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_false'
        test_mgn_common.CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_200'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--EnableTerminationProtection', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['termination_protection_enabled'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_false_enable_500(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_false'
        test_mgn_common.CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_500'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--EnableTerminationProtection', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['termination_protection_enabled'] = 'Fail'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_mgn_with_running_ok_disable_api_termination_false_enable_error(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_false'
        test_mgn_common.CUT_OVER_MODIFY_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_error'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--EnableTerminationProtection', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list), args)
        expected_report = copy.deepcopy(self.base_report_windows)
        expected_report[0]['termination_protection_enabled'] = 'NA'
        expected_report[0]['validationStatus'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'default'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['host_ip_check_status'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_non_existing_tag(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'default'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--Tags', 'NonExistingTag'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['mandatory_tags'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_empty_tag(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'default'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--Tags', ''])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['mandatory_tags'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_no_name(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'describe_instance_private_ip_no_name'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'default'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['mandatory_tags'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_not_matching(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'default'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        servers_ip_not_matching = copy.deepcopy(servers_list_linux_private_ip)
        servers_ip_not_matching[0]['servers'][0]['private_ip'] = \
            servers_ip_not_matching[0]['servers'][0]['private_ip'] + '1'
        post_cutover_validations.verify_instance_details(servers_ip_not_matching, args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['host_ip_check_status'] = 'Fail'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_aws_cli_running(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'aws_cli_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'aws-cli'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        expected_report[0]['aws-cli'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_aws_cli_probably_running(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'aws_cli_probably_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'aws-cli'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        expected_report[0]['aws-cli'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_aws_cli_not_running(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'aws_cli_not_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'aws-cli'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        expected_report[0]['aws-cli'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_vmtoolsd_runnning(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'vmtoolsd_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'vmtoolsd'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        # is this expected? it reports Fail when vmtoolsd is installed
        expected_report[0]['vmtoolsd'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_vmtoolsd_not_running(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'vmtoolsd_not_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'vmtoolsd'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        # is this expected? it reports Fail when vmtoolsd is not installed
        expected_report[0]['vmtoolsd'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_my_command_running(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'my_command_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'my_command'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        expected_report[0]['my_command'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_my_command_not_running(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'my_command_not_running'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--ServiceList', 'my_command'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        del expected_report[0]['amazon-ssm-agent']
        expected_report[0]['my_command'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_host_file_entry_check_pass(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'host_file_entry_check_pass'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--HostFileEntryCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['host_file_entry_status'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_host_file_entry_check_fail(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'host_file_entry_check_fail'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--HostFileEntryCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['host_file_entry_status'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_dns_entry_check_no_dnsips(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'dns_entry_check_success'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--DnsEntryCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['dns_entry_check'] = 'NA'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_dns_entry_check_with_dnsips_success(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'dns_entry_check_success'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--DnsEntryCheck', 'True',
                                                    '--dnsIps', '192.168.0.5|192.168.0.1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['dns_entry_check'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_dns_entry_check_with_dnsips_fail(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'dns_entry_check_success'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--DnsEntryCheck', 'True',
                                                    '--dnsIps', '192.168.0.55|192.168.0.1'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['dns_entry_check'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_syslog_entry_check_pass(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'syslog_entry_check_pass'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--SyslogEntryCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['syslog_entry_check'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_syslog_entry_check_fail(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'syslog_entry_check_fail'
        post_cutover_validations.finalReport = []
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--SyslogEntryCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['syslog_entry_check'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_boot_status_check_pass(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'boot_status_check_pass'
        post_cutover_validations.finalReport = []
        post_cutover_validations.bucket_name = post_cutover_validations.output_bucket_name
        post_cutover_validations.s3_resource = boto3.resource('s3')
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--BootupStatusCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['instance_bootup_screenshot'] = 's3://cmf-post-migration-report/server1_i-111111111111.jpg'
        expected_report[0]['instance_bootup_status'] = 'Pass'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Pass'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    def test_mgn_with_running_ok_disable_api_termination_true_linux_private_ip_boot_status_check_fail(self):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        test_mgn_common.CUT_OVER_EXECUTE_CMD_SCENARIO = 'boot_status_check_fail'
        post_cutover_validations.finalReport = []
        post_cutover_validations.bucket_name = post_cutover_validations.output_bucket_name
        post_cutover_validations.s3_resource = boto3.resource('s3')
        args = post_cutover_validations.parse_args(['--Waveid', '1', '--BootupStatusCheck', 'True'])
        post_cutover_validations.verify_instance_details(copy.deepcopy(servers_list_linux_private_ip), args)
        expected_report = copy.deepcopy(self.base_report_linux)
        expected_report[0]['instance_bootup_screenshot'] = 's3://cmf-post-migration-report/server1_i-111111111111.jpg'
        expected_report[0]['instance_bootup_status'] = 'Fail'
        expected_report[0]['host_ip_check_status'] = 'Pass'
        expected_report[0]['validationStatus'] = 'Fail'
        self.assertEqual(expected_report, post_cutover_validations.finalReport)

    @patch('builtins.open', new=mock_file_open)
    @patch('subprocess.Popen')
    def test_main_mgn_with_running_ok_disable_api_termination_true(self, mock_popen):
        post_cutover_validations = importlib.import_module('5-post_cutover_validations')
        test_mgn_common.MGN_TEST_SCENARIO = 'mgn_with_running_ok'
        test_mgn_common.CUT_OVER_DESC_INSTANCE_ATTR_SCENARIO = 'ec2_attr_disable_api_termination_true'
        post_cutover_validations.finalReport = []
        post_cutover_validations.bucket_name = post_cutover_validations.output_bucket_name
        post_cutover_validations.s3_resource = boto3.resource('s3')
        args = post_cutover_validations.parse_args(['--Waveid', '1'])
        post_cutover_validations.main(args)
        expected_report = copy.deepcopy(self.base_report_windows)
        self.assertEqual(expected_report, post_cutover_validations.finalReport)
        self.assertEqual(1, mock_popen.call_count)
